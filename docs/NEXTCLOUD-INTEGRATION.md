# Nextcloud discovery and integration — 2026-10-26

## Discovery

Both RHEL10.2/RKE2 v1.36.5+rke2r1 nodes are Ready. Fleet in `fleet-local`
reconciles the platform `main` branch; its `local` cluster is the only intended
target. At inspection, platform foundation was 3/3 Ready and applications 4/4.
Keycloak is paused at 0 replicas, with its database retained; local Rancher auth
was verified enabled. Do not restart identity workloads without reviewing
Nextcloud capacity.

Reuse the existing TenantCatalog renderer and Rancher Project/quota model,
restricted Pod Security, Canal/Calico NetworkPolicy, CNPG operator, cert-manager,
and Traefik. StorageClass `local-path` is explicit, not default, with
WaitForFirstConsumer and Delete reclaim. It stores directories at
`/opt/local-path-provisioner`, is node-local and has no data migration or HA.
Traefik is a DaemonSet exposing host ports 80/443, with ClusterIP service.
Rancher's namespace-scoped Issuer is the only existing certificate issuer;
Nextcloud has its own namespace-scoped self-signed issuer. No public ACME.

Existing tenants have namespace budgets, LimitRanges, restricted Pod Security,
and group-based Rancher roles. There was no protected class. The added
classification retains this model, omits the broad synthetic-tenant network
exceptions for Home and refuses protected tenants with dashboardAccess enabled.
The binding reconciler honors dashboardAccess:false, so no initial Home
synthetic-role bindings are created. This is operator-only application access,
not complete lifecycle/data deletion enforcement.

Secrets currently use private local files and direct Kubernetes Secret bootstrap;
there is no configured external secrets manager. The new helper is plan-only
by default and must not be applied without development-bootstrap approval.
No secret values are tracked. Helm and chart rendering used temporary files in
/tmp, not a host installation.

Monitoring/central logs and cost collection remain disabled after the OOM.
Metrics API is available for capacity review; container logs are ephemeral.
No CNPG Backup or ScheduledBackup resources were found. No external backup or
restore validation exists. No useful-data durability claim can yet be made.

Latest observed working sets: control 2,875,624 Ki, worker 2,025,420 Ki; each
has 3,740,808 Ki allocatable. Before expansion the worker had 5,538,328,576 bytes free (5.16 GiB), below
its 8-GiB free-space gate. The user then approved expanding only the worker VM
to 100 GiB; its existing partition, LVM PV/root LV and XFS filesystem were grown
online. Root is now about 95 GiB with about 74 GiB free. `/opt/local-path-provisioner`
was verified on that root filesystem. No physical disk was repartitioned or
formatted, and no existing workload data was deleted. Fresh capacity preflight
results take precedence over the earlier discovery snapshot.

## Prepared implementation

- Catalog index `local-lab/tenant-config/tenants.yaml` references the per-tenant
  file `tenants/home.yaml`. Catalog tenant `home`, environment `local-vm`, application `nextcloud`, protected
  namespace `tenant-home-nextcloud`, Rancher Project `p-home-local`.
- Foundation owns namespace, restricted PSA, quota (6Gi storage requests), and
  LimitRange. Home receives default deny only.
- `nextcloud-support` owns default service-account token suppression, scoped
  Fleet deployer RBAC, and exact DNS/Traefik/PostgreSQL/CNPG exceptions.
  Its explicit Helm ownership adoption is limited to the new namespace's
  auto-created default ServiceAccount and newly declared support resources.
- `nextcloud-registration` creates a PAUSED GitRepo with keepResources:true,
  deleteNamespace:false, targetNamespace confinement and explicit local target.
  It does not change shared controllers or existing applications.
- App repo has two explicit paths: `bundles/database` and `bundles/nextcloud`.
  It owns CNPG Cluster, Nextcloud Helm chart, TLS and Apache tuning. Chart
  extraManifests include TLS/config resources without an extra duplicate bundle.
- Nextcloud has no token mount or application API grant; CNPG manages its own
  namespaced API identity. The deployer cannot mutate policies/RBAC/quotas or
  delete PVCs/Clusters. No tenant user is given Fleet control.

## Outstanding gates

Confirm private hostname and LAN routing. Approve the development credential
bootstrap. Worker disk capacity is now expanded; recheck capacity before activation.
Publish reviewed changes only with commit/push authorization. Pin the reviewed
application SHA and unpause its GitRepo through the platform source after
support reconciliation, preflight and secrets are ready. Do not apply standalone
application YAML or install Helm releases outside Fleet.

Run `python3 scripts/preflight.py` in the application repo for a read-only memory
and disk gate. Application/DB compatibility and registry pulls, server admission,
live CNPG API reachability, readiness, LAN/browser access, cross-tenant denial,
backup/restore and restart persistence remain pending. Local Helm rendering and
catalog sync are configuration checks, not runtime acceptance. No tests were
added or run, following AGENTS.md.

Current full deploy/rebuild scripts assume Keycloak is up and must not be used
for this temporary paused-identity application profile. Protected Home must be
excluded from any future disposable rebuild/decommission until a separate
approved backup and migration plan is implemented.

Application operations and paired-backup recovery procedures live in the
separate `perkforge-tenant-nextcloud` repository.
