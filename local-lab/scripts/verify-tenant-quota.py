#!/usr/bin/env python3
"""Verify ResourceQuota enforcement and LimitRange defaults with server dry-runs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "local-lab/tenant-config/tenants.yaml"
DEFAULT_OUTPUT = ROOT / "local-lab/evidence/tenant-quota"
DEFAULT_KUBECTL = ROOT / ".secrets/kubectl"
DEFAULT_KUBECONFIG = ROOT / ".secrets/rke2.yaml"
RANCHER_QUOTA_KEYS = {
    "pods": "pods",
    "requests.cpu": "requestsCpu",
    "requests.memory": "requestsMemory",
    "limits.cpu": "limitsCpu",
    "limits.memory": "limitsMemory",
    "persistentvolumeclaims": "persistentVolumeClaims",
    "requests.storage": "requestsStorage",
    "services": "services",
}


def rancher_limits(values: dict) -> dict:
    return {RANCHER_QUOTA_KEYS[key]: str(value) for key, value in values.items()}


def project_quota_errors(tenant: dict, environment: dict, management_cluster: str,
                         project: dict, namespace: dict) -> list[str]:
    """Check Rancher project ceilings and the namespace's reserved allocation."""
    tenant_id = tenant["id"]
    project_id = f"p-{tenant_id}-{tenant['cluster']}"
    expected_project = rancher_limits(tenant["resources"]["budget"])
    expected_namespace = {"limit": rancher_limits(environment["allocation"])}
    expected_project_ref = f"{tenant['cluster']}:{project_id}"
    errors = []

    metadata = project.get("metadata", {})
    labels = metadata.get("labels", {})
    if metadata.get("name") != project_id:
        errors.append("project identity")
    if metadata.get("namespace") != management_cluster:
        errors.append("project management namespace")
    if labels.get("platform.perkforge.io/tenant") != tenant_id or \
            labels.get("platform.perkforge.io/managed-by") != "tenant-foundation":
        errors.append("project ownership labels")
    spec = project.get("spec", {})
    if spec.get("clusterName") != tenant["cluster"]:
        errors.append("project target cluster")
    if spec.get("resourceQuota", {}).get("limit") != expected_project:
        errors.append("Rancher project quota ceiling")
    if spec.get("namespaceDefaultResourceQuota", {}).get("limit") != expected_project:
        errors.append("Rancher namespace default quota")

    ns_metadata = namespace.get("metadata", {})
    annotations = ns_metadata.get("annotations", {})
    if ns_metadata.get("name") != environment["namespace"]:
        errors.append("namespace identity")
    if ns_metadata.get("labels", {}).get("platform.perkforge.io/tenant") != tenant_id:
        errors.append("namespace tenant label")
    if annotations.get("field.cattle.io/projectId") != expected_project_ref:
        errors.append("namespace Rancher project association")
    try:
        actual_namespace_quota = json.loads(annotations.get("field.cattle.io/resourceQuota", "{}"))
    except json.JSONDecodeError:
        actual_namespace_quota = None
    if actual_namespace_quota != expected_namespace:
        errors.append("namespace reserved project quota allocation")
    return errors


class Kubectl:
    def __init__(self, executable: str, kubeconfig: str | None, context: str | None):
        self.prefix = [executable]
        if kubeconfig:
            self.prefix += ["--kubeconfig", kubeconfig]
        if context:
            self.prefix += ["--context", context]

    def run(self, args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(self.prefix + args, input=input_text, text=True, capture_output=True)

    def json(self, *args: str) -> dict:
        return json.loads(subprocess.run(self.prefix + list(args) + ["-o", "json"], check=True,
                                         text=True, capture_output=True).stdout)


def quota_cases(catalog: dict) -> list[dict]:
    tenant = catalog["tenants"][0]
    env = tenant["environments"][0]
    return [
        {"id": "limitrange-defaults", "namespace": env["namespace"], "kind": "Pod",
         "expected": "allow", "mutation": "defaults"},
        {"id": "within-resource-budget", "namespace": env["namespace"], "kind": "Pod",
         "expected": "allow", "mutation": "within"},
        {"id": "requests-cpu-over-budget", "namespace": env["namespace"], "kind": "Pod",
         "expected": "deny", "mutation": "cpu"},
        {"id": "requests-memory-over-budget", "namespace": env["namespace"], "kind": "Pod",
         "expected": "deny", "mutation": "memory"},
    ]


def pod_manifest(case: dict, suffix: str) -> dict:
    container = {"name": "probe", "image": "busybox:1.36.1", "command": ["sh", "-c", "true"],
                 "securityContext": {"allowPrivilegeEscalation": False, "runAsNonRoot": True,
                    "runAsUser": 10000, "capabilities": {"drop": ["ALL"]},
                    "seccompProfile": {"type": "RuntimeDefault"}}}
    if case["mutation"] != "defaults":
        requests = {"cpu": "100m", "memory": "128Mi"}
        limits = {"cpu": "500m", "memory": "512Mi"}
        if case["mutation"] == "cpu":
            requests["cpu"], limits["cpu"] = "1200m", "1500m"
        if case["mutation"] == "memory":
            requests["memory"], limits["memory"] = "1600Mi", "1800Mi"
        container["resources"] = {"requests": requests, "limits": limits}
    return {"apiVersion": "v1", "kind": "Pod",
            "metadata": {"name": f"pf-quota-{case['mutation']}-{suffix}", "namespace": case["namespace"]},
            "spec": {"containers": [container], "automountServiceAccountToken": False}}


def preflight(catalog: dict, kubectl: Kubectl) -> None:
    for tenant in catalog["tenants"]:
        project_id = f"p-{tenant['id']}-{tenant['cluster']}"
        project = kubectl.json("get", "projects.management.cattle.io", project_id,
                               "--namespace", catalog["rancherManagementCluster"])
        for environment in tenant["environments"]:
            namespace = environment["namespace"]
            ns = kubectl.json("get", "namespace", namespace)
            errors = project_quota_errors(tenant, environment,
                                          catalog["rancherManagementCluster"], project, ns)
            if errors:
                raise RuntimeError(f"Rancher tenant quota configuration differs from catalog for {namespace}: " +
                                   ", ".join(errors))
            labels = ns.get("metadata", {}).get("labels", {})
            if labels.get("platform.perkforge.io/tenant") != tenant["id"]:
                raise RuntimeError(f"namespace {namespace} is not labeled for the catalog tenant")
            quota = kubectl.json("get", "resourcequota", "tenant-budget", "-n", namespace)
            expected = environment["allocation"]
            for key, value in expected.items():
                if str(quota.get("spec", {}).get("hard", {}).get(key)) != str(value):
                    raise RuntimeError(f"tenant-budget quota in {namespace} does not match catalog key {key}")
            kubectl.json("get", "limitrange", "tenant-defaults", "-n", namespace)


def run_case(kubectl: Kubectl, case: dict, suffix: str, defaults: dict) -> dict:
    manifest = yaml.safe_dump(pod_manifest(case, suffix), sort_keys=False)
    result = kubectl.run(["create", "--dry-run=server", "-f", "-", "-o", "json"], manifest)
    allowed = result.returncode == 0
    quota_denial = "exceeded quota" in result.stderr.lower()
    error = None
    details = "server-side dry-run admitted request" if allowed else \
        "ResourceQuota rejected the request" if quota_denial else \
        "request failed for a reason other than the expected ResourceQuota denial"
    if case["mutation"] == "defaults" and allowed:
        try:
            obj = json.loads(result.stdout)
            resources = obj["spec"]["containers"][0]["resources"]
            actual = {"requestCpu": resources["requests"]["cpu"],
                      "requestMemory": resources["requests"]["memory"],
                      "limitCpu": resources["limits"]["cpu"],
                      "limitMemory": resources["limits"]["memory"]}
            passed = actual == defaults
            details = "LimitRange injected catalog defaults" if passed else "LimitRange defaults differ from catalog"
        except (ValueError, KeyError, TypeError):
            actual, passed = {}, False
            details = "server dry-run output did not include defaulted resources"
    else:
        actual = "allow" if allowed else "deny"
        passed = allowed if case["expected"] == "allow" else (not allowed and quota_denial)
    return {**case, "actual": actual, "denialSource": "ResourceQuota" if quota_denial else None,
            "passed": passed, "detail": details}


def write_evidence(output: Path, context: str, cluster: str, results: list[dict], timestamp: dt.datetime):
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = timestamp.strftime("%Y%m%dT%H%M%SZ")
    jp, mp = output / f"tenant-quota-{stamp}.json", output / f"tenant-quota-{stamp}.md"
    data = {"schemaVersion": "perkforge.security-evidence/v1alpha1", "testSuite": "tenant-resource-governance",
            "timestamp": timestamp.isoformat().replace("+00:00", "Z"), "cluster": cluster,
            "kubectlContext": context,
            "method": "Rancher project and namespace quota configuration preflight plus API server-side dry-run Pod creates evaluated by ResourceQuota and LimitRange",
            "limitations": ["Dry-run requests do not persist Pods.",
                            "Preflight verifies the Rancher project ceiling and namespace reservation configuration; it does not exercise aggregate quota consumption across multiple namespaces.",
                            "Tests namespace quota admission only; it does not measure runtime CPU throttling."],
            "summary": {"total": len(results), "passed": sum(bool(r["passed"]) for r in results),
                        "failed": sum(not r["passed"] for r in results)}, "results": results}
    jp.write_text(json.dumps(data, indent=2) + "\n")
    lines = ["# Tenant resource quota evidence", "", f"- Timestamp: `{data['timestamp']}`",
             f"- Cluster: `{cluster}`", f"- Context: `{context}`",
             f"- Result: **{data['summary']['passed']}/{data['summary']['total']} passed**",
             "- Method: API server-side dry-run; no Pods are persisted.", "",
             "| Test | Namespace | Expected | Actual | Denial source | Result |", "|---|---|---|---|---|---|"]
    for row in results:
        actual = json.dumps(row["actual"], sort_keys=True) if isinstance(row["actual"], dict) else row["actual"]
        lines.append(f"| `{row['id']}` | `{row['namespace']}` | {row['expected']} | `{actual}` | "
                     f"{row.get('denialSource') or '—'} | {'PASS' if row['passed'] else 'FAIL'} |")
    mp.write_text("\n".join(lines) + "\n")
    return jp, mp


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--kubectl", default=str(DEFAULT_KUBECTL))
    parser.add_argument("--kubeconfig", default=str(DEFAULT_KUBECONFIG))
    parser.add_argument("--context")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--apply", action="store_true", help="send non-persisting server dry-run requests")
    args = parser.parse_args()
    try:
        catalog = yaml.safe_load(args.catalog.read_text())
        cases = quota_cases(catalog)
        if not args.apply:
            print("Plan only; no API requests sent.")
            print(f"Would dry-run {len(cases)} Pods in {cases[0]['namespace']} against its ResourceQuota and LimitRange.")
            return 0
        kubectl = Kubectl(args.kubectl, args.kubeconfig, args.context)
        preflight(catalog, kubectl)
        defaults = {"requestCpu": str(catalog["tenants"][0]["resources"]["defaults"]["requestCpu"]),
                    "requestMemory": str(catalog["tenants"][0]["resources"]["defaults"]["requestMemory"]),
                    "limitCpu": str(catalog["tenants"][0]["resources"]["defaults"]["limitCpu"]),
                    "limitMemory": str(catalog["tenants"][0]["resources"]["defaults"]["limitMemory"])}
        suffix = dt.datetime.now(dt.timezone.utc).strftime("%H%M%S")
        results = [run_case(kubectl, case, suffix, defaults) for case in cases]
        current = kubectl.run(["config", "current-context"])
        cluster = kubectl.run(["config", "view", "--minify", "-o", "jsonpath={.clusters[0].name}"])
        jp, mp = write_evidence(args.output_dir, args.context or current.stdout.strip() or "unknown",
            cluster.stdout.strip() or "unknown", results, dt.datetime.now(dt.timezone.utc))
        failed = sum(not row["passed"] for row in results)
        print(f"Quota evidence: {len(results)-failed}/{len(results)} passed; {failed} failed.\nJSON: {jp}\nMarkdown: {mp}")
        return 1 if failed else 0
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"tenant quota verification could not run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
