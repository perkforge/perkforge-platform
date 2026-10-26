import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "local-lab/scripts/verify-tenant-observability.py"
spec = importlib.util.spec_from_file_location("tenant_observability_evidence", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ObservabilityVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = yaml.safe_load((ROOT / "local-lab/tenant-config/tenants.yaml").read_text())

    def test_default_mode_is_plan_only_and_does_not_call_kubectl_or_write_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with patch("sys.argv", [str(SCRIPT), "--kubectl", "/missing/kubectl",
                                     "--output-dir", directory]), redirect_stdout(output):
                result = module.main()
            self.assertEqual(result, 0)
            self.assertIn("Plan only; no Kubernetes API requests made", output.getvalue())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_probe_pod_is_restricted_and_has_no_service_account_token(self):
        pod = module.probe_pod("tenant-alpha", "deadbeef")
        self.assertFalse(pod["spec"]["automountServiceAccountToken"])
        self.assertEqual(pod["metadata"]["labels"][module.RUN_LABEL], "deadbeef")
        security = pod["spec"]["containers"][0]["securityContext"]
        self.assertTrue(security["runAsNonRoot"])
        self.assertTrue(security["readOnlyRootFilesystem"])
        self.assertEqual(security["capabilities"]["drop"], ["ALL"])

    def test_tenant_policy_requires_scrape_ingress_and_no_observability_egress(self):
        alpha = self.catalog["tenants"][0]
        namespace = alpha["environments"][0]["namespace"]
        valid = {"metadata": {"labels": {
            "platform.perkforge.io/tenant": alpha["id"],
            module.MANAGED_LABEL: module.MANAGED_VALUE}}}
        policy = {"metadata": {"name": "allow-tenant-internal-and-dns"}, "spec": {
            "ingress": [{"from": [{"namespaceSelector": {"matchLabels": {
                "kubernetes.io/metadata.name": module.PROM_NAMESPACE}},
                "podSelector": {"matchLabels": {"app.kubernetes.io/name": "prometheus"}}}]}],
            "egress": [{"to": [{"namespaceSelector": {"matchLabels": {
                "platform.perkforge.io/tenant": alpha["id"]}}}]}]}}
        fake = JsonKubectl({
            ("get", "namespace", namespace): valid,
            ("get", "networkpolicies.networking.k8s.io", "-n", namespace): {"items": [policy]},
        })
        rows = module.check_tenant_policy(fake, {"tenants": [alpha]})
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["passed"])
        policy["spec"]["egress"].append({"to": [{"namespaceSelector": {"matchLabels": {
            "kubernetes.io/metadata.name": "monitoring"}}}]})
        with self.assertRaisesRegex(RuntimeError, "allow tenant egress"):
            module.check_tenant_policy(fake, {"tenants": [alpha]})

    def test_tenant_policy_requires_prometheus_ingress_selector(self):
        alpha = self.catalog["tenants"][0]
        namespace = alpha["environments"][0]["namespace"]
        fake = JsonKubectl({
            ("get", "namespace", namespace): {"metadata": {"labels": {
                "platform.perkforge.io/tenant": alpha["id"], module.MANAGED_LABEL: module.MANAGED_VALUE}}},
            ("get", "networkpolicies.networking.k8s.io", "-n", namespace): {"items": [{
                "metadata": {"name": "allow-tenant-internal-and-dns"},
                "spec": {"ingress": [], "egress": []}}]},
        })
        with self.assertRaisesRegex(RuntimeError, "does not permit ingress"):
            module.check_tenant_policy(fake, {"tenants": [alpha]})

    def test_service_exposure_rejects_ingress_route_or_non_clusterip(self):
        prom = service(module.PROM_SERVICE, module.PROM_NAMESPACE)
        grafana = service(module.GRAFANA_SERVICE, module.PROM_NAMESPACE)
        opencost = service("opencost", module.OPENCOST_NAMESPACE)
        fake = JsonKubectl({
            ("get", "service", module.PROM_SERVICE, "-n", module.PROM_NAMESPACE): prom,
            ("get", "service", module.GRAFANA_SERVICE, "-n", module.PROM_NAMESPACE): grafana,
            ("get", "services", "--all-namespaces"): {"items": [prom, grafana, opencost]},
            ("get", "ingresses.networking.k8s.io", "--all-namespaces"): {"items": [{
                "metadata": {"namespace": module.PROM_NAMESPACE, "name": "public-monitoring"},
                "spec": {"rules": [{"http": {"paths": [{"backend": {"service": {
                    "name": module.GRAFANA_SERVICE}}}]}}]}}]},
        })
        with self.assertRaisesRegex(RuntimeError, "Ingress .* observability namespace"):
            module.check_services(fake)

        prom["spec"]["type"] = "NodePort"
        with self.assertRaisesRegex(RuntimeError, "Prometheus Service is exposed as NodePort"):
            module.check_services(fake)

    def test_any_non_clusterip_service_in_observability_namespaces_is_rejected(self):
        prom = service(module.PROM_SERVICE, module.PROM_NAMESPACE)
        grafana = service(module.GRAFANA_SERVICE, module.PROM_NAMESPACE)
        rogue = service("alternate-grafana", module.PROM_NAMESPACE)
        rogue["spec"]["type"] = "LoadBalancer"
        fake = JsonKubectl({
            ("get", "service", module.PROM_SERVICE, "-n", module.PROM_NAMESPACE): prom,
            ("get", "service", module.GRAFANA_SERVICE, "-n", module.PROM_NAMESPACE): grafana,
            ("get", "services", "--all-namespaces"): {"items": [prom, grafana, rogue]},
        })
        with self.assertRaisesRegex(RuntimeError, "alternate-grafana has external type LoadBalancer"):
            module.check_services(fake)

    def test_prometheus_label_query_checks_tenant_environment_and_tier_without_emitting_samples(self):
        expectations = {"tenant-alpha": {
            "label_platform_perkforge_io_tenant": "tenant-alpha",
            "label_platform_perkforge_io_environment": "default",
            "label_platform_perkforge_io_isolation_tier": "shared"}}
        response = {"status": "success", "data": {"result": [{"metric": {
            "namespace": "tenant-alpha", **expectations["tenant-alpha"]}, "value": ["1", "1"]}]}}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps(response).encode()
        with patch.object(module, "urlopen", return_value=Response()) as open_url:
            result = module.scrape_label_check(19090, expectations)
        self.assertTrue(result["passed"])
        self.assertNotIn("tenant-alpha", json.dumps(result))
        self.assertIn("label_platform_perkforge_io_tenant", open_url.call_args.args[0])
        response["data"]["result"][0]["metric"]["label_platform_perkforge_io_environment"] = "wrong"
        with patch.object(module, "urlopen", return_value=Response()):
            self.assertFalse(module.scrape_label_check(19090, expectations)["passed"])

    def test_denial_requires_successful_dns_before_http_failure_counts(self):
        dns_failure = CommandKubectl({"nslookup": (1, ""), "wget": (1, "")})
        self.assertFalse(module.check_denied(dns_failure, "tenant-alpha", "probe", "prom", 9090)["passed"])
        denied = CommandKubectl({"nslookup": (0, "Address"), "wget": (1, "")})
        self.assertTrue(module.check_denied(denied, "tenant-alpha", "probe", "prom", 9090)["passed"])
        open_access = CommandKubectl({"nslookup": (0, "Address"), "wget": (0, "")})
        self.assertFalse(module.check_denied(open_access, "tenant-alpha", "probe", "prom", 9090)["passed"])


class JsonKubectl:
    def __init__(self, responses): self.responses = responses
    def json(self, *args): return self.responses[tuple(args)]


class CommandKubectl:
    def __init__(self, responses): self.responses = responses
    def run(self, args, **kwargs):
        key = args[args.index("--") + 1]
        code, stdout = self.responses[key]
        return type("Result", (), {"returncode": code, "stdout": stdout, "stderr": ""})()


def service(name, namespace):
    return {"metadata": {"name": name, "namespace": namespace},
            "spec": {"type": "ClusterIP", "clusterIP": "10.0.0.1"}}


if __name__ == "__main__":
    unittest.main()
