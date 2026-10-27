import importlib.util
import json
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "local-lab/scripts"))
from tenant_catalog import load_catalog
SCRIPT = ROOT / "local-lab/scripts/verify-tenant-quota.py"
spec = importlib.util.spec_from_file_location("tenant_quota_evidence", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TenantQuotaEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(ROOT / "local-lab/tenant-config/tenants.yaml")
        cls.catalog["tenants"] = [t for t in cls.catalog["tenants"]
                                  if t.get("classification") != "protected"]

    def test_cases_cover_defaults_admission_and_resource_quota_denials(self):
        cases = module.quota_cases(self.catalog)
        self.assertEqual([case["mutation"] for case in cases], ["defaults", "within", "cpu", "memory"])
        self.assertEqual([case["expected"] for case in cases], ["allow", "allow", "deny", "deny"])

    def test_default_case_omits_resources_for_limitrange_mutation(self):
        pod = module.pod_manifest(module.quota_cases(self.catalog)[0], "123456")
        self.assertFalse(pod["spec"]["automountServiceAccountToken"])
        self.assertNotIn("resources", pod["spec"]["containers"][0])

    def test_denial_requires_resourcequota_error(self):
        case = module.quota_cases(self.catalog)[2]
        result = module.run_case(FakeKubectl(1, stderr="exceeded quota tenant-budget"), case,
                                 "123456", {})
        self.assertTrue(result["passed"])
        unrelated = module.run_case(FakeKubectl(1, stderr="Forbidden"), case, "123456", {})
        self.assertFalse(unrelated["passed"])
        self.assertFalse(module.run_case(FakeKubectl(0), case, "123456", {})["passed"])

    def test_limitrange_case_requires_catalog_default_values(self):
        case = module.quota_cases(self.catalog)[0]
        defaults = {"requestCpu": "100m", "requestMemory": "128Mi",
                    "limitCpu": "500m", "limitMemory": "512Mi"}
        payload = {"spec": {"containers": [{"resources": {
            "requests": {"cpu": "100m", "memory": "128Mi"},
            "limits": {"cpu": "500m", "memory": "512Mi"}}}]}}
        self.assertTrue(module.run_case(FakeKubectl(0, stdout=json.dumps(payload)),
                                        case, "123456", defaults)["passed"])
        self.assertFalse(module.run_case(FakeKubectl(0, stdout="{}"), case, "123456", defaults)["passed"])

    def test_project_and_namespace_quota_configuration_matches_catalog(self):
        tenant = self.catalog["tenants"][0]
        project_id = f"p-{tenant['id']}-{tenant['cluster']}"
        project = {
            "metadata": {"name": project_id, "namespace": "local", "labels": {
                "platform.perkforge.io/tenant": tenant["id"],
                "platform.perkforge.io/managed-by": "tenant-foundation"}},
            "spec": {"clusterName": tenant["cluster"],
                     "resourceQuota": {"limit": module.rancher_limits(tenant["resources"]["budget"])},
                     "namespaceDefaultResourceQuota": {"limit": module.rancher_limits(tenant["resources"]["budget"])}}}
        namespace = {"metadata": {"name": tenant["environments"][0]["namespace"],
                    "labels": {"platform.perkforge.io/tenant": tenant["id"]},
                    "annotations": {
                        "field.cattle.io/projectId": f"{tenant['cluster']}:{project_id}",
                        "field.cattle.io/resourceQuota": json.dumps({"limit": module.rancher_limits(
                            tenant["environments"][0]["allocation"])})}}}
        self.assertEqual(module.project_quota_errors(tenant, tenant["environments"][0],
                                                     "local", project, namespace), [])
        project["spec"]["resourceQuota"]["limit"]["requestsMemory"] = "1Gi"
        errors = module.project_quota_errors(tenant, tenant["environments"][0],
                                             "local", project, namespace)
        self.assertIn("Rancher project quota ceiling", errors)

    def test_namespace_quota_preflight_uses_each_environment_allocation(self):
        tenant = self.catalog["tenants"][0]
        second_environment = {"name": "test", "namespace": "tenant-alpha-test",
                              "allocation": {**tenant["environments"][0]["allocation"],
                                             "requests.cpu": "250m"}}
        project_id = f"p-{tenant['id']}-{tenant['cluster']}"
        project = {"metadata": {"name": project_id, "namespace": "local", "labels": {
                       "platform.perkforge.io/tenant": tenant["id"],
                       "platform.perkforge.io/managed-by": "tenant-foundation"}},
                   "spec": {"clusterName": tenant["cluster"],
                            "resourceQuota": {"limit": module.rancher_limits(tenant["resources"]["budget"])},
                            "namespaceDefaultResourceQuota": {"limit": module.rancher_limits(tenant["resources"]["budget"])}}}
        namespace = {"metadata": {"name": second_environment["namespace"],
                    "labels": {"platform.perkforge.io/tenant": tenant["id"]},
                    "annotations": {"field.cattle.io/projectId": f"{tenant['cluster']}:{project_id}",
                                    "field.cattle.io/resourceQuota": json.dumps({"limit": module.rancher_limits(
                                        second_environment["allocation"])})}}}
        self.assertEqual(module.project_quota_errors(tenant, second_environment,
                                                     "local", project, namespace), [])

    def test_project_quota_check_rejects_wrong_namespace_association(self):
        tenant = self.catalog["tenants"][0]
        project_id = f"p-{tenant['id']}-{tenant['cluster']}"
        project = {
            "metadata": {"name": project_id, "namespace": "local", "labels": {
                "platform.perkforge.io/tenant": tenant["id"],
                "platform.perkforge.io/managed-by": "tenant-foundation"}},
            "spec": {"clusterName": tenant["cluster"],
                     "resourceQuota": {"limit": module.rancher_limits(tenant["resources"]["budget"])},
                     "namespaceDefaultResourceQuota": {"limit": module.rancher_limits(tenant["resources"]["budget"])}}}
        namespace = {"metadata": {"name": tenant["environments"][0]["namespace"],
                    "labels": {"platform.perkforge.io/tenant": tenant["id"]},
                    "annotations": {"field.cattle.io/projectId": "local:p-wrong",
                                    "field.cattle.io/resourceQuota": "not-json"}}}
        errors = module.project_quota_errors(tenant, tenant["environments"][0],
                                             "local", project, namespace)
        self.assertIn("namespace Rancher project association", errors)
        self.assertIn("namespace reserved project quota allocation", errors)


class FakeKubectl:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr

    def run(self, args, input_text=None):
        return type("Result", (), {"returncode": self.returncode,
                                   "stdout": self.stdout, "stderr": self.stderr})()


if __name__ == "__main__":
    unittest.main()
