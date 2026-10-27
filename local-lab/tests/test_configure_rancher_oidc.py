import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "local-lab/scripts"))
from tenant_catalog import load_catalog
SCRIPT = ROOT / "local-lab/scripts/configure-rancher-oidc.py"
spec = importlib.util.spec_from_file_location("configure_rancher_oidc", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RancherOidcConfigurationTests(unittest.TestCase):
    def test_https_only_preserves_live_client_and_principal_list(self):
        current = {"metadata":{"name":"genericoidc","resourceVersion":"17","labels":{module.OWNER_LABEL:module.OWNER_VALUE}},
                   "type":module.AUTH_TYPE,"enabled":True,"clientId":"rancher","clientSecret":"fixture-only",
                   "issuer":"http://keycloak.local-lab.test/auth/realms/perkforge",
                   "authEndpoint":"http://keycloak.local-lab.test/auth/realms/perkforge/protocol/openid-connect/auth",
                   "allowedPrincipalIds":["existing-review-group"]}
        configs = [{"metadata":{"name":"local"},"enabled":True},current]
        before, patch = module.https_only_config(configs)
        self.assertEqual(set(patch), {"metadata","issuer","authEndpoint"})
        self.assertEqual(patch["metadata"], {"resourceVersion":"17"})
        self.assertEqual(before["allowedPrincipalIds"],["existing-review-group"])
        self.assertNotIn("clientSecret",patch)
        current["issuer"] = "https://unexpected.invalid"
        with self.assertRaisesRegex(ValueError,"Unexpected existing issuer"):
            module.https_only_config(configs)

    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(ROOT / "local-lab/tenant-config/tenants.yaml")
        cls.catalog["tenants"] = [t for t in cls.catalog["tenants"]
                                  if t.get("classification") != "protected"]

    def test_auth_config_uses_restricted_generic_oidc_groups_and_split_urls(self):
        desired = module.auth_config(self.catalog, "private-fixture")
        self.assertEqual(desired["type"], "genericOIDCConfig")
        self.assertTrue(desired["enabled"])
        self.assertEqual(desired["accessMode"], "restricted")
        self.assertEqual(len(desired["allowedPrincipalIds"]), 6)
        self.assertIn("genericoidc_group:///tenants/tenant-alpha/admins",
                      desired["allowedPrincipalIds"])
        config = desired
        self.assertEqual(config["issuer"], module.KEYCLOAK_PUBLIC_REALM)
        self.assertEqual(config["rancherUrl"], module.RANCHER_REDIRECT_URL)
        self.assertEqual(config["rancherApiHost"], module.RANCHER_URL)
        self.assertNotIn("genericOIDCConfig", desired)
        self.assertIn("keycloak.local-lab.test", config["authEndpoint"])
        self.assertIn(".svc.cluster.local", config["tokenEndpoint"])
        self.assertTrue(config["groupSearchEnabled"])
        self.assertEqual(config["groupsClaim"], "groups")

    def test_empty_secret_and_mismatched_group_paths_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "secret is empty"):
            module.auth_config(self.catalog, "  ")
        catalog = yaml.safe_load(yaml.safe_dump(self.catalog))
        catalog["tenants"][0]["identity"]["groups"]["admins"] = "/tenants/all/admins"
        with self.assertRaisesRegex(ValueError, "expected Keycloak group path"):
            module.group_principals(catalog)

    def test_refuses_other_enabled_provider_or_unowned_generic_oidc_config(self):
        desired = module.auth_config(self.catalog, "fixture")
        local = {"metadata": {"name": "local"}, "enabled": True}
        builtin = {"metadata": {"name": "genericoidc"}, "type": module.AUTH_TYPE,
                   "clientId": "", "authEndpoint": ""}
        with self.assertRaisesRegex(ValueError, "another external Rancher auth provider"):
            module.validate_target([local, builtin, {"metadata": {"name": "keycloakoidc"},
                                                       "enabled": True}], desired)
        unowned = {**builtin, "clientId": "some-other-client"}
        with self.assertRaisesRegex(ValueError, "unowned settings"):
            module.validate_target([local, unowned], desired)

    def test_refuses_to_enable_oidc_if_local_auth_is_disabled_or_missing(self):
        desired = module.auth_config(self.catalog, "fixture")
        generic = {"metadata": {"name": "genericoidc"}, "type": module.AUTH_TYPE,
                   "clientId": "", "authEndpoint": ""}
        with self.assertRaisesRegex(ValueError, "local authentication must already be enabled"):
            module.validate_target([generic, {"metadata": {"name": "local"}, "enabled": False}], desired)
        with self.assertRaisesRegex(ValueError, "local authentication must already be enabled"):
            module.validate_target([generic], desired)

    def test_apply_is_idempotent_and_checks_safe_postcondition(self):
        with tempfile.TemporaryDirectory() as directory:
            secret_file = Path(directory) / "oidc-secret"
            secret_file.write_text("fixture-secret\n")
            fake = FakeKubectl()
            module.reconcile(self.catalog, secret_file, fake, apply=True)
            first = fake.apply_count
            self.assertEqual(fake.current["enabled"], True)
            self.assertEqual(fake.current["accessMode"], "restricted")
            self.assertTrue(fake.local["enabled"])
            module.reconcile(self.catalog, secret_file, fake, apply=True)
            self.assertEqual(fake.apply_count, first + 1)
            self.assertEqual(fake.current["clientSecret"], "fixture-secret")

    def test_server_dry_run_passes_dry_run_flag_without_persisting(self):
        with tempfile.TemporaryDirectory() as directory:
            secret_file = Path(directory) / "oidc-secret"
            secret_file.write_text("fixture-secret\n")
            fake = FakeKubectl()
            module.reconcile(self.catalog, secret_file, fake, server_dry_run=True)
            self.assertEqual(fake.apply_count, 1)
            self.assertTrue(fake.last_dry_run)
            self.assertEqual(fake.current.get("clientId"), "")

    def test_plan_mode_does_not_expose_or_read_secret_content(self):
        with tempfile.TemporaryDirectory() as directory:
            secret_file = Path(directory) / "oidc-secret"
            secret_file.write_text("never-print-this-secret\n")
            output = io.StringIO()
            with patch("sys.argv", [str(SCRIPT), "--secret-file", str(secret_file),
                                     "--kubectl", "/missing/kubectl"]), redirect_stdout(output):
                result = module.main()
            self.assertEqual(result, 0)
            self.assertIn("Plan only", output.getvalue())
            self.assertNotIn("never-print-this-secret", output.getvalue())


class FakeKubectl:
    def __init__(self):
        self.local = {"metadata": {"name": "local"}, "type": "localConfig", "enabled": True}
        self.current = {"metadata": {"name": "genericoidc",
                                     "labels": {module.OWNER_LABEL: module.OWNER_VALUE}},
                        "type": module.AUTH_TYPE, "clientId": "", "authEndpoint": ""}
        self.apply_count = 0
        self.last_dry_run = False

    def json(self, *args):
        if args == ("get", "authconfigs.management.cattle.io"):
            return {"items": [self.local, self.current]}
        if args == ("get", "authconfigs.management.cattle.io", "genericoidc"):
            return self.current
        if args == ("get", "authconfigs.management.cattle.io", "local"):
            return self.local
        raise AssertionError(f"unexpected kubectl request: {args}")

    def apply(self, document, server_dry_run=False):
        self.apply_count += 1
        self.last_dry_run = server_dry_run
        if not server_dry_run:
            self.current = document


if __name__ == "__main__":
    unittest.main()
