#!/usr/bin/env python3
"""Validate tenant catalog data and render the existing Fleet foundation bundle."""

from __future__ import annotations

import argparse
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

from tenant_catalog import load_catalog
import portal_application
import tenant_templates

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
    portal_application.validate_applications(catalog)
    return tenants


def render(catalog: dict) -> str:
    validate_catalog(catalog)
    documents = tenant_templates.render('foundation', catalog=catalog)
    documents.extend(portal_application.active_resources(catalog))
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
        if metadata.get("labels", {}).get("platform.perkforge.io/managed-by") == "tenant-application":
            relative = Path("tenants/home/applications/portal/resources.yaml")
        elif kind == "RoleTemplate":
            relative = Path("shared/roletemplates.yaml")
        else:
            tenant_id = (metadata["labels"]["platform.perkforge.io/tenant"]
                         if kind in {"Project", "Namespace"}
                         else namespaces[metadata["namespace"]])
            relative = Path("tenants") / tenant_id / filenames[kind]
        groups.setdefault(relative, []).append(document)
    return {path: GENERATED_HEADER + yaml.safe_dump_all(rows, sort_keys=False, explicit_start=True)
            for path, rows in sorted(groups.items())}


def refuse_application_identity_removal(previous, desired):
    def identities(text, application_only=False):
        result=set()
        for obj in yaml.safe_load_all(text):
            if not isinstance(obj, dict): continue
            metadata=obj.get('metadata', {})
            if application_only and metadata.get('labels', {}).get('platform.perkforge.io/managed-by')!='tenant-application': continue
            result.add((obj.get('apiVersion'),obj.get('kind'),metadata.get('namespace'),metadata.get('name')))
        return result
    if identities(previous, True) - identities(desired):
        raise ValueError('Refusing to prune provisioned application identities; use paused. Decommission requires separate review.')


def refuse_application_pruning(stale):
    if any('applications' in path.parts for path in stale):
        raise ValueError('Refusing to prune provisioned application resources; retain the catalog entry as paused. Decommission requires separate review.')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="generated bundle directory; an explicit .yaml file retains legacy combined output")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write rendered YAML to --output")
    mode.add_argument("--check", action="store_true", help="fail if --output differs from rendered tenant state")
    parser.add_argument("--preview-application", choices=["home/portal"], help="render catalog-owned application review artifacts outside active Fleet output")
    args = parser.parse_args()
    try:
        catalog = load_catalog(args.catalog)
        validate_catalog(catalog)
        if args.preview_application:
            destination = portal_application.PREVIEW if args.output == DEFAULT_OUTPUT else args.output
            if destination.resolve().is_relative_to((ROOT / 'local-lab/fleet').resolve()):
                raise ValueError('Application previews cannot be written into active Fleet paths')
            files = portal_application.outputs(portal_application.contract_for(catalog))
            if args.check:
                if any(not (destination/name).exists() or (destination/name).read_text()!=text for name,text in files.items()):
                    raise ValueError('Stale application preview; regenerate from the tenant catalog')
                print('Catalog application preview is in sync; not an active Fleet output')
            elif args.write:
                destination.mkdir(parents=True, exist_ok=True)
                for name,text in files.items(): (destination/name).write_text(text)
                print(f'Wrote application review artifacts to {destination}; no deployment')
            else:
                sys.stdout.write(files['resources.yaml'])
            return 0
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
                refuse_application_pruning(stale)
                for path,text in expected.items():
                    if path.exists():
                        refuse_application_identity_removal(path.read_text(), text)
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
            if args.output.exists():
                refuse_application_identity_removal(args.output.read_text(), rendered)
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
