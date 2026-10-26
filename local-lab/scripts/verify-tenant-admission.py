#!/usr/bin/env python3
"""Verify tenant Pod Security Admission with non-persisted server dry-runs."""

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
DEFAULT_OUTPUT = ROOT / "local-lab/evidence/tenant-admission"
DEFAULT_KUBECTL = ROOT / ".secrets/kubectl"
DEFAULT_KUBECONFIG = ROOT / ".secrets/rke2.yaml"


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
        result = subprocess.run(self.prefix + list(args) + ["-o", "json"], check=True,
                                text=True, capture_output=True)
        return json.loads(result.stdout)


def security_context() -> dict:
    return {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]},
            "readOnlyRootFilesystem": True, "runAsNonRoot": True, "runAsUser": 10000,
            "seccompProfile": {"type": "RuntimeDefault"}}


def admission_cases(catalog: dict) -> list[dict]:
    namespace = catalog["tenants"][0]["environments"][0]["namespace"]
    mutations = [
        ("restricted-compliant-pod", "baseline", "allow"),
        ("privileged-container", "privileged", "deny"),
        ("host-network", "hostNetwork", "deny"),
        ("host-pid", "hostPID", "deny"),
        ("host-path-mount", "hostPath", "deny"),
        ("root-user", "root", "deny"),
        ("privilege-escalation", "allowPrivilegeEscalation", "deny"),
        ("unconfined-seccomp", "unconfinedSeccomp", "deny"),
        ("added-capability", "addedCapability", "deny"),
    ]
    return [{"id": name, "namespace": namespace, "expected": expected, "mutation": mutation}
            for name, mutation, expected in mutations]


def pod_manifest(case: dict, suffix: str) -> dict:
    container = {"name": "probe", "image": "busybox:1.36.1", "command": ["sh", "-c", "true"],
                 "securityContext": security_context()}
    spec = {"containers": [container]}
    mutation = case["mutation"]
    if mutation == "privileged":
        container["securityContext"]["privileged"] = True
    elif mutation == "hostNetwork":
        spec["hostNetwork"] = True
    elif mutation == "hostPID":
        spec["hostPID"] = True
    elif mutation == "hostPath":
        spec["volumes"] = [{"name": "host", "hostPath": {"path": "/", "type": "Directory"}}]
        container["volumeMounts"] = [{"name": "host", "mountPath": "/host"}]
    elif mutation == "root":
        container["securityContext"]["runAsUser"] = 0
    elif mutation == "allowPrivilegeEscalation":
        container["securityContext"]["allowPrivilegeEscalation"] = True
    elif mutation == "unconfinedSeccomp":
        container["securityContext"]["seccompProfile"] = {"type": "Unconfined"}
    elif mutation == "addedCapability":
        container["securityContext"]["capabilities"]["add"] = ["NET_ADMIN"]
    return {"apiVersion": "v1", "kind": "Pod",
            "metadata": {"name": f"pf-admission-{case['id']}-{suffix}", "namespace": case["namespace"]},
            "spec": {**spec, "automountServiceAccountToken": False}}


def preflight(catalog: dict, kubectl: Kubectl) -> None:
    tenant = catalog["tenants"][0]
    namespace = tenant["environments"][0]["namespace"]
    obj = kubectl.json("get", "namespace", namespace)
    labels = obj.get("metadata", {}).get("labels", {})
    if labels.get("platform.perkforge.io/tenant") != tenant["id"]:
        raise RuntimeError(f"namespace {namespace} is not labeled for the catalog tenant")
    if labels.get("pod-security.kubernetes.io/enforce") != "restricted":
        raise RuntimeError(f"namespace {namespace} does not enforce Pod Security Restricted")


def run_case(kubectl: Kubectl, case: dict, suffix: str) -> dict:
    manifest = yaml.safe_dump(pod_manifest(case, suffix), sort_keys=False)
    result = kubectl.run(["create", "--dry-run=server", "-f", "-", "-o", "name"], manifest)
    allowed = result.returncode == 0
    psa_denial = "violates PodSecurity" in result.stderr
    passed = allowed if case["expected"] == "allow" else (not allowed and psa_denial)
    detail = ("server-side dry-run admitted request" if allowed else
              "Pod Security Admission rejected the request" if psa_denial else
              "request failed for a reason other than the expected Pod Security denial")
    return {**case, "actual": "allow" if allowed else "deny",
            "denialSource": "PodSecurity Admission" if psa_denial else None,
            "passed": passed, "detail": detail}


def write_evidence(output: Path, context: str, cluster: str, results: list[dict],
                   timestamp: dt.datetime) -> tuple[Path, Path]:
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = timestamp.strftime("%Y%m%dT%H%M%SZ")
    json_path = output / f"tenant-admission-{stamp}.json"
    md_path = output / f"tenant-admission-{stamp}.md"
    summary = {"schemaVersion": "perkforge.security-evidence/v1alpha1",
               "testSuite": "tenant-pod-security-admission",
               "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
               "cluster": cluster, "kubectlContext": context,
               "method": "Kubernetes API server-side dry-run create requests evaluated by namespace Pod Security Admission",
               "limitations": ["No Pods or test resources are persisted by server dry-run.",
                               "This validates Pod Security Admission, not other policies or runtime behavior."],
               "summary": {"total": len(results), "passed": sum(bool(r["passed"]) for r in results),
                           "failed": sum(not r["passed"] for r in results)}, "results": results}
    json_path.write_text(json.dumps(summary, indent=2) + "\n")
    lines = ["# Tenant Pod Security Admission evidence", "",
             f"- Timestamp: `{summary['timestamp']}`", f"- Cluster: `{cluster}`",
             f"- Context: `{context}`", f"- Result: **{summary['summary']['passed']}/{summary['summary']['total']} passed**",
             "- Method: server-side dry-run; requests are not persisted.", "",
             "| Test | Namespace | Expected | Actual | Denial source | Result |", "|---|---|---|---|---|---|"]
    for row in results:
        lines.append(f"| `{row['id']}` | `{row['namespace']}` | {row['expected']} | {row['actual']} | "
                     f"{row.get('denialSource') or '—'} | {'PASS' if row['passed'] else 'FAIL'} |")
    md_path.write_text("\n".join(lines) + "\n")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--kubectl", default=str(DEFAULT_KUBECTL))
    parser.add_argument("--kubeconfig", default=str(DEFAULT_KUBECONFIG))
    parser.add_argument("--context")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--apply", action="store_true", help="send non-persisting dry-run requests to API admission")
    args = parser.parse_args()
    try:
        catalog = yaml.safe_load(args.catalog.read_text())
        cases = admission_cases(catalog)
        if not args.apply:
            print("Plan only; no API requests sent.")
            print(f"Would server-side dry-run {len(cases)} Pod create requests in {cases[0]['namespace']}.")
            print("Re-run with --apply to query admission; dry-run requests are not persisted.")
            return 0
        kubectl = Kubectl(args.kubectl, args.kubeconfig, args.context)
        preflight(catalog, kubectl)
        suffix = dt.datetime.now(dt.timezone.utc).strftime("%H%M%S")
        results = [run_case(kubectl, case, suffix) for case in cases]
        current = kubectl.run(["config", "current-context"])
        cluster = kubectl.run(["config", "view", "--minify", "-o", "jsonpath={.clusters[0].name}"])
        json_path, md_path = write_evidence(args.output_dir,
            args.context or current.stdout.strip() or "unknown", cluster.stdout.strip() or "unknown",
            results, dt.datetime.now(dt.timezone.utc))
        failed = sum(not result["passed"] for result in results)
        print(f"Admission evidence: {len(results)-failed}/{len(results)} passed; {failed} failed.")
        print(f"JSON: {json_path}\nMarkdown: {md_path}")
        return 1 if failed else 0
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"tenant admission verification could not run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
