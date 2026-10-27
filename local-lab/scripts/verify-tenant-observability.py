#!/usr/bin/env python3
"""Verify tenant metrics attribution and deny tenant access to shared dashboards.

Plan-only by default. With --apply, this performs read-only API checks, starts a
localhost-only Prometheus port-forward, and creates one short-lived restricted
probe Pod per tenant. Probe Pods are always removed by their unique run label.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import secrets
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

import yaml

from tenant_catalog import load_catalog

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "local-lab/tenant-config/tenants.yaml"
DEFAULT_OUTPUT = ROOT / "local-lab/evidence/tenant-observability"
DEFAULT_KUBECTL = ROOT / ".secrets/kubectl"
DEFAULT_KUBECONFIG = ROOT / ".secrets/rke2.yaml"
MANAGED_LABEL = "platform.perkforge.io/managed-by"
MANAGED_VALUE = "tenant-foundation"
RUN_LABEL = "platform.perkforge.io/observability-test-run"
IMAGE = "busybox:1.36.1"
PROM_SERVICE = "kube-prometheus-stack-prometheus"
GRAFANA_SERVICE = "kube-prometheus-stack-grafana"
PROM_NAMESPACE = "monitoring"
OPENCOST_NAMESPACE = "opencost"


class Kubectl:
    def __init__(self, executable: str, kubeconfig: str | None, context: str | None):
        self.prefix = [executable]
        if kubeconfig:
            self.prefix += ["--kubeconfig", kubeconfig]
        if context:
            self.prefix += ["--context", context]

    def run(self, args: list[str], *, input_text: str | None = None,
            timeout: int = 90) -> subprocess.CompletedProcess:
        return subprocess.run(self.prefix + args, input=input_text, text=True,
                              capture_output=True, timeout=timeout)

    def json(self, *args: str) -> dict:
        result = subprocess.run(self.prefix + list(args) + ["-o", "json"], check=True,
                                text=True, capture_output=True, timeout=90)
        return json.loads(result.stdout)


def _service_has_endpoints(kubectl: Kubectl, namespace: str, name: str) -> bool:
    endpoints = kubectl.json("get", "endpoints", name, "-n", namespace)
    return any(subset.get("addresses") for subset in endpoints.get("subsets", []))


def check_services(kubectl: Kubectl) -> tuple[dict, dict, dict | None]:
    prom = kubectl.json("get", "service", PROM_SERVICE, "-n", PROM_NAMESPACE)
    grafana = kubectl.json("get", "service", GRAFANA_SERVICE, "-n", PROM_NAMESPACE)
    service_list = kubectl.json("get", "services", "--all-namespaces")
    listed = {(s.get("metadata", {}).get("namespace"), s.get("metadata", {}).get("name")): s
              for s in service_list.get("items", [])}
    opencost = listed.get((OPENCOST_NAMESPACE, "opencost"))  # optional profile component
    for name, service in (("Prometheus", prom), ("Grafana", grafana)):
        spec = service.get("spec", {})
        if spec.get("type", "ClusterIP") != "ClusterIP":
            raise RuntimeError(f"{name} Service is exposed as {spec.get('type')}, expected ClusterIP")
        if not spec.get("clusterIP") or spec.get("clusterIP") == "None":
            raise RuntimeError(f"{name} Service has no ClusterIP")
    for service in service_list.get("items", []):
        service_namespace = service.get("metadata", {}).get("namespace")
        service_type = service.get("spec", {}).get("type", "ClusterIP")
        if service_namespace in {PROM_NAMESPACE, OPENCOST_NAMESPACE} and service_type != "ClusterIP":
            raise RuntimeError(f"observability Service {service_namespace}/"
                               f"{service['metadata']['name']} has external type {service_type}")
    ingresses = kubectl.json("get", "ingresses.networking.k8s.io", "--all-namespaces")
    for ingress in ingresses.get("items", []):
        namespace = ingress.get("metadata", {}).get("namespace")
        if namespace in {PROM_NAMESPACE, OPENCOST_NAMESPACE}:
            raise RuntimeError(f"Ingress {namespace}/{ingress['metadata']['name']} exists in an "
                               "observability namespace that must remain internal")
    targets = {(PROM_NAMESPACE, PROM_SERVICE), (PROM_NAMESPACE, GRAFANA_SERVICE)}
    if opencost:
        targets.add((OPENCOST_NAMESPACE, "opencost"))
    for ns, name in targets:
        if not _service_has_endpoints(kubectl, ns, name):
            raise RuntimeError(f"observability Service {ns}/{name} has no ready endpoints")
    return prom, grafana, opencost


def check_tenant_policy(kubectl: Kubectl, catalog: dict) -> list[dict]:
    rows = []
    for tenant in catalog["tenants"]:
        for env in tenant["environments"]:
            namespace = env["namespace"]
            ns = kubectl.json("get", "namespace", namespace)
            labels = ns.get("metadata", {}).get("labels", {})
            if labels.get("platform.perkforge.io/tenant") != tenant["id"]:
                raise RuntimeError(f"{namespace} tenant label differs from catalog")
            if labels.get(MANAGED_LABEL) != MANAGED_VALUE:
                raise RuntimeError(f"{namespace} is not managed by tenant-foundation")
            policies = kubectl.json("get", "networkpolicies.networking.k8s.io", "-n", namespace)
            allow = next((p for p in policies.get("items", [])
                          if p.get("metadata", {}).get("name") == "allow-tenant-internal-and-dns"), None)
            if allow is None:
                raise RuntimeError(f"{namespace} is missing allow-tenant-internal-and-dns")
            ingress_rules = allow.get("spec", {}).get("ingress", [])
            scrape_allowed = any(
                any(peer.get("namespaceSelector", {}).get("matchLabels", {}).get(
                    "kubernetes.io/metadata.name") == PROM_NAMESPACE and
                    peer.get("podSelector", {}).get("matchLabels", {}).get(
                    "app.kubernetes.io/name") == "prometheus"
                    for peer in rule.get("from", [])) for rule in ingress_rules)
            if not scrape_allowed:
                raise RuntimeError(f"{namespace} does not permit ingress from the Prometheus collector")
            egress = allow.get("spec", {}).get("egress", [])
            # Tenant egress is deliberately limited to tenant peers, DNS, and Keycloak.
            if any("monitoring" in json.dumps(rule).lower() or "grafana" in json.dumps(rule).lower()
                   or "prometheus" in json.dumps(rule).lower() for rule in egress):
                raise RuntimeError(f"{namespace} policy appears to allow tenant egress to observability")
            rows.append({"id": "tenant-observability-egress-policy", "tenant": tenant["id"],
                         "namespace": namespace, "expected": "deny", "actual": "policy denies",
                         "passed": True, "detail": "tenant policy has no Prometheus/Grafana egress exception"})
    return rows


def probe_pod(namespace: str, run_id: str) -> dict:
    return {"apiVersion": "v1", "kind": "Pod", "metadata": {
        "name": f"pf-observe-{run_id}", "namespace": namespace,
        "labels": {RUN_LABEL: run_id, "app.kubernetes.io/name": "tenant-observability-probe"},
        "annotations": {"platform.perkforge.io/test-resource": "disposable"}},
        "spec": {"restartPolicy": "Never", "automountServiceAccountToken": False,
        "containers": [{"name": "probe", "image": IMAGE, "imagePullPolicy": "IfNotPresent",
            "command": ["sh", "-c", "sleep 3600"],
            "securityContext": {"allowPrivilegeEscalation": False, "runAsNonRoot": True,
                "runAsUser": 10000, "readOnlyRootFilesystem": True,
                "capabilities": {"drop": ["ALL"]},
                "seccompProfile": {"type": "RuntimeDefault"}},
            "resources": {"requests": {"cpu": "10m", "memory": "16Mi"},
                          "limits": {"cpu": "100m", "memory": "64Mi"}}}]}}


def wait_ready(kubectl: Kubectl, namespace: str, name: str) -> None:
    result = kubectl.run(["wait", "--for=condition=Ready", f"pod/{name}", "-n", namespace,
                          "--timeout=120s"], timeout=130)
    if result.returncode:
        raise RuntimeError(f"observability probe did not become ready in {namespace}")


def check_denied(kubectl: Kubectl, namespace: str, pod_name: str,
                 service_name: str, port: int) -> dict:
    fqdn = f"{service_name}.{PROM_NAMESPACE}.svc.cluster.local"
    dns = kubectl.run(["exec", pod_name, "-n", namespace, "--", "nslookup", fqdn], timeout=20)
    if dns.returncode:
        return {"actual": "unknown", "expected": "DNS allowed, service denied", "passed": False,
                "detail": "service DNS lookup failed; network denial cannot be established"}
    request = kubectl.run(["exec", pod_name, "-n", namespace, "--", "wget", "-q", "-T", "4",
                           "-t", "1", "-O", "/dev/null", f"http://{fqdn}:{port}/"], timeout=20)
    denied = request.returncode != 0
    return {"actual": "deny" if denied else "allow", "expected": "deny", "passed": denied,
            "detail": "DNS resolved and HTTP access was denied" if denied
            else "tenant probe reached the shared service"}


def scrape_label_check(port: int, expectations: dict[str, dict[str, str]]) -> dict:
    query = 'kube_namespace_labels{label_platform_perkforge_io_tenant!=""}'
    url = f"http://127.0.0.1:{port}/api/v1/query?query=" + quote(query)
    try:
        with urlopen(url, timeout=10) as response:
            payload = json.load(response)
    except (OSError, URLError, json.JSONDecodeError) as exc:
        return {"actual": "query failed", "expected": "tenant namespace labels present",
                "passed": False, "detail": f"Prometheus query failed: {type(exc).__name__}"}
    if payload.get("status") != "success":
        return {"actual": "query failed", "expected": "tenant namespace labels present",
                "passed": False, "detail": "Prometheus API did not return a successful query"}
    # Compare required attribution labels, but never retain sample values in evidence.
    observed = {sample.get("metric", {}).get("namespace"): sample.get("metric", {})
                for sample in payload.get("data", {}).get("result", [])}
    missing = []
    for namespace, expected in expectations.items():
        labels = observed.get(namespace, {})
        if any(labels.get(key) != value for key, value in expected.items()):
            missing.append(namespace)
    return {"actual": "present" if not missing else "missing or incorrect attribution labels",
            "expected": "all catalog tenant/environment/isolation labels present",
            "passed": not missing,
            "detail": "tenant, environment, and isolation labels are queryable" if not missing
            else "one or more tenant namespaces are absent or have incorrect attribution labels"}


def cleanup(kubectl: Kubectl, namespaces: list[str], run_id: str) -> list[str]:
    errors = []
    for namespace in sorted(set(namespaces)):
        result = kubectl.run(["delete", "pods", "-n", namespace, "-l", f"{RUN_LABEL}={run_id}",
                              "--ignore-not-found=true", "--wait=true", "--timeout=60s"], timeout=70)
        if result.returncode:
            errors.append(namespace)
    return errors


def write_evidence(output: Path, context: str, cluster: str, rows: list[dict], timestamp: dt.datetime):
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = timestamp.strftime("%Y%m%dT%H%M%SZ")
    jp, mp = output / f"tenant-observability-{stamp}.json", output / f"tenant-observability-{stamp}.md"
    data = {"schemaVersion": "perkforge.security-evidence/v1alpha1",
            "testSuite": "tenant-observability-isolation", "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
            "cluster": cluster, "kubectlContext": context,
            "method": "Prometheus namespace-label query and restricted disposable tenant Pods querying shared services",
            "limitations": ["A live passing request proves policy behavior only for this cluster and moment.",
                            "Prometheus query results are reduced to namespace names; metric values are not recorded.",
                            "Grafana access is tested at the HTTP service endpoint; it does not test dashboard data-source authorization."],
            "summary": {"total": len(rows), "passed": sum(bool(r["passed"]) for r in rows),
                        "failed": sum(not r["passed"] for r in rows)}, "results": rows}
    jp.write_text(json.dumps(data, indent=2) + "\n")
    lines = ["# Tenant observability evidence", "", f"- Timestamp: `{data['timestamp']}`",
             f"- Cluster: `{cluster}`", f"- Context: `{context}`",
             f"- Result: **{data['summary']['passed']}/{data['summary']['total']} passed**", "",
             "| Test | Tenant / scope | Expected | Actual | Result |", "|---|---|---|---|---|"]
    for row in rows:
        lines.append(f"| `{row['id']}` | `{row.get('namespace', row.get('service', 'platform'))}` | "
                     f"{row['expected']} | {row['actual']} | {'PASS' if row['passed'] else 'FAIL'} |")
    mp.write_text("\n".join(lines) + "\n")
    return jp, mp


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--kubectl", default=str(DEFAULT_KUBECTL))
    parser.add_argument("--kubeconfig", default=str(DEFAULT_KUBECONFIG))
    parser.add_argument("--context")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--apply", action="store_true", help="run live checks and create disposable probe Pods")
    args = parser.parse_args()
    try:
        catalog = load_catalog(args.catalog)
        tenants = catalog["tenants"]
        expectations = {}
        for tenant in tenants:
            for env in tenant["environments"]:
                expectations[env["namespace"]] = {
                    "label_platform_perkforge_io_tenant": tenant["id"],
                    "label_platform_perkforge_io_environment": env["name"],
                    "label_platform_perkforge_io_isolation_tier": tenant["isolation"]["tier"],
                }
        namespaces = list(expectations)
        if not namespaces:
            raise ValueError("tenant catalog contains no namespaces")
        if not args.apply:
            print("Plan only; no Kubernetes API requests made.")
            print(f"Would check tenant namespace labels/policies for {len(namespaces)} namespace(s), "
                  "Prometheus label attribution, and tenant denial to Prometheus/Grafana.")
            print("Re-run with --apply to run live checks and write evidence.")
            return 0

        kubectl = Kubectl(args.kubectl, args.kubeconfig, args.context)
        prom, grafana, _ = check_services(kubectl)
        rows = check_tenant_policy(kubectl, catalog)
        run_id = secrets.token_hex(4)
        docs = [probe_pod(ns, run_id) for ns in namespaces]
        payload = yaml.safe_dump_all(docs, explicit_start=True, sort_keys=False)
        apply_error = None
        cleanup_errors = []
        port = 19090 + int(run_id[:2], 16)
        port_forward = None
        try:
            applied = kubectl.run(["apply", "-f", "-"], input_text=payload)
            if applied.returncode:
                raise RuntimeError("could not create restricted observability probes; check namespace quota/capacity")
            for ns in namespaces:
                wait_ready(kubectl, ns, f"pf-observe-{run_id}")
            port_forward = subprocess.Popen(kubectl.prefix + ["port-forward", "-n", PROM_NAMESPACE,
                f"service/{PROM_SERVICE}", f"{port}:9090", "--address=127.0.0.1"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            if port_forward.poll() is not None:
                raise RuntimeError("Prometheus localhost port-forward failed")
            rows.append({"id": "prometheus-tenant-label-attribution", "service": PROM_SERVICE,
                         **scrape_label_check(port, expectations)})
            for tenant, env in ((t, e) for t in tenants for e in t["environments"]):
                name = f"pf-observe-{run_id}"
                for service, target_port in ((PROM_SERVICE, 9090), (GRAFANA_SERVICE, 80)):
                    rows.append({"id": "tenant-shared-observability-denied", "tenant": tenant["id"],
                                 "namespace": env["namespace"], "service": service,
                                 **check_denied(kubectl, env["namespace"], name, service, target_port)})
        except (RuntimeError, subprocess.SubprocessError) as exc:
            apply_error = str(exc)
            rows.append({"id": "observability-probe-setup", "expected": "checks completed",
                         "actual": "error", "passed": False,
                         "detail": "live probe setup or execution failed"})
        finally:
            if port_forward is not None:
                port_forward.terminate()
                try:
                    port_forward.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    port_forward.kill()
            cleanup_errors = cleanup(kubectl, namespaces, run_id)
        if cleanup_errors:
            rows.append({"id": "observability-probe-cleanup", "namespace": ",".join(cleanup_errors),
                         "expected": "deleted", "actual": "resources may remain", "passed": False,
                         "detail": "cleanup failed in one or more tenant namespaces"})
        current = kubectl.run(["config", "current-context"])
        cluster = kubectl.run(["config", "view", "--minify", "-o", "jsonpath={.clusters[0].name}"])
        jp, mp = write_evidence(args.output_dir, args.context or current.stdout.strip() or "unknown",
                                cluster.stdout.strip() or "unknown", rows, dt.datetime.now(dt.timezone.utc))
        failed = sum(not row["passed"] for row in rows)
        print(f"Observability evidence: {len(rows) - failed}/{len(rows)} passed; {failed} failed.")
        print(f"JSON: {jp}\nMarkdown: {mp}")
        if apply_error:
            print(f"Probe setup failed: {apply_error}", file=sys.stderr)
            return 2
        return 2 if cleanup_errors else (1 if failed else 0)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"tenant observability verification could not run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
