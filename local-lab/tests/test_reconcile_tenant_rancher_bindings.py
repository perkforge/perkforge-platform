import importlib.util
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "local-lab/scripts/reconcile-tenant-rancher-bindings.py"
spec = importlib.util.spec_from_file_location("tenant_rancher_bindings", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TenantRancherBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = yaml.safe_load((ROOT / "local-lab/tenant-config/tenants.yaml").read_text())
        cls.projects = {}
        for tenant in cls.catalog["tenants"]:
            project_id = f"p-{tenant['id']}-{tenant['cluster']}"
            cls.projects[project_id] = {
                "metadata": {
                    "name": project_id,
                    "namespace": cls.catalog["rancherManagementCluster"],
                    "labels": {
                        "platform.perkforge.io/tenant": tenant["id"],
                        "platform.perkforge.io/managed-by": "tenant-foundation",
                    },
                },
                "spec": {"clusterName": tenant["cluster"]},
                "status": {"backingNamespace": project_id},
            }

    def test_emits_three_deterministic_role_bindings_per_tenant(self):
        bindings = module.build_bindings(self.catalog, self.projects)
        self.assertEqual(len(bindings), 6)
        self.assertEqual(len({obj["metadata"]["name"] for obj in bindings}), 6)
        self.assertEqual({obj["roleTemplateName"] for obj in bindings},
                         set(module.ROLE_TEMPLATES.values()))
        for obj in bindings:
            tenant = obj["metadata"]["labels"]["platform.perkforge.io/tenant"]
            role = obj["metadata"]["labels"]["platform.perkforge.io/tenant-role"]
            self.assertEqual(obj["groupPrincipalName"],
                             f"genericoidc_group:///tenants/{tenant}/{role}")
            self.assertEqual(obj["projectName"], f"local:p-{tenant}-local")
            self.assertEqual(obj["metadata"]["namespace"], f"p-{tenant}-local")

    def test_refuses_unowned_or_wrong_cluster_projects(self):
        projects = yaml.safe_load(yaml.safe_dump(self.projects))
        projects["p-tenant-alpha-local"]["metadata"]["labels"][
            "platform.perkforge.io/tenant"] = "someone-else"
        with self.assertRaisesRegex(ValueError, "not owned"):
            module.build_bindings(self.catalog, projects)

    def test_waits_for_rancher_backing_namespace(self):
        projects = yaml.safe_load(yaml.safe_dump(self.projects))
        del projects["p-tenant-alpha-local"]["status"]["backingNamespace"]
        with self.assertRaisesRegex(ValueError, "backingNamespace"):
            module.build_bindings(self.catalog, projects)

    def test_group_principal_paths_are_explicit_and_role_scoped(self):
        catalog = yaml.safe_load(yaml.safe_dump(self.catalog))
        catalog["tenants"][0]["identity"]["groups"]["developers"] = "/tenants/all/developers"
        with self.assertRaisesRegex(ValueError, "unexpected Keycloak developers group path"):
            module.build_bindings(catalog, self.projects)

    def test_apply_refuses_disabled_generic_oidc_before_writing(self):
        fake = FakeKubectl(self.projects, oidc_enabled=False)
        with self.assertRaisesRegex(ValueError, "Generic OIDC through Keycloak is not enabled"):
            module.reconcile(self.catalog, fake, apply=True)
        self.assertEqual(fake.applied, [])

    def test_apply_is_idempotent_for_catalog_owned_bindings(self):
        fake = FakeKubectl(self.projects, oidc_enabled=True)
        module.reconcile(self.catalog, fake, apply=True)
        first_count = len(fake.applied)
        self.assertEqual(first_count, 6)
        module.reconcile(self.catalog, fake, apply=True)
        self.assertEqual(len(fake.applied), first_count)


class FakeKubectl:
    def __init__(self, projects, oidc_enabled):
        self.projects = projects
        self.oidc_enabled = oidc_enabled
        self.applied = []

    def json(self, *args):
        if args[0] == "get" and args[1] == "projects.management.cattle.io":
            return self.projects[args[2]]
        if args[0] == "get" and args[1] == "authconfigs.management.cattle.io":
            return {"enabled": self.oidc_enabled, "type": "genericOIDCConfig"}
        if args[0] == "get" and args[1] == "roletemplates.management.cattle.io":
            return {"metadata": {"name": args[2]}}
        if args[0] == "get" and args[1] == "projectroletemplatebindings.management.cattle.io":
            namespace = args[args.index("--namespace") + 1]
            return {"items": [obj for obj in self.applied
                              if obj["metadata"]["namespace"] == namespace]}
        raise AssertionError(f"unexpected kubectl request: {args}")

    def apply(self, document):
        self.applied.append(document)


if __name__ == "__main__":
    unittest.main()
