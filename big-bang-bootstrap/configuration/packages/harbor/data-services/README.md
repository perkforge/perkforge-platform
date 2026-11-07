# Dedicated Harbor data and foundation

These manifests are selected only by the new explicit `local-harbor-data` root,
which inherits the existing accepted stack. The base Valkey manifest remains
suspended; that root enables it and adds Harbor to the existing CNPG watches.
The app root inherits the data root. Neither root is selected by publication.
See the [single-MR rollout and approval sequence](../README.md).

## Data contract

- PostgreSQL 17.11: one CNPG instance; worker placement; 8Gi
  `longhorn-dedicated`; requests 250m/512Mi, limits 1 CPU/1Gi; 100 connections;
  superuser access off and plaintext connections rejected.
- Valkey 7.2.15: separate pinned chart/image; one Recreate writer; worker placement;
  2Gi `longhorn-dedicated`; requests 100m/256Mi, limits 500m/512Mi; bounded init;
  128Mi no-eviction cache and AOF every second; no replica or metrics exporter.
- Harbor database/owner `harbor`, PostgreSQL `verify-full`, 20-open/5-idle pools
  in both core and jobservice (40 open/10 idle at one replica each).
  Cache password-only default user, TLS required, indexes core 0/jobs 1/
  registry 2. No sharing with existing stores or reuse of their credentials.
- Ingress defaults to deny: exact same-namespace core/jobservice to PostgreSQL
  5432; core/jobservice/registry to
  Valkey 6379; exact existing CNPG operator to its 5432/8000 control ports.
  This is ingress-only policy; egress and host-local CNI isolation are not claimed.

## Protected input order

Before data selection, provide the dedicated database username/password Secret,
Valkey ACL Secret, matching `harbor-redis` password and Valkey TLS material. Verify
all exact names/keys in the preparation/delivery contracts before any write.
After PostgreSQL is ready, export only its public server CA certificate into the
app trust bundle; keep CNPG's CA signing key in place. Check ownership/Cluster UID
and recorded server CA Secret rather than guessing its name.

Internal/service certificates must match their actual service DNS identities.
The pinned Harbor chart resolves Redis Secret values into private runtime
configuration. Never print, commit or render real credentials into the public
source cache. Offline chart tests use absent/synthetic credentials only.
Preserve admin, encryption, signing, shared-service and database/registry inputs
with consistent database/content backups. Password replacement is not recovery.

## Namespace authority

The 13-object owner-admin foundation includes the Harbor namespace, app/data
installer accounts in `bigbang`, and five scoped Roles/bindings in Harbor.

- CNPG gets the existing namespace Role unchanged, including Secret/workload and
  Pod exec authority, bound to `cnpg-system/platform-cnpg` only.
- Data installer manages only Valkey native workload and Harbor Helm history;
  app installer manages only rendered Harbor workload/Ingress and Harbor history.
- `flux-system/platform-reconciler` gets Harbor Cluster/NetworkPolicy reconciliation,
  Pod reads and namespace-local ServersTransport reconciliation, without delete.
- No ClusterRole, bind/escalate or shared `bigbang` history access is added.
- Both installer token automounts are off. Namespace/Role creation remains an
  owner-admin step; the child chart does not own the namespace.

`operator-watch-review.yaml` documents the exact patch embedded by the data root:
`gitlab,tenant-home-nextcloud,harbor` in both Helm values and native Deployment.
Immediately before selection, compare live watches and the whole operator spec.
Stop/rebase if another approved namespace was added; never overwrite newer work.

## Create-only foundation

`configuration/ansible/harbor-prerequisites.yaml` is default-off/check-safe. With
explicit approval, it requires the clean exact published release, pinned API,
cluster/operator UIDs, protected kubeconfig and accepted operator pin/readiness.
It inspects all 13 targets before any create and refuses foreign ownership,
rule/subject drift, terminating objects, or token-mount changes. Missing objects
are created/read back one at a time; failure stops subsequent creates. A repeat
reuses exact owned objects without changes and preserves all previous UIDs.
It never changes watches, credentials, workloads, source selection or existing
objects. Supply the inventory plus protected inputs and
`harbor_foundation_scope=harbor-foundation-v1`, `harbor_foundation_apply=true`.
The scope is an approval guard, not permission itself.

## Capacity and physical acceptance

Read-only sample, 2026-11-07 about 14:40 UTC: three Ready nodes, 15 Ready releases,
no unready active Pods; live source v0.26.0. Source publication v0.28.0 had not
installed Harbor. These observations must be refreshed before deployment.

- Worker CPU requests: 5.270/6 and 5.045/6 cores, leaving 1.685 cores in total.
- Finite worker memory limits: about 99% and 90% of allocatable. Some existing
  containers are unbounded, so finite totals are not actual memory ceilings.
- Data plus the native-Ingress app proposes 850m/2048Mi requests. New init,
  migration and push/pull peaks, per-node placement and other queued work still
  require capacity acceptance. Do not shrink existing applications to force fit.
- Two-replica data storage adds 20Gi; registry/job logs add 22Gi, total 42Gi.
  Preserve existing/retained smoke claims and backup reservations. Replication is
  not a backup, and single database/cache instances intentionally accept downtime.

Before app selection: correct TLS/password success; wrong password/CA/hostname,
plaintext and cross-namespace denial; bounded write/restart persistence; healthy
replicas and unchanged existing stores/claims. Ready alone proves none of these.
Certificate lifecycle/renewal, backup recovery, performance and tightly restricted
egress need separate evidence before broader use.
