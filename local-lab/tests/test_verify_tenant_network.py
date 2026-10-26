import importlib.util
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "local-lab/scripts/verify-tenant-network.py"
spec = importlib.util.spec_from_file_location("tenant_network_evidence", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TenantNetworkEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = yaml.safe_load((ROOT / "local-lab/tenant-config/tenants.yaml").read_text())

    def test_probe_matrix_covers_same_tenant_cross_tenant_keycloak_and_dns(self):
        probes = module.build_probes(self.catalog)
        self.assertEqual([probe["id"] for probe in probes],
                         ["alpha-same-tenant-service", "bravo-same-tenant-service",
                          "alpha-to-bravo-denied", "bravo-to-alpha-denied",
                          "alpha-to-keycloak-allowed",
                          "tenant-alpha-dns-resolution", "tenant-bravo-dns-resolution"])
        self.assertEqual([probe["expected"] for probe in probes],
                         ["allow", "allow", "deny", "deny", "allow", "allow", "allow"])
        self.assertEqual(probes[4]["targetNamespace"], "keycloak")
        self.assertEqual(probes[5]["method"], "DNS lookup for kubernetes.default.svc.cluster.local")

    def test_probe_services_only_select_server_pods(self):
        docs = module.resources(self.catalog, "deadbeef")
        services = [item for item in docs if item["kind"] == "Service"]
        pods = [item for item in docs if item["kind"] == "Pod"]
        self.assertEqual(len(services), 2)
        self.assertTrue(all(service["spec"]["selector"]["platform.perkforge.io/network-test-role"] == "server"
                            for service in services))
        self.assertEqual({pod["metadata"]["labels"]["platform.perkforge.io/network-test-role"]
                          for pod in pods}, {"server", "client"})
        self.assertEqual(len(pods), 4)
        self.assertTrue(all(pod["spec"]["automountServiceAccountToken"] is False for pod in pods))
        self.assertTrue(all(pod["spec"]["containers"][0]["securityContext"]["runAsNonRoot"] for pod in pods))
        self.assertTrue(all(pod["spec"]["containers"][0]["securityContext"]["readOnlyRootFilesystem"]
                            for pod in pods))

    def test_http_allow_requires_expected_marker_and_deny_requires_no_response(self):
        self.assertTrue(module.check_http(FakeKubectl(0, "alpha-marker"), "a", "client",
                                          "10.0.0.1", "alpha-marker", True)["passed"])
        self.assertFalse(module.check_http(FakeKubectl(0, "wrong-content"), "a", "client",
                                           "10.0.0.1", "alpha-marker", True)["passed"])
        self.assertTrue(module.check_http(FakeKubectl(1), "a", "client",
                                          "10.0.0.2", "bravo-marker", False)["passed"])
        self.assertFalse(module.check_http(FakeKubectl(0, "unexpected response"), "a", "client",
                                           "10.0.0.2", "bravo-marker", False)["passed"])

    def test_keycloak_probe_requires_expected_oidc_issuer(self):
        result = module.check_http_url(FakeKubectl(0, '"issuer":"/auth/realms/perkforge"'),
                                       "tenant-alpha", "probe", "http://keycloak",
                                       "/auth/realms/perkforge")
        self.assertTrue(result["passed"])
        denied = module.check_http_url(FakeKubectl(1), "tenant-alpha", "probe",
                                       "http://keycloak", "/auth/realms/perkforge")
        self.assertFalse(denied["passed"])

    def test_evidence_records_expected_and_actual_network_results(self):
        results = [{"id": "alpha-to-bravo-denied", "sourceNamespace": "tenant-alpha",
                    "targetNamespace": "tenant-bravo", "expected": "deny", "actual": "deny",
                    "passed": True}]
        timestamp = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            json_path, markdown_path = module.write_evidence(
                Path(directory), "deadbeef", "rancher-local", "local", results, timestamp)
            document = json.loads(json_path.read_text())
            self.assertEqual(document["summary"], {"total": 1, "passed": 1, "failed": 0})
            self.assertEqual(document["results"][0]["expected"], "deny")
            self.assertIn("tests combined source egress and destination ingress", markdown_path.read_text())


class FakeKubectl:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def run(self, args, **kwargs):
        return type("Result", (), {"returncode": self.returncode,
                                   "stdout": self.stdout, "stderr": self.stderr})()


if __name__ == "__main__":
    unittest.main()
