# Nextcloud discovery and integration — 2026-10-26

## Current deployment

Nextcloud is deployed and verified as a local trial. The app is pinned to
`3feb9b09686d5e1e08e9bf6616f6126335a1653f`, chart 9.4.1, Nextcloud
35.0.2-apache and PostgreSQL17.6. The app repository's later documentation commit
does not change this deployed workload. Fleet reports app 2/2, foundation 5/5,
and existing platform-apps 4/4 Ready. Keycloak remains paused.

The user authorized publication, development-only credential bootstrap, activation
and the trial acceptance workflow. Two immutable Kubernetes Secrets were created
from owner-only files under `.secrets/nextcloud/`; values were never tracked.

The application GitRepo now lives in Rancher Fleet workspace
`fleet-home-nextcloud`, not fleet-local. A Policy requires
`home-nextcloud-deployer`, restricts the source repository, and disables namespace
creation. A Home-labeled BundleNamespaceMapping selects the existing local
cluster in fleet-local. This avoids granting namespace patch authority to the
tenant deployer. Rancher's FleetWorkspace controller owns the workspace namespace;
the platform bundle does not also declare that Namespace. During migration a
Helm keep safeguard was recorded before removing duplicate namespace ownership.

Server admission passed for the application and CNPG. The installed operator
requires unsupervised update strategy for a single-instance CNPG cluster; upgrades
remain controlled by the platform's pinned Git revision. Runtime fixes include
UID33 initialization of persistent subdirectories, an explicit trusted-domain
config and Cron-mode hook, and KeepAlive disabled for the one-worker Apache
profile. A one-time ownership repair touched only the new app PVC's seven
subdirectories, retaining their contents and avoiding privileged app containers.
No data reset, PVC deletion or shared controller change was needed.

Verified: certificate-checked HTTPS/WebDAV upload/download; matching file checksum
after deleting/recreating only the application pod; unchanged database/app PVC
and volume IDs; browser login to the dashboard in an ephemeral context with a
local-only TLS bypass; successful scheduled CronJobs; UID33 with no mounted API
token; selected Alpha/Bravo group authorization denied to Home. The deployer
cannot patch namespaces, delete PVCs, edit policies or create RoleBindings.
The failed initial CronJob is retained as history; subsequent jobs completed.

Private app evidence: `.evidence/smoke-20261027T011531Z/summary.json` and
`.evidence/browser-20261027T012251Z/summary.json`. Runtime testing was authorized
by the user's activation instruction; the offline unit suite was not run.

Unverified: access from a separate LAN client, broad network denial, backups and
restore, node-failure recovery and multi-user load. Workstation tests used temporary
hostname overrides to 192.168.122.202. Hostname/router/bridge/firewall configuration
has not been changed. Workstation /etc/hosts approval remains pending; other LAN
clients need an approved route to the libvirt NAT subnet. Use replaceable data.
The capacity script is an initial-deployment gate: its full additional workload
budget is not a post-deployment health check.

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

## Implementation

- Catalog index `local-lab/tenant-config/tenants.yaml` references the per-tenant
  file `tenants/home.yaml`. Catalog tenant `home`, environment `local-vm`, application `nextcloud`, protected
  namespace `tenant-home-nextcloud`, Rancher Project `p-home-local`.
- Foundation owns namespace, restricted PSA, quota (6Gi storage requests), and
  LimitRange. Home receives default deny only.
- `nextcloud-support` owns default service-account token suppression, scoped
  Fleet deployer RBAC, and exact DNS/Traefik/PostgreSQL/CNPG exceptions.
  Its explicit Helm ownership adoption is limited to the new namespace's
  auto-created default ServiceAccount and newly declared support resources.
- `nextcloud-registration` creates the active, commit-pinned GitRepo in the
  dedicated workspace, with keepResources:true, namespace deletion disabled by
  default, targetNamespace confinement and explicit local target.
  It does not change shared controllers or existing applications.
- App repo has two explicit paths: `bundles/database` and `bundles/nextcloud`.
  It owns CNPG Cluster, Nextcloud Helm chart, TLS and Apache tuning. Chart
  extraManifests include TLS/config resources without an extra duplicate bundle.
- Nextcloud has no token mount or application API grant; CNPG manages its own
  namespaced API identity. The deployer cannot mutate policies/RBAC/quotas or
  delete PVCs/Clusters. No tenant user is given Fleet control.

## Initial activation procedure (completed for the local trial)

For a new environment, confirm private hostname and LAN routing and approve
the development credential bootstrap. Worker disk capacity is expanded; check
fresh pre-deployment headroom. Publish reviewed changes with authorization, pin
the application SHA, and unpause through platform source only after support
reconciliation, preflight and secrets are ready. Do not apply standalone
application YAML or install Helm releases outside Fleet.

Run `python3 scripts/preflight.py` in the application repo for a read-only memory
and disk gate. The current runtime results and their limits are recorded above. Registry
pulls, application admission, CNPG health, readiness, browser login and restart
persistence have passed for the current configuration. Broader denial and
backup/restore remain pending; do not infer them from static rendering.

Current full deploy/rebuild scripts assume Keycloak is up and must not be used
for this temporary paused-identity application profile. Protected Home must be
excluded from any future disposable rebuild/decommission until a separate
approved backup and migration plan is implemented.

Application operations and paired-backup recovery procedures live in the
separate `perkforge-tenant-nextcloud` repository.
