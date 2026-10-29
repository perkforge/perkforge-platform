# OpenBao lab capacity and optional Nextcloud pause

Read-only snapshots on 2026-10-27; no pause/deployment performed during this
repository preparation. The user subsequently approved the bounded pause and
lab setup, contingent on reviewed configuration and validation.

| Resource | Control | Worker |
|---|---:|---:|
| Allocatable memory | 3653 MiB | 3653 MiB |
| Scheduled requests (describe nodes, includes init-container accounting) | 2520 MiB | 2560 MiB |
| Unallocated requests | 1133 MiB | 1093 MiB |
| Measured working set | 2899 MiB | 2749 MiB |
| Existing memory limits | 192 MiB + unbounded workloads | 5464 MiB + unbounded workloads |
| MemoryPressure / DiskPressure | False / False | False / False |

Host: about 15 GiB physical, 2.6 GiB available, 10.6 GiB of 15.3 GiB swap in use.
Swap use is historical/current allocation, not proof of current thrashing. No VM
RAM increase is proposed. CPU snapshot was 88% on worker; capture time series and
OOM events during any trial rather than assuming startup peaks from idle usage.

OpenBao is proposed at 100m CPU / 256 MiB request, 500m / 512 MiB limit; ESO at
25m / 64 MiB request, 200m / 128 MiB limit. These are bounded lab trial settings,
not upstream-guaranteed minima or measured production sizing. Official charts
permit explicit resources and the supported Go runtime `GOMEMLIMIT` is set below
each cgroup limit (384/96 MiB) to leave room for non-Go memory. Cold initialization,
unseal, policy loading, audit, snapshot/restore and concurrent pulls must be
measured. At these requests worker reservation headroom becomes about 773 MiB;
at added limits, current working-set headroom would be about 264 MiB if existing
usage held constant. Existing workloads can grow and many have no reservations.
Neither usage percentages nor scheduler success establish safety or require
Nextcloud downtime by themselves.

| Nextcloud component | Current working set (two samples) | Request | Limit |
|---|---:|---:|---:|
| Web | 51–52 MiB | 384 MiB | 512 MiB |
| Database | 49–51 MiB | 192 MiB | 320 MiB |
| Cron, idle at observation | 0 | 64 MiB while active | 128 MiB while active |
| Shared CNPG operator | 100 MiB | unset | unset |

Web-only pause frees roughly 52 MiB actual now; that is a small gain. Web+DB
pause frees roughly 100 MiB now and 576 MiB of scheduled requests, avoids their
832-MiB combined peak allowance and prevents 128-MiB cron overlap. It gives a
cleaner trial but does not prove a 640-MiB OpenBao/ESO envelope is safe. Keep CNPG
operator running: GitLab and Keycloak databases also depend on it. Keep Keycloak
running for OIDC tests. No active CNPG ScheduledBackup exists for Nextcloud.

Recommendation: finish offline tests first. For live tests, a time-bounded full
Nextcloud pause is reasonable if Corey accepts its outage and protected-data
recovery risk, but web-only pause is unlikely to materially help. Do not stop
other shared services implicitly. An unpaused trial is also possible if fresh
metrics/peaks and reserve justify it; the snapshots alone are insufficient.

## Proposed separate pause approval and exact order

Approve only a bounded Nextcloud outage: record original Fleet/BundleDeployment
pause/drift settings, app replicas, cron suspend state and database annotation;
prevent Fleet overwriting temporary settings; suspend cron; wait for active jobs
to finish; scale `tenant-home-nextcloud/nextcloud` from 1 to 0; set
`cnpg.io/hibernation=on` on
`clusters.postgresql.cnpg.io/nextcloud-db` in that namespace. Wait for its
`cnpg.io/hibernation=True` condition and database pod removal. Keep the Cluster
resource and both PVCs. Do not set database instances to zero, delete the Cluster,
delete Jobs/PVCs/Secrets, disable the CNPG operator or rebuild VMs.

Fleet `GitRepo.spec.paused` stops new Git changes, not workloads. Record and
pause the two generated BundleDeployments too where needed; verify agent-side
`spec.paused`/`spec.options.correctDrift` and no in-flight rollout before any
manual change. Do not assume GitRepo pausing alone defeats drift correction.
Observed BundleDeployments are `tenant-home-nextcloud-app` and
`tenant-home-nextcloud-database` in
`cluster-fleet-local-local-1a3d67d0a899`; both had `spec.paused` and
`spec.options.correctDrift` unset. Their installed CRD supports `spec.paused`.
Record and set those pause flags only after the GitRepo is paused, confirm no
pending deployment, then make the temporary workload changes. On resume remove
only the added pause fields to restore their original unset state.
Use the fully qualified CNPG resource name: `kubectl get cluster` is ambiguous
because Fleet also registers a Cluster kind. No temporary stop command has run.

Resume (with OpenBao trial stopped first if needed to avoid overlapping cold
starts): remove the added hibernation annotation (originally absent), wait for
CNPG healthy/primary Ready, scale web back to 1 and wait for deployment readiness,
restore cron `suspend:false`, then restore exact Fleet pause/drift settings.
Verify both original PVC UIDs/volume bindings, TLS/WebDAV/app login, completed
cron, healthy CNPG and Fleet 2/2. If a job was originally active, drain it before
pause rather than deleting it. Preserve evidence and original pin
`3feb9b09686d5e1e08e9bf6616f6126335a1653f`.

Observed protected PVCs: `nextcloud-db-1` UID
`471ceaf8-8d51-4f9a-ac26-1d812526ff87`, and `nextcloud-nextcloud` UID
`d114bf3f-0c87-4e5e-81b9-12478db7b4c1`; corresponding volumes are `pvc-<UID>`.
These identities are comparison evidence, not backup. A restore of this protected
Nextcloud database has not been verified. A data-preserving shutdown still needs
explicit approval; the disposable-cluster description does not authorize it.

Sources: [CNPG declarative hibernation](https://cloudnative-pg.io/docs/current/declarative_hibernation/)
([official source](https://github.com/cloudnative-pg/cloudnative-pg/blob/main/docs/src/declarative_hibernation.md));
[Fleet pause/drift semantics](https://fleet.rancher.io/reference/ref-gitrepo).
