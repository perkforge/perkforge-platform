#!/usr/bin/env python3
"""Verify effective tenant RBAC with impersonated group authorization checks."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "local-lab/tenant-config/tenants.yaml"
DEFAULT_OUTPUT = ROOT / "local-lab/evidence/tenant-rbac"
DEFAULT_KUBECTL = ROOT / ".secrets/kubectl"
DEFAULT_KUBECONFIG = ROOT / ".secrets/rke2.yaml"
ROLE_TEMPLATE_PATH = ROOT / "local-lab/scripts/reconcile-tenant-rancher-bindings.py"
_spec = importlib.util.spec_from_file_location("tenant_binding_reconciler", ROLE_TEMPLATE_PATH)
_bindings = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bindings)

GROUP_PREFIX = "genericoidc_group://"
CLUSTER_SCOPED_RESOURCES = {"namespaces", "nodes"}


def group_principal(tenant_id: str, role: str) -> str:
    return f"{GROUP_PREFIX}/tenants/{tenant_id}/{role}"


def authorization_cases(catalog: dict) -> list[dict]:
    """Generate positive and negative checks for each role and tenant boundary."""
    cases = []
    role_checks = {
        "admins": [
            ("list", "pods", True),
            ("get", "secrets", True),
            ("create", "deployments.apps", True),
            ("create", "pods", True),
            ("create", "rolebindings.rbac.authorization.k8s.io", False),
            ("update", "roles.rbac.authorization.k8s.io", False),
            ("list", "serviceaccounts", False),
            ("create", "serviceaccounts/token", False),
            ("create", "pods/exec", False),
            ("create", "namespaces", False),
            ("impersonate", "serviceaccounts", False),
            ("update", "resourcequotas", False),
            ("list", "nodes", False),
        ],
        "developers": [
            ("list", "pods", True),
            ("create", "deployments.apps", True),
            ("get", "secrets", False),
            ("create", "secrets", False),
            ("create", "rolebindings.rbac.authorization.k8s.io", False),
            ("update", "roles.rbac.authorization.k8s.io", False),
            ("list", "serviceaccounts", False),
            ("create", "serviceaccounts/token", False),
            ("create", "pods/exec", False),
            ("create", "namespaces", False),
            ("impersonate", "serviceaccounts", False),
            ("list", "nodes", False),
        ],
        "viewers": [
            ("list", "pods", True),
            ("list", "deployments.apps", True),
            ("create", "deployments.apps", False),
            ("get", "secrets", False),
            ("create", "secrets", False),
            ("create", "rolebindings.rbac.authorization.k8s.io", False),
            ("update", "roles.rbac.authorization.k8s.io", False),
            ("list", "serviceaccounts", False),
            ("create", "serviceaccounts/token", False),
            ("create", "pods/exec", False),
            ("create", "namespaces", False),
            ("impersonate", "serviceaccounts", False),
            ("list", "nodes", False),
        ],
    }
    for tenant in catalog["tenants"]:
        tenant_id = tenant["id"]
        for environment in tenant["environments"]:
            namespace = environment["namespace"]
            for role, checks in role_checks.items():
                for verb, resource, expected in checks:
                    cases.append({
                        "id": f"{tenant_id}-{role}-{environment['name']}-{verb}-{resource.split('.')[0]}",
                        "tenant": tenant_id,
                        "role": role,
                        "namespace": namespace,
                        "verb": verb,
                        "resource": resource,
                        "expectedAllowed": expected,
                        "group": group_principal(tenant_id, role),
                    })
        for other in catalog["tenants"]:
            if other["id"] == tenant_id:
                continue
            for role in role_checks:
                for environment in other["environments"]:
                    namespace = environment["namespace"]
                    for verb, resource in (("list", "pods"), ("get", "secrets"),
                                           ("create", "deployments.apps")):
                        cases.append({
                            "id": f"{tenant_id}-{role}-deny-{other['id']}-{environment['name']}-{verb}-{resource.split('.')[0]}",
                            "tenant": tenant_id,
                            "role": role,
                            "namespace": namespace,
                            "verb": verb,
                            "resource": resource,
                            "expectedAllowed": False,
                            "group": group_principal(tenant_id, role),
                        })
    return cases


class Kubectl:
    def __init__(self, executable: str, kubeconfig: str | None, context: str | None):
        self.prefix = [executable]
        if kubeconfig:
            self.prefix += ["--kubeconfig", kubeconfig]
        if context:
            self.prefix += ["--context", context]

    def run(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(self.prefix + args, text=True, capture_output=True)

    def json(self, *args: str) -> dict:
        result = subprocess.run(self.prefix + list(args) + ["-o", "json"],
                                check=True, text=True, capture_output=True)
        return json.loads(result.stdout)


def preflight(catalog: dict, kubectl: Kubectl) -> list[str]:
    """Ensure Rancher OIDC, owned projects, role templates, and PRTBs exist."""
    auth = kubectl.run([
        "get", "authconfigs.management.cattle.io", "genericoidc",
        "-o", "jsonpath={.enabled}:{.type}",
    ])
    if auth.returncode != 0 or auth.stdout.strip() != "true:genericOIDCConfig":
        raise RuntimeError("Rancher Generic OIDC through Keycloak is not enabled")
    projects = {}
    for tenant in catalog["tenants"]:
        project_id = f"p-{tenant['id']}-{tenant['cluster']}"
        projects[project_id] = kubectl.json(
            "get", "projects.management.cattle.io", project_id,
            "--namespace", catalog["rancherManagementCluster"],
        )
    expected = _bindings.build_bindings(catalog, projects)
    for role_template in _bindings.ROLE_TEMPLATES.values():
        kubectl.json("get", "roletemplates.management.cattle.io", role_template)
    for binding in expected:
        metadata = binding["metadata"]
        current = kubectl.json(
            "get", "projectroletemplatebindings.management.cattle.io", metadata["name"],
            "--namespace", metadata["namespace"],
        )
        for field in ("projectName", "roleTemplateName", "groupPrincipalName"):
            if current.get(field) != binding.get(field):
                raise RuntimeError(
                    f"Rancher binding {metadata['namespace']}/{metadata['name']} differs from the tenant catalog")
        labels = current.get("metadata", {}).get("labels", {})
        if labels.get("platform.perkforge.io/managed-by") != "tenant-foundation" or \
                labels.get("platform.perkforge.io/tenant") != metadata["labels"]["platform.perkforge.io/tenant"]:
            raise RuntimeError(
                f"Rancher binding {metadata['namespace']}/{metadata['name']} is not catalog-owned")
    return sorted({tenant["cluster"] for tenant in catalog["tenants"]})


def run_case(kubectl: Kubectl, case: dict) -> dict:
    command = [
        "auth", "can-i", case["verb"], case["resource"],
        f"--as=evidence-{case['tenant']}-{case['role']}",
        f"--as-group={case['group']}",
        "--quiet",
    ]
    resource = case["resource"].split(".", 1)[0]
    if resource not in CLUSTER_SCOPED_RESOURCES:
        command.append(f"--namespace={case['namespace']}")
    result = kubectl.run(command)
    actual = result.returncode == 0
    error = None if result.returncode in (0, 1) and not result.stderr.strip() else \
        "kubectl auth can-i returned an API or impersonation error"
    return {
        **case,
        "actualAllowed": actual,
        "passed": actual == case["expectedAllowed"] and error is None,
        "error": error,
    }


def write_evidence(output_dir: Path, cluster_ids: list[str], context: str,
                   results: list[dict], timestamp: dt.datetime) -> tuple[Path, Path]:
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = timestamp.strftime("%Y%m%dT%H%M%SZ")
    json_path = output_dir / f"tenant-rbac-{stamp}.json"
    markdown_path = output_dir / f"tenant-rbac-{stamp}.md"
    summary = {
        "schemaVersion": "perkforge.security-evidence/v1alpha1",
        "testSuite": "tenant-rbac-authorization",
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "targetClusters": cluster_ids,
        "kubectlContext": context,
        "method": "Kubernetes authorization checks using impersonated Generic OIDC group principal names from Keycloak",
        "limitations": [
            "This verifies Kubernetes authorization only; it does not prove browser login, Keycloak group issuance, or Rancher dashboard behavior.",
            "It does not test admission, quota admission, or workload network connectivity.",
        ],
        "summary": {
            "total": len(results),
            "passed": sum(bool(result["passed"]) for result in results),
            "failed": sum(not result["passed"] for result in results),
        },
        "results": results,
    }
    json_path.write_text(json.dumps(summary, indent=2) + "\n")
    markdown = [
        "# Tenant RBAC authorization evidence",
        "",
        f"- Timestamp: `{summary['timestamp']}`",
        f"- Cluster ID(s): `{', '.join(cluster_ids)}`",
        f"- kubectl context: `{context}`",
        f"- Result: **{summary['summary']['passed']}/{summary['summary']['total']} passed**",
        "- Method: Kubernetes authorization checks with impersonated Generic OIDC group principal names from Keycloak.",
        "- Limitation: this does not verify browser login, Keycloak claims, Rancher dashboard behavior, admission, quota admission, or network connectivity.",
        "",
        "| Test | Tenant role | Namespace | Request | Expected | Actual | Result |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for result in results:
        request = f"{result['verb']} `{result['resource']}`"
        expected = "allow" if result["expectedAllowed"] else "deny"
        actual = "allow" if result["actualAllowed"] else "deny"
        status = "PASS" if result["passed"] else "FAIL"
        markdown.append(
            f"| `{result['id']}` | {result['tenant']} {result['role']} | `{result['namespace']}` | "
            f"{request} | {expected} | {actual} | {status} |"
        )
    markdown_path.write_text("\n".join(markdown) + "\n")
    return json_path, markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--kubectl", default=str(DEFAULT_KUBECTL))
    parser.add_argument("--kubeconfig", default=str(DEFAULT_KUBECONFIG))
    parser.add_argument("--context")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        catalog = yaml.safe_load(args.catalog.read_text())
        _bindings._renderer.validate_catalog(catalog)
        kubectl = Kubectl(args.kubectl, args.kubeconfig, args.context)
        cluster_ids = preflight(catalog, kubectl)
        current_context = kubectl.run(["config", "current-context"])
        context_name = args.context or current_context.stdout.strip() or "unknown"
        results = [run_case(kubectl, case) for case in authorization_cases(catalog)]
        timestamp = dt.datetime.now(dt.timezone.utc)
        json_path, markdown_path = write_evidence(
            args.output_dir, cluster_ids, context_name, results, timestamp)
        failed = sum(not result["passed"] for result in results)
        print(f"RBAC evidence: {len(results) - failed}/{len(results)} passed; {failed} failed.")
        print(f"JSON: {json_path}")
        print(f"Markdown: {markdown_path}")
        return 1 if failed else 0
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError,
            json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"tenant RBAC verification could not run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
