#!/usr/bin/env python3
"""Validate tenant catalog data and render the existing Fleet foundation bundle."""

from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

from tenant_catalog import load_catalog

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "local-lab/tenant-config/tenants.yaml"
DEFAULT_OUTPUT = ROOT / "local-lab/fleet/bundles/tenant-foundation"
TENANT_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
QUANTITY = re.compile(r"^([0-9]+(?:\.[0-9]+)?)(m|Ki|Mi|Gi|Ti|Pi|Ei|k|K|M|G|T|P|E)?$")
BUDGET_KEYS = {
    "pods", "requests.cpu", "requests.memory", "limits.cpu", "limits.memory",
    "persistentvolumeclaims", "requests.storage", "services",
}
BINARY = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4,
          "Pi": 1024**5, "Ei": 1024**6}
DECIMAL = {"k": 1000, "K": 1000, "M": 1000**2, "G": 1000**3,
           "T": 1000**4, "P": 1000**5, "E": 1000**6}


def fail(message: str) -> None:
    raise ValueError(message)


def quantity(value: object, key: str) -> Decimal:
    text = str(value)
    match = QUANTITY.fullmatch(text)
    if not match:
        fail(f"invalid Kubernetes quantity for {key}: {text!r}")
    number = Decimal(match.group(1))
    suffix = match.group(2)
    if key.endswith(".cpu") and suffix == "m":
        return number / 1000
    if suffix == "m":
        fail(f"millicore suffix is only valid for CPU ({key})")
    return number * (BINARY.get(suffix, DECIMAL.get(suffix, 1)))


def validate_catalog(catalog: dict) -> list[dict]:
    if catalog.get("apiVersion") != "platform.perkforge.io/v1alpha1":
        fail("apiVersion must be platform.perkforge.io/v1alpha1")
    if catalog.get("kind") != "TenantCatalog":
        fail("kind must be TenantCatalog")
    management_cluster = catalog.get("rancherManagementCluster")
    if not isinstance(management_cluster, str) or not management_cluster:
        fail("rancherManagementCluster is required")
    cluster_rows = catalog.get("clusters")
    if not isinstance(cluster_rows, list) or not cluster_rows:
        fail("clusters must be a non-empty list")
    clusters = {}
    for row in cluster_rows:
        name = row.get("name", "")
        version = str(row.get("podSecurityVersion", ""))
        if not name or name in clusters:
            fail(f"invalid or duplicate cluster name: {name!r}")
        if not re.fullmatch(r"v1\.[0-9]+", version):
            fail(f"{name}: podSecurityVersion must look like v1.36")
        clusters[name] = version
    if management_cluster not in clusters:
        fail("rancherManagementCluster must be listed in clusters")
    tenants = catalog.get("tenants")
    if not isinstance(tenants, list) or not tenants:
        fail("tenants must be a non-empty list")
    ids, namespaces, projects = set(), set(), set()
    for tenant in tenants:
        tenant_id = tenant.get("id", "")
        if not TENANT_ID.fullmatch(tenant_id):
            fail(f"invalid tenant id: {tenant_id!r}")
        if tenant_id in ids:
            fail(f"duplicate tenant id: {tenant_id}")
        ids.add(tenant_id)
        if not tenant.get("displayName"):
            fail(f"{tenant_id}: displayName is required")
        classification = tenant.get("classification", "experimental")
        if classification not in {"experimental", "protected"}:
            fail(f"{tenant_id}: classification must be experimental or protected")
        if classification == "protected" and tenant.get("rancher", {}).get("dashboardAccess") is not False:
            fail(f"{tenant_id}: protected tenants initially require dashboardAccess: false")
        lifecycle = tenant.get("lifecycle", {})
        if not isinstance(lifecycle, dict) or set(lifecycle) - {"state"}:
            fail(f"{tenant_id}: lifecycle may contain only state")
        lifecycle_state = lifecycle.get("state", "active")
        if lifecycle_state not in {"active", "suspended", "offboarding"}:
            fail(f"{tenant_id}: lifecycle.state must be active, suspended, or offboarding")
        rancher = tenant.get("rancher", {})
        target_cluster = tenant.get("cluster", "")
        if target_cluster not in clusters:
            fail(f"{tenant_id}: target cluster {target_cluster!r} is not registered")
        project = rancher.get("projectName", "")
        if not project:
            fail(f"{tenant_id}: rancher.projectName is required")
        if (target_cluster, project) in projects:
            fail(f"duplicate Rancher project name in cluster {target_cluster}: {project}")
        projects.add((target_cluster, project))
        groups = tenant.get("identity", {}).get("groups", {})
        if set(groups) != {"admins", "developers", "viewers"} or not all(groups.values()):
            fail(f"{tenant_id}: identity.groups must define admins, developers, and viewers")
        for role, group_path in groups.items():
            if group_path != f"/tenants/{tenant_id}/{role}":
                fail(f"{tenant_id}: identity group {role} must be /tenants/{tenant_id}/{role}")
        if tenant.get("identity", {}).get("provider") != "keycloak":
            fail(f"{tenant_id}: only the configured keycloak provider is supported")
        isolation = tenant.get("isolation", {})
        if isolation != {"tier": "shared", "network": "restricted", "runtime": "restricted"}:
            fail(f"{tenant_id}: this implementation supports shared/restricted isolation only")
        resources = tenant.get("resources", {})
        budget = resources.get("budget", {})
        if set(budget) != BUDGET_KEYS:
            fail(f"{tenant_id}: resources.budget must define exactly {sorted(BUDGET_KEYS)}")
        defaults = resources.get("defaults", {})
        if set(defaults) != {"requestCpu", "requestMemory", "limitCpu", "limitMemory"}:
            fail(f"{tenant_id}: resources.defaults must define request/limit CPU and memory")
        environments = tenant.get("environments")
        if not isinstance(environments, list) or not environments:
            fail(f"{tenant_id}: at least one environment is required")
        allocated = {key: Decimal(0) for key in BUDGET_KEYS}
        for env in environments:
            name, namespace = env.get("name", ""), env.get("namespace", "")
            if not TENANT_ID.fullmatch(name) or not TENANT_ID.fullmatch(namespace):
                fail(f"{tenant_id}: invalid environment name or namespace")
            if (target_cluster, namespace) in namespaces:
                fail(f"namespace is assigned more than once in {target_cluster}: {namespace}")
            namespaces.add((target_cluster, namespace))
            allocation = env.get("allocation", {})
            if set(allocation) != BUDGET_KEYS:
                fail(f"{tenant_id}/{name}: allocation must define exactly {sorted(BUDGET_KEYS)}")
            for key, value in allocation.items():
                allocated[key] += quantity(value, key)
        for key, total in allocated.items():
            ceiling = quantity(budget[key], key)
            if total > ceiling:
                fail(f"{tenant_id}: environment allocations for {key} ({total}) exceed tenant budget ({ceiling})")
        for key in ("metrics", "costAllocation"):
            if not isinstance(tenant.get("observability", {}).get(key), bool):
                fail(f"{tenant_id}: observability.{key} must be boolean")
    return tenants


def render(catalog: dict) -> str:
    tenants = validate_catalog(catalog)
    cluster_versions = {row["name"]: row["podSecurityVersion"] for row in catalog["clusters"]}
    documents = []
    roles = {
        "perkforge-tenant-admin": {
            "displayName": "PerkForge Tenant Administrator",
            "description": "Manage tenant workloads and tenant-owned secrets without administering cluster or tenant security.",
            "rules": [
                {"apiGroups": [""], "resources": ["pods"], "verbs": ["get", "list", "watch", "delete"]},
                {"apiGroups": [""], "resources": ["pods/log", "events"], "verbs": ["get", "list", "watch"]},
                {"apiGroups": [""], "resources": ["services", "endpoints", "configmaps", "secrets", "persistentvolumeclaims"], "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
                {"apiGroups": ["apps"], "resources": ["deployments", "replicasets", "statefulsets"], "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
                {"apiGroups": ["batch"], "resources": ["jobs", "cronjobs"], "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
                {"apiGroups": ["networking.k8s.io"], "resources": ["ingresses"], "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
                {"apiGroups": ["autoscaling"], "resources": ["horizontalpodautoscalers"], "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
                {"apiGroups": ["metrics.k8s.io"], "resources": ["pods"], "verbs": ["get", "list"]},
            ],
        },
        "perkforge-tenant-developer": {
            "displayName": "PerkForge Tenant Developer",
            "description": "Deploy and troubleshoot tenant workloads without reading secrets or changing tenant security.",
            "rules": [
                {"apiGroups": [""], "resources": ["pods", "pods/log", "services", "endpoints", "configmaps", "persistentvolumeclaims", "events"], "verbs": ["get", "list", "watch"]},
                {"apiGroups": [""], "resources": ["pods"], "verbs": ["delete"]},
                {"apiGroups": [""], "resources": ["services", "configmaps", "persistentvolumeclaims"], "verbs": ["create", "update", "patch", "delete"]},
                {"apiGroups": ["apps"], "resources": ["deployments", "statefulsets"], "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
                {"apiGroups": ["apps"], "resources": ["replicasets"], "verbs": ["get", "list", "watch"]},
                {"apiGroups": ["batch"], "resources": ["jobs", "cronjobs"], "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
                {"apiGroups": ["networking.k8s.io"], "resources": ["ingresses"], "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
                {"apiGroups": ["autoscaling"], "resources": ["horizontalpodautoscalers"], "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
                {"apiGroups": ["metrics.k8s.io"], "resources": ["pods"], "verbs": ["get", "list"]},
            ],
        },
        "perkforge-tenant-viewer": {
            "displayName": "PerkForge Tenant Viewer",
            "description": "Read tenant workload status without mutation or secret access.",
            "rules": [
                {"apiGroups": [""], "resources": ["pods", "services", "endpoints", "events", "persistentvolumeclaims"], "verbs": ["get", "list", "watch"]},
                {"apiGroups": ["apps"], "resources": ["deployments", "replicasets", "statefulsets"], "verbs": ["get", "list", "watch"]},
                {"apiGroups": ["batch"], "resources": ["jobs", "cronjobs"], "verbs": ["get", "list", "watch"]},
                {"apiGroups": ["networking.k8s.io"], "resources": ["ingresses"], "verbs": ["get", "list", "watch"]},
                {"apiGroups": ["autoscaling"], "resources": ["horizontalpodautoscalers"], "verbs": ["get", "list", "watch"]},
                {"apiGroups": ["metrics.k8s.io"], "resources": ["pods"], "verbs": ["get", "list"]},
            ],
        },
    }
    for name, role in roles.items():
        documents.append({
            "apiVersion": "management.cattle.io/v3",
            "kind": "RoleTemplate",
            "metadata": {"name": name, "labels": {"platform.perkforge.io/managed-by": "tenant-foundation"}},
            "builtin": False,
            "context": "project",
            "description": role["description"],
            "displayName": role["displayName"],
            "external": False,
            "hidden": False,
            "rules": role["rules"],
        })
    for tenant in tenants:
        tenant_id = tenant["id"]
        target_cluster = tenant["cluster"]
        version = cluster_versions[target_cluster]
        groups = tenant["identity"]["groups"]
        defaults = tenant["resources"]["defaults"]
        project_id = "p-" + tenant_id + "-" + target_cluster
        lifecycle_state = tenant.get("lifecycle", {}).get("state")
        budget = tenant["resources"]["budget"]
        rancher_quota_names = {
            "pods": "pods",
            "requests.cpu": "requestsCpu",
            "requests.memory": "requestsMemory",
            "limits.cpu": "limitsCpu",
            "limits.memory": "limitsMemory",
            "persistentvolumeclaims": "persistentVolumeClaims",
            "requests.storage": "requestsStorage",
            "services": "services",
        }
        project_limits = {rancher_quota_names[key]: str(value) for key, value in budget.items()}
        documents.append({
            "apiVersion": "management.cattle.io/v3",
            "kind": "Project",
            "metadata": {
                "name": project_id,
                "namespace": catalog["rancherManagementCluster"],
                "labels": {
                    "platform.perkforge.io/tenant": tenant_id,
                    "platform.perkforge.io/managed-by": "tenant-foundation",
                    **({"platform.perkforge.io/lifecycle-state": lifecycle_state}
                       if lifecycle_state else {}),
                },
                "annotations": {"field.cattle.io/no-creator-rbac": "true"},
            },
            "spec": {
                "clusterName": target_cluster,
                "displayName": tenant["displayName"],
                "description": "PerkForge tenant project managed from the tenant catalog.",
                "resourceQuota": {"limit": project_limits},
                "namespaceDefaultResourceQuota": {"limit": project_limits},
            },
        })
        for env in tenant["environments"]:
            namespace = env["namespace"]
            labels = {
                "app.kubernetes.io/part-of": "opengovlocalpaas",
                "platform.homelab/tenant": tenant_id,
                "platform.perkforge.io/tenant": tenant_id,
                "platform.perkforge.io/environment": env["name"],
                "platform.perkforge.io/isolation-tier": tenant["isolation"]["tier"],
                "platform.perkforge.io/managed-by": "tenant-foundation",
                "platform.perkforge.io/metrics": str(tenant["observability"]["metrics"]).lower(),
                "platform.perkforge.io/cost-allocation": str(tenant["observability"]["costAllocation"]).lower(),
            }
            if lifecycle_state:
                labels["platform.perkforge.io/lifecycle-state"] = lifecycle_state
            if "classification" in tenant:
                labels["platform.perkforge.io/classification"] = tenant["classification"]
            if "application" in tenant:
                labels["platform.perkforge.io/application"] = tenant["application"]
            for mode in ("enforce", "audit", "warn"):
                labels[f"pod-security.kubernetes.io/{mode}"] = "restricted"
                labels[f"pod-security.kubernetes.io/{mode}-version"] = version
            documents.append({
                "apiVersion": "v1", "kind": "Namespace",
                "metadata": {
                    "name": namespace,
                    "labels": labels,
                    "annotations": {
                        "field.cattle.io/projectId": f"{target_cluster}:{project_id}",
                        # Rancher project quotas are pooled across namespaces.
                        # Specify each namespace's reserved allocation so Rancher
                        # does not seed every namespace with the project default.
                        # Keep Rancher's API struct field order: it stores this
                        # value as a JSON string and Fleet otherwise sees harmless
                        # ordering drift after Rancher normalizes the annotation.
                        "field.cattle.io/resourceQuota": json.dumps({"limit": {
                            rancher_quota_names[key]: str(env["allocation"][key])
                            for key in ("pods", "services", "persistentvolumeclaims",
                                        "requests.cpu", "requests.memory", "requests.storage",
                                        "limits.cpu", "limits.memory")}}, separators=(",", ":")),
                    },
                },
            })
            documents.append({
                "apiVersion": "v1", "kind": "ResourceQuota",
                "metadata": {"name": "tenant-budget", "namespace": namespace},
                "spec": {"hard": {k: str(v) for k, v in env["allocation"].items()}},
            })
            documents.append({
                "apiVersion": "v1", "kind": "LimitRange",
                "metadata": {"name": "tenant-defaults", "namespace": namespace},
                "spec": {"limits": [{
                    "type": "Container",
                    "defaultRequest": {"cpu": defaults["requestCpu"], "memory": defaults["requestMemory"]},
                    "default": {"cpu": defaults["limitCpu"], "memory": defaults["limitMemory"]},
                }]},
            })
            if tenant.get("classification") == "protected":
                # Application-specific exceptions belong to the platform's
                # protected-tenant support bundle, rather than the shared
                # synthetic-tenant allow policy.
                documents.append({
                    "apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
                    "metadata": {"name": "default-deny", "namespace": namespace},
                    "spec": {"podSelector": {}, "policyTypes": ["Ingress", "Egress"]},
                })
                continue
            documents.extend([
                {"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
                 "metadata": {"name": "default-deny", "namespace": namespace},
                 "spec": {"podSelector": {}, "policyTypes": ["Ingress", "Egress"]}},
                {"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
                 "metadata": {"name": "allow-tenant-internal-and-dns", "namespace": namespace},
                 "spec": {
                     "podSelector": {}, "policyTypes": ["Ingress", "Egress"],
                     "ingress": [{"from": [
                         {"namespaceSelector": {"matchLabels":
                             {"platform.perkforge.io/tenant": tenant_id}}},
                         {"namespaceSelector": {"matchLabels":
                             {"kubernetes.io/metadata.name": "kube-system"}},
                          "podSelector": {"matchLabels": {"app.kubernetes.io/name": "rke2-traefik"}}},
                     # Only the platform Prometheus collector receives ingress
                     # exceptions for tenant metrics scraping.
                     {"namespaceSelector": {"matchLabels":
                         {"kubernetes.io/metadata.name": "monitoring"}},
                      "podSelector": {"matchLabels": {"app.kubernetes.io/name": "prometheus"}}},
                     ]}],
                     "egress": [
                         {"to": [{"namespaceSelector": {"matchLabels":
                             {"platform.perkforge.io/tenant": tenant_id}}}]},
                         {"to": [{"namespaceSelector": {"matchLabels":
                             {"kubernetes.io/metadata.name": "kube-system"}},
                             "podSelector": {"matchLabels": {"k8s-app": "kube-dns"}}}],
                          "ports": [{"protocol": "UDP", "port": 53}, {"protocol": "TCP", "port": 53}]},
                        # Tenant applications need the shared identity service.
                        # Keycloak's in-cluster HTTP service targets container port 8080.
                        {"to": [{"namespaceSelector": {"matchLabels":
                            {"kubernetes.io/metadata.name": "keycloak"}}}],
                         "ports": [{"protocol": "TCP", "port": 8080}]},
                     ],
                 }},
            ])
    return yaml.safe_dump_all(documents, sort_keys=False, explicit_start=True)


GENERATED_HEADER = "# Generated by render-tenant-foundation.py; edit tenant-config instead.\n"


def render_files(catalog: dict) -> dict[Path, str]:
    """Partition one globally validated render without changing resource identity."""
    documents = list(yaml.safe_load_all(render(catalog)))
    namespaces = {env["namespace"]: tenant["id"]
                  for tenant in catalog["tenants"] for env in tenant["environments"]}
    groups: dict[Path, list[dict]] = {}
    filenames = {"Project": "project.yaml", "Namespace": "namespaces.yaml",
                 "ResourceQuota": "quotas.yaml", "LimitRange": "limits.yaml",
                 "NetworkPolicy": "networkpolicies.yaml"}
    for document in documents:
        kind, metadata = document["kind"], document["metadata"]
        if kind == "RoleTemplate":
            relative = Path("shared/roletemplates.yaml")
        else:
            tenant_id = (metadata["labels"]["platform.perkforge.io/tenant"]
                         if kind in {"Project", "Namespace"}
                         else namespaces[metadata["namespace"]])
            relative = Path("tenants") / tenant_id / filenames[kind]
        groups.setdefault(relative, []).append(document)
    return {path: GENERATED_HEADER + yaml.safe_dump_all(rows, sort_keys=False, explicit_start=True)
            for path, rows in sorted(groups.items())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="generated bundle directory; an explicit .yaml file retains legacy combined output")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write rendered YAML to --output")
    mode.add_argument("--check", action="store_true", help="fail if --output differs from rendered tenant state")
    args = parser.parse_args()
    try:
        catalog = load_catalog(args.catalog)
        rendered = render(catalog)
        if args.output.suffix not in {".yaml", ".yml"}:
            files = render_files(catalog)
            expected = {args.output / relative: text for relative, text in files.items()}
            existing = {path for folder in ("shared", "tenants")
                        for path in (args.output / folder).rglob("*.yaml")}
            stale = existing - expected.keys()
            legacy = args.output / "tenants.yaml"
            if args.check:
                if stale or legacy.exists() or any(not path.exists() or path.read_text() != text
                                                  for path, text in expected.items()):
                    print(f"stale tenant foundation: regenerate {args.output}", file=sys.stderr)
                    return 1
                print(f"tenant catalog and {len(files)} generated files are in sync")
                return 0
            if args.write:
                # Only clean files this generator owns; never erase hand-authored YAML.
                if any(not path.read_text().startswith(GENERATED_HEADER) for path in stale):
                    raise ValueError("unexpected YAML in generated directories; refusing to remove it")
                if legacy.exists() and list(yaml.safe_load_all(legacy.read_text())) != list(yaml.safe_load_all(rendered)):
                    raise ValueError("legacy manifest differs from catalog; review before removing it")
                for path, text in expected.items():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(text)
                for path in stale:
                    path.unlink()
                if legacy.exists():
                    legacy.unlink()
                print(f"wrote {len(files)} generated files under {args.output}")
            else:
                # Preserve stdout as a Kubernetes YAML stream for existing consumers.
                sys.stdout.write(rendered)
            return 0
        if args.check:
            if not args.output.exists() or args.output.read_text() != rendered:
                print(f"stale tenant foundation: regenerate {args.output}", file=sys.stderr)
                return 1
            print("tenant catalog and Fleet manifest are in sync")
            return 0
        if args.write:
            args.output.write_text(rendered)
            print(f"wrote {args.output}")
        else:
            sys.stdout.write(rendered)
        return 0
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"tenant foundation validation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
