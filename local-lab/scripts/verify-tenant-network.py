#!/usr/bin/env python3
"""Run disposable HTTP connectivity probes against the catalog tenant policies.

The command is plan-only unless --apply is supplied. Applying creates only
short-lived Pods, Services, and ConfigMaps in catalog-owned tenant namespaces,
then removes resources bearing this run's unique ownership label.
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

import yaml

from tenant_catalog import load_catalog

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "local-lab/tenant-config/tenants.yaml"
DEFAULT_OUTPUT = ROOT / "local-lab/evidence/tenant-network"
DEFAULT_KUBECTL = ROOT / ".secrets/kubectl"
DEFAULT_KUBECONFIG = ROOT / ".secrets/rke2.yaml"
TEST_LABEL = "platform.perkforge.io/network-test-run"
MANAGED_LABEL = "platform.perkforge.io/managed-by"
MANAGED_VALUE = "tenant-foundation"
IMAGE = "busybox:1.36.1"
KEYCLOAK_DISCOVERY_URL = (
    "http://keycloak-keycloakx-http.keycloak.svc.cluster.local:80/"
    "auth/realms/perkforge/.well-known/openid-configuration"
)


class Kubectl:
    def __init__(self, executable: str, kubeconfig: str | None, context: str | None):
        self.prefix = [executable]
        if kubeconfig:
            self.prefix += ["--kubeconfig", kubeconfig]
        if context:
            self.prefix += ["--context", context]

    def run(self, args: list[str], *, input_text: str | None = None,
            timeout: int = 120) -> subprocess.CompletedProcess:
        return subprocess.run(self.prefix + args, input=input_text, text=True,
                              capture_output=True, timeout=timeout)

    def json(self, *args: str) -> dict:
        result = subprocess.run(self.prefix + list(args) + ["-o", "json"],
                                check=True, text=True, capture_output=True)
        return json.loads(result.stdout)


def build_probes(catalog: dict) -> list[dict]:
    tenants = catalog["tenants"]
    if len(tenants) < 2:
        raise ValueError("network-isolation verification requires at least two tenants")
    alpha, bravo = tenants[0], tenants[1]
    ns_alpha = alpha["environments"][0]["namespace"]
    ns_bravo = bravo["environments"][0]["namespace"]
    return [
        {"id": "alpha-same-tenant-service", "sourceTenant": alpha["id"],
         "sourceNamespace": ns_alpha, "targetTenant": alpha["id"],
         "targetNamespace": ns_alpha, "expected": "allow", "method": "HTTP GET"},
        {"id": "bravo-same-tenant-service", "sourceTenant": bravo["id"],
         "sourceNamespace": ns_bravo, "targetTenant": bravo["id"],
         "targetNamespace": ns_bravo, "expected": "allow", "method": "HTTP GET"},
        {"id": "alpha-to-bravo-denied", "sourceTenant": alpha["id"],
         "sourceNamespace": ns_alpha, "targetTenant": bravo["id"],
         "targetNamespace": ns_bravo, "expected": "deny", "method": "HTTP GET"},
        {"id": "bravo-to-alpha-denied", "sourceTenant": bravo["id"],
         "sourceNamespace": ns_bravo, "targetTenant": alpha["id"],
         "targetNamespace": ns_alpha, "expected": "deny", "method": "HTTP GET"},
        {"id": "alpha-to-keycloak-allowed", "sourceTenant": alpha["id"],
         "sourceNamespace": ns_alpha, "targetTenant": "platform-keycloak",
         "targetNamespace": "keycloak", "expected": "allow",
         "method": "HTTP GET Keycloak OIDC discovery"},
        *[{"id": f"{tenant['id']}-dns-resolution", "sourceTenant": tenant["id"],
           "sourceNamespace": tenant["environments"][0]["namespace"], "targetTenant": None,
           "targetNamespace": None, "expected": "allow",
           "method": "DNS lookup for kubernetes.default.svc.cluster.local"}
          for tenant in (alpha, bravo)],
    ]


def pod(name: str, namespace: str, run_id: str, *, server: bool) -> dict:
    labels = {TEST_LABEL: run_id, "app.kubernetes.io/name": "tenant-network-probe",
              "platform.perkforge.io/network-test-role": "server" if server else "client"}
    container = {
        "name": "probe" if not server else "http-server",
        "image": IMAGE,
        "imagePullPolicy": "IfNotPresent",
        "securityContext": {
            "allowPrivilegeEscalation": False,
            "capabilities": {"drop": ["ALL"]},
            "readOnlyRootFilesystem": True,
            "runAsNonRoot": True,
            "runAsUser": 10000,
            "seccompProfile": {"type": "RuntimeDefault"},
        },
        "resources": {"requests": {"cpu": "10m", "memory": "16Mi"},
                      "limits": {"cpu": "100m", "memory": "64Mi"}},
    }
    if server:
        container.update({
            "image": "busybox:1.36.1",
            "command": ["httpd"], "args": ["-f", "-p", "8080", "-h", "/www"],
            "ports": [{"name": "http", "containerPort": 8080}],
            "volumeMounts": [{"name": "www", "mountPath": "/www", "readOnly": True}],
        })
    else:
        container["command"] = ["sh", "-c", "sleep 3600"]
    spec = {"containers": [container], "restartPolicy": "Never",
            "automountServiceAccountToken": False}
    if server:
        spec["volumes"] = [{"name": "www", "configMap": {"name": name + "-content"}}]
    return {"apiVersion": "v1", "kind": "Pod", "metadata": {
        "name": name, "namespace": namespace, "labels": labels,
        "annotations": {"platform.perkforge.io/test-resource": "disposable"}},
        "spec": spec}


def resources(catalog: dict, run_id: str) -> list[dict]:
    tenants = catalog["tenants"]
    alpha, bravo = tenants[0], tenants[1]
    ns_a = alpha["environments"][0]["namespace"]
    ns_b = bravo["environments"][0]["namespace"]
    names = {"alpha": f"pf-net-{run_id}-a", "bravo": f"pf-net-{run_id}-b",
             "client-alpha": f"pf-net-{run_id}-ca", "client-bravo": f"pf-net-{run_id}-cb"}
    output = []
    for key, namespace in (("alpha", ns_a), ("bravo", ns_b)):
        output.append({"apiVersion": "v1", "kind": "ConfigMap", "metadata": {
            "name": names[key] + "-content", "namespace": namespace,
            "labels": {TEST_LABEL: run_id}},
            "data": {"index.html": f"perkforge-network-probe-{key}"}})
        output.append(pod(names[key], namespace, run_id, server=True))
        output.append({"apiVersion": "v1", "kind": "Service", "metadata": {
            "name": names[key], "namespace": namespace,
            "labels": {TEST_LABEL: run_id}},
            "spec": {"selector": {TEST_LABEL: run_id,
                                   "platform.perkforge.io/network-test-role": "server"},
                      "ports": [{"name": "http", "port": 8080, "targetPort": 8080}]}})
    output.append(pod(names["client-alpha"], ns_a, run_id, server=False))
    output.append(pod(names["client-bravo"], ns_b, run_id, server=False))
    return output


def verify_preflight(catalog: dict, kubectl: Kubectl) -> None:
    for tenant in catalog["tenants"][:2]:
        for environment in tenant["environments"][:1]:
            namespace = environment["namespace"]
            obj = kubectl.json("get", "namespace", namespace)
            labels = obj.get("metadata", {}).get("labels", {})
            if labels.get("platform.perkforge.io/tenant") != tenant["id"]:
                raise RuntimeError(f"namespace {namespace} is not labeled as catalog tenant {tenant['id']}")
            if labels.get(MANAGED_LABEL) != MANAGED_VALUE:
                raise RuntimeError(f"namespace {namespace} is not owned by tenant-foundation")
            policies = kubectl.json("get", "networkpolicies.networking.k8s.io", "-n", namespace)
            policy_names = {item["metadata"]["name"] for item in policies.get("items", [])}
            if not {"default-deny", "allow-tenant-internal-and-dns"}.issubset(policy_names):
                raise RuntimeError(f"namespace {namespace} is missing the expected tenant network policies")


def wait_ready(kubectl: Kubectl, namespace: str, name: str) -> None:
    result = kubectl.run(["wait", "--for=condition=Ready", f"pod/{name}",
                          "-n", namespace, "--timeout=120s"], timeout=130)
    if result.returncode:
        raise RuntimeError(f"probe pod {namespace}/{name} did not become ready")


def service_ip(kubectl: Kubectl, namespace: str, name: str) -> str:
    service = kubectl.json("get", "service", name, "-n", namespace)
    address = service.get("spec", {}).get("clusterIP")
    if not address or address == "None":
        raise RuntimeError(f"test service {namespace}/{name} has no ClusterIP")
    endpoints = kubectl.json("get", "endpoints", name, "-n", namespace)
    if not any(subset.get("addresses") for subset in endpoints.get("subsets", [])):
        raise RuntimeError(f"test service {namespace}/{name} has no ready endpoints")
    return address


def check_http(kubectl: Kubectl, namespace: str, client: str, address: str,
               expected: str, should_allow: bool) -> dict:
    result = kubectl.run(["exec", client, "-n", namespace, "--", "wget", "-q", "-T", "4",
                          "-t", "1", "-O", "-", f"http://{address}:8080/"], timeout=12)
    response_received = result.returncode == 0
    marker_matched = response_received and expected in result.stdout
    passed = marker_matched if should_allow else not response_received
    return {"actual": "allow" if response_received else "deny", "expected": "allow" if should_allow else "deny",
            "passed": passed, "detail": "HTTP probe returned the expected marker" if marker_matched
            else "HTTP request was denied as expected" if not response_received and not should_allow
            else "HTTP response did not contain the expected marker" if response_received
            else "HTTP request failed unexpectedly"}


def check_http_url(kubectl: Kubectl, namespace: str, client: str, url: str,
                   expected: str) -> dict:
    result = kubectl.run(["exec", client, "-n", namespace, "--", "wget", "-q", "-T", "4",
                          "-t", "1", "-O", "-", url], timeout=12)
    passed = result.returncode == 0 and expected in result.stdout
    return {"actual": "allow" if result.returncode == 0 else "deny",
            "expected": "allow", "passed": passed,
            "detail": "Keycloak OIDC discovery endpoint returned the expected issuer" if passed
            else "Keycloak OIDC discovery request failed or returned unexpected content"}


def check_dns(kubectl: Kubectl, namespace: str, client: str) -> dict:
    result = kubectl.run(["exec", client, "-n", namespace, "--", "nslookup",
                          "kubernetes.default.svc.cluster.local"], timeout=12)
    passed = result.returncode == 0 and "Address" in result.stdout
    return {"actual": "allow" if passed else "deny", "expected": "allow", "passed": passed,
            "detail": "Kubernetes service DNS resolved" if passed else "Kubernetes service DNS lookup failed"}


def cleanup(kubectl: Kubectl, namespaces: list[str], run_id: str) -> list[str]:
    errors = []
    selector = f"{TEST_LABEL}={run_id}"
    for namespace in namespaces:
        result = kubectl.run(["delete", "pods,services,configmaps", "-n", namespace,
                              "-l", selector, "--ignore-not-found=true", "--wait=true", "--timeout=60s"],
                             timeout=70)
        if result.returncode:
            errors.append(namespace)
    return errors


def write_evidence(output: Path, run_id: str, context: str, cluster: str,
                   results: list[dict], timestamp: dt.datetime) -> tuple[Path, Path]:
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = timestamp.strftime("%Y%m%dT%H%M%SZ")
    json_path, md_path = output / f"tenant-network-{stamp}.json", output / f"tenant-network-{stamp}.md"
    summary = {"schemaVersion": "perkforge.security-evidence/v1alpha1",
               "testSuite": "tenant-network-isolation", "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
               "testRun": run_id, "cluster": cluster, "kubectlContext": context,
               "method": "short-lived restricted HTTP probe Pods, tenant ClusterIP requests, Keycloak OIDC discovery, and CoreDNS lookup",
               "limitations": ["Tests the installed CNI policies in this cluster; does not establish enforcement on other clusters.",
                               "Cross-tenant denial exercises both source egress and destination ingress policy.",
                               "Does not test external egress, ingress-controller exposure, host networking, or node-local traffic."],
               "summary": {"total": len(results), "passed": sum(bool(r["passed"]) for r in results),
                           "failed": sum(not r["passed"] for r in results)}, "results": results}
    json_path.write_text(json.dumps(summary, indent=2) + "\n")
    lines = ["# Tenant network isolation evidence", "", f"- Timestamp: `{summary['timestamp']}`",
             f"- Cluster: `{cluster}`", f"- Context: `{context}`",
             f"- Result: **{summary['summary']['passed']}/{summary['summary']['total']} passed**",
             "- Probes: restricted, disposable Pods; tenant ClusterIP HTTP, Keycloak OIDC discovery, and CoreDNS lookup.",
             "- Limitation: cross-tenant denial tests combined source egress and destination ingress policy.", "",
             "| Test | Source | Destination | Expected | Actual | Result |", "|---|---|---|---|---|---|"]
    for row in results:
        lines.append(f"| `{row['id']}` | `{row['sourceNamespace']}` | `{row.get('targetNamespace') or 'CoreDNS'}` | "
                     f"{row['expected']} | {row['actual']} | {'PASS' if row['passed'] else 'FAIL'} |")
    md_path.write_text("\n".join(lines) + "\n")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--kubectl", default=str(DEFAULT_KUBECTL))
    parser.add_argument("--kubeconfig", default=str(DEFAULT_KUBECONFIG))
    parser.add_argument("--context")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--apply", action="store_true", help="create temporary probes and run connectivity checks")
    args = parser.parse_args()
    try:
        catalog = load_catalog(args.catalog)
        run_id = secrets.token_hex(4)
        probes = build_probes(catalog)
        if not args.apply:
            print("Plan only; no cluster changes made.")
            print(f"Would create restricted probe Pods and Services in {probes[0]['sourceNamespace']} and {probes[1]['targetNamespace']}.")
            print("Checks include same-tenant allow, cross-tenant deny, Keycloak OIDC access, and CoreDNS.")
            print("Re-run with --apply to execute and clean up the probes.")
            return 0
        kubectl = Kubectl(args.kubectl, args.kubeconfig, args.context)
        verify_preflight(catalog, kubectl)
        docs = resources(catalog, run_id)
        payload = yaml.safe_dump_all(docs, explicit_start=True, sort_keys=False)
        alpha, bravo = catalog["tenants"][:2]
        ns_a, ns_b = alpha["environments"][0]["namespace"], bravo["environments"][0]["namespace"]
        names = {"a": f"pf-net-{run_id}-a", "b": f"pf-net-{run_id}-b",
                 "client-a": f"pf-net-{run_id}-ca", "client-b": f"pf-net-{run_id}-cb"}
        result_rows = []
        apply_error = None
        cleanup_errors = []
        try:
            applied = kubectl.run(["apply", "-f", "-"], input_text=payload)
            if applied.returncode:
                raise RuntimeError("could not create disposable probe resources; verify namespace quotas and available capacity")
            for namespace, name in ((ns_a, names["a"]), (ns_a, names["client-a"]),
                                    (ns_b, names["b"]), (ns_b, names["client-b"])):
                wait_ready(kubectl, namespace, name)
            addr_a = service_ip(kubectl, ns_a, names["a"])
            addr_b = service_ip(kubectl, ns_b, names["b"])
            for probe, namespace, client, address, marker, allowed in (
                (probes[0], ns_a, names["client-a"], addr_a, "perkforge-network-probe-alpha", True),
                (probes[1], ns_b, names["client-b"], addr_b, "perkforge-network-probe-bravo", True),
                (probes[2], ns_a, names["client-a"], addr_b, "perkforge-network-probe-bravo", False),
                (probes[3], ns_b, names["client-b"], addr_a, "perkforge-network-probe-alpha", False),
            ):
                check = check_http(kubectl, namespace, client, address, marker, allowed)
                result_rows.append({**probe, **check})
            keycloak = check_http_url(kubectl, ns_a, names["client-a"],
                                      KEYCLOAK_DISCOVERY_URL, "/auth/realms/perkforge")
            result_rows.append({**probes[4], **keycloak})
            for probe, namespace, client in ((probes[5], ns_a, names["client-a"]),
                                             (probes[6], ns_b, names["client-b"])):
                dns = check_dns(kubectl, namespace, client)
                result_rows.append({**probe, **dns})
        except RuntimeError as exc:
            apply_error = str(exc)
            result_rows.append({"id": "probe-setup", "sourceTenant": alpha["id"],
                "sourceNamespace": ns_a, "targetTenant": bravo["id"],
                "targetNamespace": ns_b, "expected": "complete", "actual": "error",
                "passed": False, "detail": apply_error})
        finally:
            cleanup_errors = cleanup(kubectl, [ns_a, ns_b], run_id)
        if cleanup_errors:
            result_rows.append({"id": "probe-cleanup", "sourceTenant": "platform",
                "sourceNamespace": ",".join(cleanup_errors), "targetTenant": None,
                "targetNamespace": None, "expected": "deleted", "actual": "resources-remain",
                "passed": False, "detail": "cleanup failed in one or more test namespaces"})
        current = kubectl.run(["config", "current-context"])
        cluster = kubectl.run(["config", "view", "--minify", "-o", "jsonpath={.clusters[0].name}"])
        timestamp = dt.datetime.now(dt.timezone.utc)
        json_path, md_path = write_evidence(args.output_dir, run_id,
            args.context or current.stdout.strip() or "unknown",
            cluster.stdout.strip() or "unknown", result_rows, timestamp)
        failed = sum(not row["passed"] for row in result_rows)
        print(f"Network evidence: {len(result_rows) - failed}/{len(result_rows)} passed; {failed} failed.")
        print(f"JSON: {json_path}\nMarkdown: {md_path}")
        if apply_error:
            print(f"Probe setup or execution failed: {apply_error}", file=sys.stderr)
            return 2
        if cleanup_errors:
            print(f"WARNING: temporary resources may remain in namespaces: {', '.join(cleanup_errors)}", file=sys.stderr)
            return 2
        return 1 if failed else 0
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"tenant network verification could not run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
