import importlib.util
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "local-lab/scripts/verify-tenant-rbac.py"
spec = importlib.util.spec_from_file_location("tenant_rbac_evidence", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TenantRbacEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = yaml.safe_load((ROOT / "local-lab/tenant-config/tenants.yaml").read_text())

    def test_matrix_covers_role_permissions_and_cross_tenant_denials(self):
        cases = module.authorization_cases(self.catalog)
        index = {(case["tenant"], case["role"], case["verb"], case["resource"], case["namespace"]): case
                 for case in cases}
        self.assertTrue(index[("tenant-alpha", "admins", "get", "secrets", "tenant-alpha")]["expectedAllowed"])
        self.assertTrue(index[("tenant-alpha", "developers", "create", "deployments.apps", "tenant-alpha")]["expectedAllowed"])
        self.assertFalse(index[("tenant-alpha", "developers", "get", "secrets", "tenant-alpha")]["expectedAllowed"])
        self.assertFalse(index[("tenant-alpha", "viewers", "create", "deployments.apps", "tenant-alpha")]["expectedAllowed"])
        for role in ("admins", "developers", "viewers"):
            for verb, resource in (("create", "rolebindings.rbac.authorization.k8s.io"),
                                   ("update", "roles.rbac.authorization.k8s.io"),
                                   ("list", "serviceaccounts"),
                                   ("create", "serviceaccounts/token"),
                                   ("create", "pods/exec"),
                                   ("create", "namespaces"),
                                   ("impersonate", "serviceaccounts")):
                self.assertFalse(index[("tenant-alpha", role, verb, resource, "tenant-alpha")]["expectedAllowed"],
                                 (role, verb, resource))
        cross = next(case for case in cases if case["id"] ==
                     "tenant-alpha-admins-deny-tenant-bravo-default-get-secrets")
        self.assertFalse(cross["expectedAllowed"])
        self.assertEqual(cross["group"],
                         "genericoidc_group:///tenants/tenant-alpha/admins")
        self.assertEqual(len(cases), len({case["id"] for case in cases}))

    def test_authorization_result_matches_expected_allow_and_deny(self):
        allowed_case = {
            "id": "allow", "tenant": "tenant-alpha", "role": "developers",
            "namespace": "tenant-alpha", "verb": "create", "resource": "deployments.apps",
            "expectedAllowed": True, "group": "group",
        }
        denied_case = {**allowed_case, "id": "deny", "expectedAllowed": False}
        self.assertTrue(module.run_case(FakeKubectl(0), allowed_case)["passed"])
        self.assertTrue(module.run_case(FakeKubectl(1), denied_case)["passed"])
        self.assertFalse(module.run_case(FakeKubectl(1), allowed_case)["passed"])
        self.assertFalse(module.run_case(FakeKubectl(1, "impersonation forbidden"), denied_case)["passed"])

    def test_evidence_contains_timestamp_expected_and_actual_results(self):
        result = {
            "id": "tenant-alpha-viewer-deny-secret", "tenant": "tenant-alpha",
            "role": "viewers", "namespace": "tenant-alpha", "verb": "get",
            "resource": "secrets", "expectedAllowed": False,
            "group": "genericoidc_group:///tenants/tenant-alpha/viewers",
            "actualAllowed": False, "passed": True, "error": None,
        }
        timestamp = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            json_path, markdown_path = module.write_evidence(
                Path(directory), ["local"], "rancher-local", [result], timestamp)
            evidence = json.loads(json_path.read_text())
            self.assertEqual(evidence["summary"], {"total": 1, "passed": 1, "failed": 0})
            self.assertFalse(evidence["results"][0]["expectedAllowed"])
            self.assertFalse(evidence["results"][0]["actualAllowed"])
            self.assertIn("2026-10-23T12:00:00Z", markdown_path.read_text())
            self.assertIn("does not verify browser login", markdown_path.read_text())


class FakeKubectl:
    def __init__(self, returncode, stderr=""):
        self.returncode = returncode
        self.stderr = stderr

    def run(self, args):
        return type("Result", (), {"returncode": self.returncode, "stderr": self.stderr})()


if __name__ == "__main__":
    unittest.main()
