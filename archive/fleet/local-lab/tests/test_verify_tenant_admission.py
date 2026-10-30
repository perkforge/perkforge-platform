import importlib.util
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "local-lab/scripts"))
from tenant_catalog import load_catalog
SCRIPT = ROOT / "local-lab/scripts/verify-tenant-admission.py"
spec = importlib.util.spec_from_file_location("tenant_admission_evidence", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TenantAdmissionEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(ROOT / "local-lab/tenant-config/tenants.yaml")
        cls.catalog["tenants"] = [t for t in cls.catalog["tenants"]
                                  if t.get("classification") != "protected"]

    def test_matrix_covers_restricted_runtime_and_host_access_controls(self):
        cases = module.admission_cases(self.catalog)
        self.assertEqual(len(cases), 9)
        self.assertEqual(cases[0]["expected"], "allow")
        self.assertTrue(all(case["expected"] == "deny" for case in cases[1:]))

    def test_positive_manifest_has_restricted_security_context(self):
        pod = module.pod_manifest(module.admission_cases(self.catalog)[0], "123456")
        self.assertFalse(pod["spec"]["automountServiceAccountToken"])
        security = pod["spec"]["containers"][0]["securityContext"]
        self.assertTrue(security["runAsNonRoot"])
        self.assertFalse(security["allowPrivilegeEscalation"])
        self.assertEqual(security["capabilities"]["drop"], ["ALL"])
        self.assertEqual(security["seccompProfile"]["type"], "RuntimeDefault")

    def test_privileged_probe_reaches_pod_security_admission(self):
        case = module.admission_cases(self.catalog)[1]
        pod = module.pod_manifest(case, "123456")
        security = pod["spec"]["containers"][0]["securityContext"]
        self.assertTrue(security["privileged"])
        self.assertTrue(security["allowPrivilegeEscalation"])

    def test_negative_case_requires_actual_pod_security_denial(self):
        case = module.admission_cases(self.catalog)[1]
        self.assertTrue(module.run_case(FakeKubectl(1, stderr='violates PodSecurity "restricted"'),
                                        case, "123456")["passed"])
        self.assertFalse(module.run_case(FakeKubectl(1, stderr="Forbidden"), case, "123456")["passed"])
        self.assertFalse(module.run_case(FakeKubectl(0), case, "123456")["passed"])
        self.assertTrue(module.run_case(FakeKubectl(0), module.admission_cases(self.catalog)[0],
                                        "123456")["passed"])

    def test_evidence_marks_server_side_dry_run_limitation(self):
        result = {"id": "privileged-container", "namespace": "tenant-alpha", "expected": "deny",
                  "actual": "deny", "denialSource": "PodSecurity Admission", "passed": True}
        with tempfile.TemporaryDirectory() as directory:
            json_path, markdown_path = module.write_evidence(
                Path(directory), "rancher-local", "local",
                [result], datetime(2026, 10, 23, tzinfo=timezone.utc))
            evidence = json.loads(json_path.read_text())
            self.assertEqual(evidence["summary"]["passed"], 1)
            self.assertIn("are persisted", evidence["limitations"][0])
            self.assertIn("PodSecurity Admission", markdown_path.read_text())


class FakeKubectl:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr

    def run(self, args, input_text=None):
        return type("Result", (), {"returncode": self.returncode,
                                   "stdout": self.stdout, "stderr": self.stderr})()


if __name__ == "__main__":
    unittest.main()
