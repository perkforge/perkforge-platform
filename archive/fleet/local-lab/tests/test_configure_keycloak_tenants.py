import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "local-lab/scripts"))
from tenant_catalog import load_catalog
SCRIPT = ROOT / "local-lab/scripts/configure-keycloak-tenants.py"
spec = importlib.util.spec_from_file_location("keycloak_tenant_config", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class KeycloakTenantConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(ROOT / "local-lab/tenant-config/tenants.yaml")
        cls.catalog["tenants"] = [t for t in cls.catalog["tenants"]
                                  if t.get("classification") != "protected"]


    def test_portal_client_has_pkce_no_admin_flows_and_exact_redirect(self):
        client = module.portal_client("fixture-only")
        self.assertEqual(client["clientId"], "household-portal")
        self.assertEqual(client["redirectUris"], ["https://portal.local-lab.test/auth/callback"])
        self.assertEqual(client["attributes"]["pkce.code.challenge.method"], "S256")
        for field in ("publicClient", "implicitFlowEnabled", "directAccessGrantsEnabled", "serviceAccountsEnabled", "fullScopeAllowed"):
            self.assertIs(client[field], False)
        groups, audience, roles = module.portal_mappers()
        self.assertEqual(groups["config"]["access.token.claim"], "true")
        self.assertEqual(groups["config"]["full.path"], "true")
        self.assertEqual(audience["config"]["included.custom.audience"], "household-portal-api")
        self.assertEqual(module.group_mapper()["config"]["access.token.claim"], "false")
        self.assertEqual(roles["protocolMapper"], "oidc-usermodel-realm-role-mapper")
        self.assertEqual(roles["config"]["claim.name"], "resource_access.household-portal-api.roles")
        self.assertEqual(roles["config"]["multivalued"], "true")
        self.assertEqual(roles["config"]["access.token.claim"], "true")
        for destination in ("id.token.claim", "userinfo.token.claim", "introspection.token.claim"):
            self.assertEqual(roles["config"][destination], "false")
        self.assertNotIn("claim.value", roles["config"])  # Never hardcode an entitlement.


    def test_portal_refuses_unowned_existing_client_before_writes(self):
        admin = object.__new__(module.KeycloakAdmin)
        calls = []
        def api(method, path, value=None, accepted=(200,)):
            calls.append((method,path))
            if path.endswith("/clients?clientId=household-portal"):
                return json.dumps([{"clientId":"household-portal","id":"foreign"}]).encode()
            return json.dumps({"attributes":{module.OWNERSHIP_ATTRIBUTE:"true"}}).encode()
        admin.api = api
        with self.assertRaisesRegex(RuntimeError, "not platform-owned"):
            admin.ensure_portal_client()
        self.assertTrue(all(method == "GET" for method, path in calls))

    def test_group_paths_cover_all_tenants_and_roles(self):
        paths = module.group_paths(self.catalog)
        self.assertEqual(len(paths), 6)
        self.assertIn("/tenants/tenant-alpha/admins", paths)
        self.assertIn("/tenants/tenant-bravo/viewers", paths)
        self.assertEqual(len(module.synthetic_identities(self.catalog)), 6)

    def test_rejects_group_that_does_not_match_tenant_role(self):
        catalog = yaml.safe_load(yaml.safe_dump(self.catalog))
        catalog["tenants"][0]["identity"]["groups"]["admins"] = "/tenants/all/admins"
        with self.assertRaisesRegex(ValueError, "expected Keycloak group"):
            module.group_paths(catalog)

    def test_rancher_client_is_confidential_and_restricts_redirect(self):
        client = module.rancher_client("fixture-secret")
        self.assertFalse(client["publicClient"])
        self.assertFalse(client["directAccessGrantsEnabled"])
        self.assertEqual(client["redirectUris"],
                         ["https://rancher.local-lab.test/verify-auth"])
        self.assertEqual(client["secret"], "fixture-secret")

    def test_group_mapper_emits_full_paths_into_id_token(self):
        config = module.group_mapper()["config"]
        self.assertEqual(config["claim.name"], "groups")
        self.assertEqual(config["full.path"], "true")
        self.assertEqual(config["id.token.claim"], "true")
        self.assertEqual(config["introspection.token.claim"], "false")


    def test_client_and_mapper_reconciliation_has_a_safe_postcondition(self):
        secret = "fixture-secret"
        client = module.rancher_client(secret)
        mapper = module.group_mapper()
        self.assertEqual(module.rancher_client_errors(client, secret, secret, [mapper]), [])
        bad_redirect = {**client, "redirectUris": ["https://wrong.example/verify-auth"]}
        errors = module.rancher_client_errors(bad_redirect, secret, secret, [mapper])
        self.assertIn("redirectUris", errors)
        bad_mapper = {**mapper, "config": {**mapper["config"], "full.path": "false"}}
        self.assertIn("groups mapper config",
                      module.rancher_client_errors(client, secret, secret, [bad_mapper]))
        self.assertIn("client secret",
                      module.rancher_client_errors(client, secret, "different-secret", [mapper]))
        self.assertNotIn(secret, ", ".join(errors))
    def test_rancher_oidc_uses_public_issuer_and_internal_backchannel(self):
        endpoints = module.rancher_oidc_endpoints()
        self.assertEqual(endpoints["issuer"],
                         "https://keycloak.local-lab.test/auth/realms/perkforge")
        self.assertTrue(endpoints["authEndpoint"].startswith("https://keycloak.local-lab.test/"))
        for name in ("tokenEndpoint", "userInfoEndpoint", "jwksUrl"):
            self.assertTrue(endpoints[name].startswith(
                "http://keycloak-keycloakx-http.keycloak.svc.cluster.local/"))

    def test_chart_pins_public_issuer_and_dynamic_backchannel(self):
        values = yaml.safe_load((ROOT / "local-lab/fleet/bundles/keycloak/values.yaml").read_text())
        self.assertEqual(values["proxy"], {"enabled": True, "mode": "xforwarded"})
        environment = yaml.safe_load(values["extraEnv"])
        variables = {entry["name"]: entry.get("value") for entry in environment}
        self.assertEqual(variables["KC_HOSTNAME"], "https://keycloak.local-lab.test/auth")
        self.assertEqual(variables["KC_HOSTNAME_BACKCHANNEL_DYNAMIC"], "true")

    def test_keycloak_group_path_reconcile_is_idempotent_and_owned(self):
        admin = module.KeycloakAdmin.__new__(module.KeycloakAdmin)
        groups = {}
        create_count = 0

        def api(method, path, value=None, accepted=(200,)):
            nonlocal create_count
            pieces = path.split("?", 1)[0].strip("/").split("/")
            if method == "GET" and pieces[-1] in {"groups", "children"}:
                parent = pieces[-2] if pieces[-1] == "children" else None
                return json.dumps([group for group in groups.values()
                                   if group["parent"] == parent]).encode()
            if method == "POST" and pieces[-1] in {"groups", "children"}:
                parent = pieces[-2] if pieces[-1] == "children" else None
                create_count += 1
                group_id = f"group-{create_count}"
                groups[group_id] = {"id": group_id, "name": value["name"],
                                    "attributes": value["attributes"], "parent": parent}
                return b""
            if method == "PUT" and pieces[-2] == "groups":
                group_id = pieces[-1]
                groups[group_id].update(value)
                return b""
            raise AssertionError(f"unexpected Keycloak API request: {method} {path}")

        admin.api = api
        first = admin.ensure_group_path("/tenants/tenant-alpha/admins")
        second = admin.ensure_group_path("/tenants/tenant-alpha/admins")
        self.assertEqual(first, second)
        self.assertEqual(create_count, 3)
        leaf = groups[first]
        self.assertEqual(leaf["attributes"]["platform-tenant"], ["tenant-alpha"])
        self.assertEqual(leaf["attributes"]["platform-role"], ["admins"])

    def test_adopts_only_empty_legacy_tenants_container(self):
        admin = module.KeycloakAdmin.__new__(module.KeycloakAdmin)
        groups = {
            "root": {"id": "root", "name": "tenants", "path": "/tenants",
                     "attributes": {}, "parent": None},
            "tenant": {"id": "tenant", "name": "tenant-alpha",
                       "path": "/tenants/tenant-alpha",
                       "attributes": {"perkforge-managed": ["true"]}, "parent": "root",
                       "platform-tenant": ["tenant-alpha"]},
            "admins": {"id": "admins", "name": "admins",
                       "path": "/tenants/tenant-alpha/admins",
                       "attributes": {"perkforge-managed": ["true"],
                                      "platform-tenant": ["tenant-alpha"],
                                      "platform-role": ["admins"]}, "parent": "tenant"},
        }

        def api(method, path, value=None, accepted=(200,)):
            pieces = path.split("?", 1)[0].strip("/").split("/")
            if method == "GET" and "members" in pieces:
                return b"[]"
            if method == "GET" and pieces[-1] in {"groups", "children"}:
                parent = pieces[-2] if pieces[-1] == "children" else None
                return json.dumps([group for group in groups.values()
                                   if group["parent"] == parent]).encode()
            if method == "PUT" and pieces[-2] == "groups":
                groups[pieces[-1]].update(value)
                return b""
            raise AssertionError(f"unexpected Keycloak API request: {method} {path}")

        admin.api = api
        admin.ensure_group_path("/tenants/tenant-alpha/admins")
        self.assertEqual(groups["root"]["attributes"], {"perkforge-managed": ["true"]})

    def test_refuses_to_adopt_populated_legacy_tenants_container(self):
        admin = module.KeycloakAdmin.__new__(module.KeycloakAdmin)

        def api(method, path, value=None, accepted=(200,)):
            if method == "GET" and "search=tenants" in path:
                return json.dumps([{"id": "root", "name": "tenants", "attributes": {}}]).encode()
            if method == "GET" and "members" in path:
                return json.dumps([{"id": "existing-user"}]).encode()
            raise AssertionError(f"unexpected Keycloak API request: {method} {path}")

        admin.api = api
        with self.assertRaisesRegex(RuntimeError, "without PerkForge ownership metadata"):
            admin.ensure_group_path("/tenants/tenant-alpha/admins")

    def test_adopts_legacy_synthetic_user_in_its_catalog_group(self):
        admin = module.KeycloakAdmin.__new__(module.KeycloakAdmin)
        user = {"id": "user-1", "username": "tenant-alpha-admins",
                "email": "tenant-alpha-admins@example.invalid", "enabled": True,
                "attributes": {}}
        calls = []
        memberships = [{"id": "group-1", "attributes": {
            "perkforge-managed": ["true"], "platform-tenant": ["tenant-alpha"],
            "platform-role": ["admins"]}}]

        def api(method, path, value=None, accepted=(200,)):
            calls.append((method, path, value))
            if method == "GET" and "/users?" in path:
                return json.dumps([user]).encode()
            if method == "GET" and path.endswith("/groups"):
                return json.dumps(memberships).encode()
            if method == "PUT" and path.endswith("/users/user-1"):
                user.update(value)
                return b""
            if method == "PUT" and path.endswith("/groups/group-1"):
                return b""
            raise AssertionError(f"unexpected Keycloak API request: {method} {path}")

        admin.api = api
        with tempfile.TemporaryDirectory() as directory:
            password_file = Path(directory) / "tenant-alpha-admins-password"
            password_file.write_text("existing-local-secret\n")
            admin.ensure_user("tenant-alpha", "admins", "tenant-alpha-admins",
                              "group-1", password_file)
        self.assertEqual(user["attributes"], {})
        self.assertFalse(any(method == "PUT" and path.endswith("/users/user-1")
                             for method, path, _ in calls))
        self.assertFalse(any("reset-password" in path for _, path, _ in calls))

    def test_rejects_unowned_user_with_group_membership(self):
        admin = module.KeycloakAdmin.__new__(module.KeycloakAdmin)
        user = {"id": "user-1", "username": "tenant-alpha-admins",
                "email": "tenant-alpha-admins@example.invalid", "enabled": True,
                "attributes": {}}

        def api(method, path, value=None, accepted=(200,)):
            if method == "GET" and "/users?" in path:
                return json.dumps([user]).encode()
            if method == "GET" and path.endswith("/groups"):
                return json.dumps([{"id": "unowned-group"}]).encode()
            raise AssertionError(f"unexpected Keycloak API request: {method} {path}")

        admin.api = api
        with tempfile.TemporaryDirectory() as directory:
            password_file = Path(directory) / "tenant-alpha-admins-password"
            password_file.write_text("existing-local-secret\n")
            with self.assertRaisesRegex(RuntimeError, "not owned by this tenant catalog"):
                admin.ensure_user("tenant-alpha", "admins", "tenant-alpha-admins",
                                  "group-1", password_file)

    def test_secret_file_is_owner_only(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "private" / "client-secret"
            module.write_secret(target, "synthetic-secret")
            self.assertEqual(target.read_text(), "synthetic-secret\n")
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(target.parent.stat().st_mode & 0o777, 0o700)


if __name__ == "__main__":
    unittest.main()
