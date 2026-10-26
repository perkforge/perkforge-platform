import importlib.util
import json
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "local-lab/scripts/render-tenant-foundation.py"
spec = importlib.util.spec_from_file_location("tenant_foundation", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TenantFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = yaml.safe_load((ROOT / "local-lab/tenant-config/tenants.yaml").read_text())

    def test_catalog_allocations_fit_tenant_budgets(self):
        self.assertEqual(len(module.validate_catalog(self.catalog)), 2)

    def test_each_tenant_can_target_a_registered_cluster(self):
        catalog = yaml.safe_load(yaml.safe_dump(self.catalog))
        catalog["clusters"].append({"name": "cluster-stg", "podSecurityVersion": "v1.36"})
        catalog["tenants"][1]["cluster"] = "cluster-stg"
        objects = list(yaml.safe_load_all(module.render(catalog)))
        project = next(obj for obj in objects if obj.get("kind") == "Project" and
                       obj["metadata"]["name"] == "p-tenant-bravo-cluster-stg")
        self.assertEqual(project["spec"]["clusterName"], "cluster-stg")
        namespace = next(obj for obj in objects if obj.get("kind") == "Namespace" and
                         obj["metadata"]["name"] == "tenant-bravo")
        self.assertEqual(namespace["metadata"]["annotations"]["field.cattle.io/projectId"],
                         "cluster-stg:p-tenant-bravo-cluster-stg")

    def test_overallocated_namespace_budget_is_rejected(self):
        invalid = yaml.safe_load(yaml.safe_dump(self.catalog))
        invalid["tenants"][0]["environments"][0]["allocation"]["requests.cpu"] = "2"
        with self.assertRaisesRegex(ValueError, "exceed tenant budget"):
            module.validate_catalog(invalid)

    def test_render_has_isolated_namespaces_and_tenant_network_selectors(self):
        objects = list(yaml.safe_load_all(module.render(self.catalog)))
        namespaces = [obj for obj in objects if obj["kind"] == "Namespace"]
        self.assertEqual({obj["metadata"]["name"] for obj in namespaces},
                         {"tenant-alpha", "tenant-bravo"})
        policies = [obj for obj in objects if obj["kind"] == "NetworkPolicy"
                    and obj["metadata"]["name"] == "allow-tenant-internal-and-dns"]
        self.assertEqual(len(policies), 2)
        for policy in policies:
            peers = policy["spec"]["ingress"][0]["from"]
            self.assertIn("platform.perkforge.io/tenant", peers[0]["namespaceSelector"]["matchLabels"])
            self.assertEqual(peers[1]["namespaceSelector"]["matchLabels"]["kubernetes.io/metadata.name"], "kube-system")
            self.assertEqual(peers[1]["podSelector"]["matchLabels"]["app.kubernetes.io/name"], "rke2-traefik")
            self.assertEqual(peers[2]["namespaceSelector"]["matchLabels"]["kubernetes.io/metadata.name"],
                             "monitoring")
            self.assertEqual(peers[2]["podSelector"]["matchLabels"]["app.kubernetes.io/name"],
                             "prometheus")
            egress = policy["spec"]["egress"]
            keycloak = next(rule for rule in egress if rule.get("ports") == [
                {"protocol": "TCP", "port": 8080}])
            self.assertEqual(keycloak["to"][0]["namespaceSelector"]["matchLabels"],
                             {"kubernetes.io/metadata.name": "keycloak"})
            self.assertEqual(egress[1]["ports"], [
                {"protocol": "UDP", "port": 53}, {"protocol": "TCP", "port": 53}])

    def test_catalog_uses_role_scoped_keycloak_group_paths(self):
        for tenant in self.catalog["tenants"]:
            for role in ("admins", "developers", "viewers"):
                self.assertEqual(tenant["identity"]["groups"][role],
                                 f"/tenants/{tenant['id']}/{role}")
        objects = list(yaml.safe_load_all(module.render(self.catalog)))
        self.assertFalse(any(obj["kind"] in {"Role", "RoleBinding"} for obj in objects))

    def test_catalog_rejects_wide_group_paths(self):
        invalid = yaml.safe_load(yaml.safe_dump(self.catalog))
        invalid["tenants"][0]["identity"]["groups"]["developers"] = "/tenants/all/developers"
        with self.assertRaisesRegex(ValueError, "must be /tenants/tenant-alpha/developers"):
            module.validate_catalog(invalid)


    def test_projects_have_stable_ids_association_and_aggregate_quota(self):
        objects = list(yaml.safe_load_all(module.render(self.catalog)))
        projects = [obj for obj in objects if obj["kind"] == "Project"]
        self.assertEqual({obj["metadata"]["name"] for obj in projects},
                         {"p-tenant-alpha-local", "p-tenant-bravo-local"})
        for project in projects:
            self.assertEqual(project["metadata"]["namespace"], "local")
            self.assertEqual(project["spec"]["clusterName"], "local")
            self.assertEqual(project["metadata"]["annotations"]["field.cattle.io/no-creator-rbac"], "true")
            self.assertEqual(project["spec"]["resourceQuota"],
                             project["spec"]["namespaceDefaultResourceQuota"])
        namespaces = [obj for obj in objects if obj["kind"] == "Namespace"]
        for namespace in namespaces:
            tenant_id = namespace["metadata"]["labels"]["platform.perkforge.io/tenant"]
            self.assertEqual(namespace["metadata"]["annotations"]["field.cattle.io/projectId"],
                             f"local:p-{tenant_id}-local")
            quota = json.loads(namespace["metadata"]["annotations"]["field.cattle.io/resourceQuota"])
            self.assertEqual(quota["limit"]["requestsCpu"], "1")
            self.assertEqual(quota["limit"]["requestsMemory"], "1500Mi")
            self.assertEqual(list(quota["limit"]), [
                "pods", "services", "persistentVolumeClaims", "requestsCpu",
                "requestsMemory", "requestsStorage", "limitsCpu", "limitsMemory",
            ])

    def test_rancher_namespace_reservation_matches_environment_allocation(self):
        catalog = yaml.safe_load(yaml.safe_dump(self.catalog))
        tenant = catalog["tenants"][0]
        first = tenant["environments"][0]
        first["name"], first["namespace"] = "dev", "tenant-alpha-dev"
        first["allocation"] = {"pods": "7", "requests.cpu": "500m", "requests.memory": "750Mi",
                               "limits.cpu": "1", "limits.memory": "1Gi",
                               "persistentvolumeclaims": "2", "requests.storage": "4Gi", "services": "4"}
        tenant["environments"].append({"name": "prod", "namespace": "tenant-alpha-prod",
            "allocation": {"pods": "8", "requests.cpu": "500m", "requests.memory": "750Mi",
                           "limits.cpu": "1", "limits.memory": "1Gi",
                           "persistentvolumeclaims": "3", "requests.storage": "6Gi", "services": "6"}})
        objects = list(yaml.safe_load_all(module.render(catalog)))
        namespaces = {obj["metadata"]["name"]: obj for obj in objects if obj["kind"] == "Namespace"}
        dev_reservation = json.loads(namespaces["tenant-alpha-dev"]["metadata"]["annotations"]
                                     ["field.cattle.io/resourceQuota"])["limit"]
        prod_reservation = json.loads(namespaces["tenant-alpha-prod"]["metadata"]["annotations"]
                                      ["field.cattle.io/resourceQuota"])["limit"]
        self.assertEqual(dev_reservation["requestsCpu"], "500m")
        self.assertEqual(prod_reservation["requestsCpu"], "500m")
        self.assertEqual(dev_reservation["requestsStorage"], "4Gi")
        self.assertEqual(prod_reservation["requestsStorage"], "6Gi")

    def test_custom_roles_do_not_grant_developer_or_viewer_secret_access(self):
        objects = list(yaml.safe_load_all(module.render(self.catalog)))
        roles = {obj["metadata"]["name"]: obj for obj in objects if obj["kind"] == "RoleTemplate"}
        for role in roles.values():
            # Rancher defaults this boolean to false and omits it from the
            # stored object; avoid perpetual Fleet drift from an explicit false.
            self.assertNotIn("projectCreatorDefault", role)
        for name in ("perkforge-tenant-developer", "perkforge-tenant-viewer"):
            resources = {resource for rule in roles[name]["rules"] for resource in rule.get("resources", [])}
            self.assertNotIn("secrets", resources)
            self.assertNotIn("rolebindings", resources)
        developer = roles["perkforge-tenant-developer"]
        self.assertFalse(any("create" in rule.get("verbs", []) and "pods" in rule.get("resources", [])
                             for rule in developer["rules"]))
        for name in ("perkforge-tenant-admin", "perkforge-tenant-developer", "perkforge-tenant-viewer"):
            self.assertTrue(any(rule.get("apiGroups") == ["metrics.k8s.io"] and
                                rule.get("resources") == ["pods"]
                                for rule in roles[name]["rules"]))


if __name__ == "__main__":
    unittest.main()
