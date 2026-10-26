#!/usr/bin/env python3
"""Plan or apply Keycloak group bindings to Rancher tenant projects."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "local-lab/tenant-config/tenants.yaml"
OIDC_AUTH_NAME = "genericoidc"
OIDC_PROVIDER_TYPE = "genericOIDCConfig"
ROLE_TEMPLATES = {
    "admins": "perkforge-tenant-admin",
    "developers": "perkforge-tenant-developer",
    "viewers": "perkforge-tenant-viewer",
}
RENDERER_PATH = ROOT / "local-lab/scripts/render-tenant-foundation.py"
_spec = importlib.util.spec_from_file_location("tenant_foundation_renderer", RENDERER_PATH)
_renderer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_renderer)


def fail(message: str) -> None:
    raise ValueError(message)


def binding_name(tenant_id: str, role: str) -> str:
    digest = hashlib.sha256(f"{tenant_id}/{role}".encode()).hexdigest()[:20]
    return f"pf-{digest}"


def build_bindings(catalog: dict, projects: dict[str, dict], *,
                   include_inactive: bool = False) -> list[dict]:
    """Build PRTBs only for catalog-owned projects with a known backing namespace."""
    bindings = []
    management_cluster = catalog["rancherManagementCluster"]
    for tenant in catalog["tenants"]:
        tenant_id = tenant["id"]
        lifecycle_state = tenant.get("lifecycle", {}).get("state", "active")
        if lifecycle_state != "active" and not include_inactive:
            continue
        cluster_id = tenant["cluster"]
        project_id = f"p-{tenant_id}-{cluster_id}"
        project = projects.get(project_id)
        if project is None:
            fail(f"Rancher Project {project_id} is missing; reconcile the Fleet foundation first")
        metadata = project.get("metadata", {})
        labels = metadata.get("labels", {})
        if metadata.get("namespace") != management_cluster:
            fail(f"Rancher Project {project_id} is in an unexpected management namespace")
        if labels.get("platform.perkforge.io/tenant") != tenant_id or \
                labels.get("platform.perkforge.io/managed-by") != "tenant-foundation":
            fail(f"Rancher Project {project_id} is not owned by this tenant catalog")
        if project.get("spec", {}).get("clusterName") != cluster_id:
            fail(f"Rancher Project {project_id} belongs to a different cluster")
        backing_namespace = project.get("status", {}).get("backingNamespace")
        if not backing_namespace:
            fail(f"Rancher Project {project_id} has no status.backingNamespace yet")
        project_name = f"{cluster_id}:{project_id}"
        for role, role_template in ROLE_TEMPLATES.items():
            group_path = tenant["identity"]["groups"][role]
            if group_path != f"/tenants/{tenant_id}/{role}":
                fail(f"{tenant_id}: unexpected Keycloak {role} group path {group_path!r}")
            bindings.append({
                "apiVersion": "management.cattle.io/v3",
                "kind": "ProjectRoleTemplateBinding",
                "metadata": {
                    "name": binding_name(tenant_id, role),
                    "namespace": backing_namespace,
                    "labels": {
                        "platform.perkforge.io/tenant": tenant_id,
                        "platform.perkforge.io/managed-by": "tenant-foundation",
                        "platform.perkforge.io/tenant-role": role,
                    },
                },
                "projectName": project_name,
                "roleTemplateName": role_template,
                # With Keycloak's full-path groups mapper this is the literal
                # group path, prefixed by Rancher's OIDC principal type.
                "groupPrincipalName": f"genericoidc_group://{group_path}",
            })
    return bindings


class Kubectl:
    def __init__(self, executable: str, kubeconfig: str | None, context: str | None):
        self.prefix = [executable]
        if kubeconfig:
            self.prefix += ["--kubeconfig", kubeconfig]
        if context:
            self.prefix += ["--context", context]

    def json(self, *args: str) -> dict:
        result = subprocess.run(self.prefix + list(args) + ["-o", "json"],
                                check=True, capture_output=True, text=True)
        return json.loads(result.stdout)

    def apply(self, document: dict) -> None:
        subprocess.run(self.prefix + ["apply", "-f", "-"], input=yaml.safe_dump(document),
                       check=True, text=True)

    def delete(self, name: str, namespace: str) -> None:
        subprocess.run(self.prefix + ["delete", "projectroletemplatebinding", name,
                                      "--namespace", namespace,
                                      "--ignore-not-found=true"],
                       check=True, text=True, capture_output=True)


def reconcile(catalog: dict, kubectl: Kubectl, apply: bool) -> list[dict]:
    management_cluster = catalog["rancherManagementCluster"]
    projects = {}
    for tenant in catalog["tenants"]:
        project_id = f"p-{tenant['id']}-{tenant['cluster']}"
        projects[project_id] = kubectl.json(
            "get", "projects.management.cattle.io", project_id,
            "--namespace", management_cluster,
        )
    all_bindings = build_bindings(catalog, projects, include_inactive=True)
    inactive_ids = {tenant["id"] for tenant in catalog["tenants"]
                    if tenant.get("lifecycle", {}).get("state", "active") != "active"}
    bindings = [obj for obj in all_bindings
                if obj["metadata"]["labels"]["platform.perkforge.io/tenant"] not in inactive_ids]
    inactive_bindings = [obj for obj in all_bindings
                         if obj["metadata"]["labels"]["platform.perkforge.io/tenant"] in inactive_ids]

    if apply:
        auth = kubectl.json("get", "authconfigs.management.cattle.io", OIDC_AUTH_NAME)
        if auth.get("enabled") is not True or auth.get("type") != OIDC_PROVIDER_TYPE:
            fail("Rancher Generic OIDC through Keycloak is not enabled; refusing unusable group bindings")
        for role_template in ROLE_TEMPLATES.values():
            kubectl.json("get", "roletemplates.management.cattle.io", role_template)

    # Refuse to overwrite or duplicate manually managed bindings. Existing exact
    # objects are safe to re-apply; group principals and role refs are immutable.
    existing: dict[tuple[str, str], dict] = {}
    by_namespace: dict[str, list[dict]] = {}
    for namespace in sorted({obj["metadata"]["namespace"] for obj in all_bindings}):
        items = kubectl.json("get", "projectroletemplatebindings.management.cattle.io",
                             "--namespace", namespace).get("items", [])
        by_namespace[namespace] = items
        existing.update({(namespace, obj.get("metadata", {}).get("name")): obj for obj in items})
    for binding in all_bindings:
        namespace = binding["metadata"]["namespace"]
        name = binding["metadata"]["name"]
        current = existing.get((namespace, name))
        identity_fields = ("projectName", "roleTemplateName", "groupPrincipalName")
        if current is not None:
            current_labels = current.get("metadata", {}).get("labels", {})
            expected_labels = binding["metadata"]["labels"]
            if any(current.get(field) != binding.get(field) for field in identity_fields) or \
                    any(current_labels.get(key) != value for key, value in expected_labels.items()):
                fail(f"binding {namespace}/{name} conflicts with existing Rancher state")
            if binding in inactive_bindings:
                if apply:
                    kubectl.delete(name, namespace)
            continue
        if binding in inactive_bindings:
            continue
        for current in by_namespace[namespace]:
            if current.get("roleTemplateName") == binding["roleTemplateName"] and \
                    current.get("groupPrincipalName") == binding["groupPrincipalName"]:
                fail(f"a matching group/role binding already exists as "
                     f"{namespace}/{current.get('metadata', {}).get('name')}; review before adoption")
        if apply:
            kubectl.apply(binding)
    return bindings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--kubectl", default="kubectl")
    parser.add_argument("--kubeconfig")
    parser.add_argument("--context")
    parser.add_argument("--apply", action="store_true",
                        help="reconcile Rancher PRTBs; requires enabled Generic OIDC through Keycloak")
    args = parser.parse_args()
    try:
        catalog = yaml.safe_load(args.catalog.read_text())
        _renderer.validate_catalog(catalog)
        kubectl = Kubectl(args.kubectl, args.kubeconfig, args.context)
        bindings = reconcile(catalog, kubectl, args.apply)
        if not args.apply:
            sys.stdout.write(yaml.safe_dump_all(bindings, sort_keys=False, explicit_start=True))
        inactive_tenants = [tenant["id"] for tenant in catalog["tenants"]
                            if tenant.get("lifecycle", {}).get("state", "active") != "active"]
        if not args.apply:
            if inactive_tenants:
                removal_names = [binding_name(tenant["id"], role)
                                 for tenant in catalog["tenants"]
                                 if tenant["id"] in inactive_tenants
                                 for role in ROLE_TEMPLATES]
                print("Suspended/offboarding bindings to remove when applied: " +
                      ", ".join(removal_names), file=sys.stderr)
            print("Plan only; no resources were changed.", file=sys.stderr)
        else:
            print(f"Reconciled {len(bindings)} active Rancher project role bindings; "
                  f"inactive tenants: {len(inactive_tenants)}.")
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError,
            json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"tenant Rancher binding reconciliation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
