# Local Velero rollout and tenant recovery

**Work in progress, not ready to deploy.** This is one cohesive source change for a
separate bounded local Garage instance, Velero installation, copied-data acceptance
and platform-operated backup/restore. Current roots remain unchanged. No live
storage, quota, key, RBAC, backup or schedule has been changed by this source work.
Garage 2.5.0 is pinned and its exact S3/Kopia component tests passed. Host quota/
capacity maintenance, private endpoint isolation and native cluster acceptance
remain required. A component pass does not mean tenant data is protected.

Only platform operators use Velero, its API and repository/store credentials.
Tenant namespace selection is a content filter, not authorization. Tenants receive
no Velero identity, role, bucket key or repository password.

## Scope and ownership

- `install.yaml`: default-off foundation, backend and activation stages for one
  immutable released commit. Ansible creates owned prerequisites and protected
  references; Flux owns the actual backend and Velero releases/workloads.
- `bootstrap-store.yaml`: default-off native Garage layout, one supplied key and
  one bucket. Admin access is loopback-only. No adoption, deletion, rotation or
  uncertain-write retry. Private intent receipts stop ambiguous resumes.
- `exercise.yaml`: default-off native CSI/Kopia copied-byte roundtrip through a
  backend restart, two disposable namespaces and fresh target storage.
- `recovery.yaml`: default-off one-tenant backup, **paused** schedule or isolated
  restore with native hooks, immutable application/database identity and transfer
  checks. It never switches traffic, changes app versions or unpauses owners.
- `prepare.yaml`: optional offline profile preview only, including future AWS.
  Its review references are operator input, not approval or verified evidence.
  No preview receipt is needed to install or run the native exercise.

All default and `--check` invocations are inert. Source review does not approve
execution. Live namespace/RBAC/Secret creation, Garage key import, backend/Velero
activation, synthetic storage use and backup/restore each need their actual scope
approved. Host maintenance and schedule activation are separate decisions.

## Current prerequisites and storage safety

Worker-2 has one approximately 931 GiB XFS filesystem, about 910 GiB free, mounted
**noquota**. Longhorn reserves 30% (about 279 GiB), has about 49 GiB scheduled, uses a 25%
minimum-free floor and 100% overprovisioning. Those are observed capacity facts,
not a backup allocation. **No backup capacity has been selected.** A PV capacity
field, free bytes and a Longhorn reserve are not a filesystem hard quota.

Before the rollout, approve a maintenance window and exact byte budget. The host
procedure must preserve mount identity, Longhorn replica availability and recovery
access while enabling XFS project accounting/enforcement. Set an exclusive project
ID and inherited hard quota on a new dedicated direct child directory named
`velero-backups` (or a suffixed variant), owned 1000:1000 with no world permissions,
outside every Longhorn replica/engine/metadata subtree. Set Garage's object capacity below the hard quota,
leaving the separately entered `velero_metadata_budget_bytes` inside the quota.
Budget for the active SQLite DB, WAL, up to three transient native snapshots and
growth (at least four times the observed DB size, plus WAL/growth). This is a
planning reserve, not a second quota or verified growth estimate; monitor actual
usage and stop before exhaustion. The only hard limit is the filesystem project
quota. Reconcile the Longhorn reservation to cover the quota, original free-space floor and additional snapshot/restore/cleanup headroom.

Do not unmount an active Longhorn disk, edit fstab, change reservations or create the
backing path through this installer. Those host operations need a separately
reviewed safety plan. One uninterrupted deployment is unsafe while `noquota` is
present. The same MR can deliver the remaining app rollout after that prerequisite.

The read-only host preflight checks filesystem UUID/source, project inheritance,
quota accounting/enforcement and hard limit, directory ownership, Longhorn disk
UUID, current scheduled replica promises, reserve, free space and headroom. It
rejects a reserve that leaves less capacity than already scheduled. It does not
claim that synthetic guard tests verified the live host. Failures stop before new
cluster resources. The local PV is statically prebound, node-affine and **Retain**.
A failed reinstall never adopts a foreign PV/claim or silently changes its path.

Use observed compressed baseline plus measured daily changed bytes, metadata and
maintenance growth to propose the 48h allocation. Include simultaneous old/new
restore volumes and snapshot space; do not assume deduplication/compression. The
Nextcloud tenant's existing 2 PVC/48 Gi quota is fully allocated, so its real isolated
restore needs a separate approved namespace/quota/capacity plan.

This is local upgrade recovery, not independent disaster recovery. Losing this
worker/disk can lose its backups. An independent disk/site/account copy is a
separate durability decision. Existing GitLab Garage remains untouched on its
replicated Longhorn claims. A separate instance is a placement/failure-boundary
choice, not a Velero requirement.

## Versions and transport

The exact Big Bang 3.35.1 wrapper 12.2.1-bb.0 contains upstream chart 12.2.1,
Velero 1.18.4 and AWS plugin 1.14.4. The official matrix pairs 1.18.x/1.14.x.
[Compatibility evidence](compatibility.yaml) pins the downloaded chart checksum.
Do not replace only one image or upgrade shared pins. CSI is integrated; the old
standalone CSI plugin in wrapper annotations is not needed. Kubernetes 1.36.5 is
expected by upstream's broad range but not among 1.18's listed test versions;
actual cluster acceptance remains required.

Garage is AGPLv3. This new instance selects current official release 2.5.0, pinned
to the verified linux/amd64 manifest
`sha256:23b16d34e0348d9aca9b960a7429a7e6d494974b5288bfb8f6c3ab856895f71e`.
The store selects an amd64 node; existing GitLab 2.2.0 is not upgraded. This is not
an LTS/security-support claim. MinIO's archived upstream is not a maintained
drop-in alternative. Garage implements the required basic and
multipart S3 APIs, but not S3 bucket versioning or AWS IAM/policy APIs. Its native
bucket-scoped key has read/write, **not owner/create-bucket**, authority. Prefixes
organize data; the Garage authorization boundary here is the dedicated bucket.

On 2026-11-07, disposable native tests passed with AWS plugin 1.14.4's exact
object-store source and unchanged dependency graph. Its default CRC32 works:
4 KiB and 11 MiB multipart PUT/HEAD/GET/hash/list/prefix/delete passed without a
checksum workaround. Velero 1.18.4's exact
`project-velero/kopia@d946b1e75197` and unchanged dependency graph initialized an
encrypted repository, uploaded 17 MiB, survived Garage restart, restored the SHA256
through a fresh config/cache, ran full `SafetyFull` maintenance and restored again.
Both clients rejected an untrusted CA, wrong hostname, wrong key and another
existing bucket. Normal snapshot manifest deletion and maintenance passed; this
does not prove immediate physical chunk reclamation, interrupted multipart abort
cleanup or incremental snapshot growth.

The actual `bootstrap-store.yaml` also passed against a separate empty native
2.5.0 SQLite instance: one layout, supplied key and bucket, read/write without owner or
create-bucket authority, then zero-change repeat. Both disposable instances were
stopped. These are component tests, not full plugin gRPC/Iron Bank image execution,
Kubernetes CSI data movement, application consistency or live recovery acceptance.

Traefik terminates HTTPS on a new platform-only backup hostname/certificate.
Garage's internal backend hop is HTTP; do not call this end-to-end encryption.
There is no admin ingress/service. A dedicated Traefik IP allowlist requires exact
reviewed platform source addresses; the backend policy permits only the existing
Traefik selector. Never allow a shared tenant/NAT source identity merely to make
connectivity pass. If source identity cannot distinguish clients, resolve the
private routing design before activation; DNS alone does not enforce privacy. Endpoint reachability still needs actual CNI/DNAT and
firewall verification. Keep the route private to platform clients. Supply a trusted
CA and verify both the plugin and exact Kopia path, including wrong-CA denial.
`insecureSkipTLSVerify` stays false. The pinned source propagates BSL CA bytes into
Kopia RootCA. The verified localhost TLS proxy exercised both pinned client
libraries; the actual Traefik route, certificate delivery and cluster path still
require acceptance.

## Single-node metadata durability

For this **new** instance, SQLite is selected instead of GitLab's LMDB baseline.
Garage's [known issues](https://garagehq.deuxfleurs.fr/documentation/reference-manual/known-issues/)
warn that LMDB metadata can corrupt after forced shutdown/power loss; RF1 has no
second metadata copy. SQLite avoids those listed LMDB-specific issues, at lower
throughput. Both `metadata_fsync` and `data_fsync` are explicitly true. Native
`metadata_auto_snapshot_interval = "1h"` writes to `/data/meta-snapshots` within
the same hard quota. Garage keeps the newest two snapshots automatically, with
three temporarily present during cleanup. There is no invented keep-count option.
Three manual native snapshots on the exact SQLite image retained exactly two.
The hourly timer and forced-power-loss recovery were not tested. This metadata
interval is not the tenant backup cadence or an RPO promise.

Snapshots remain on the same disk and can be lost with it. A clean restart does
not prove power-loss safety, and Garage has no object locking/WORM guarantee.
Treat the bucket/key and repository password as trusted platform custody; the
immutable references here identify app versions, not immutable backup storage.

If metadata is damaged, stop writes and pause owners under a separately approved
recovery action. Preserve the original data/metadata and node identity before any
repair. Use a native consistent snapshot with the same Garage version in an
isolated offline recovery copy; never copy a running DB as its backup. Retain the
object directory and protected node/RPC/key material, verify repository reopening
and an isolated fresh-cache restore before returning service, and keep the failed
original until acceptance. A snapshot rewind can lose metadata for newer writes
and does not guarantee every backup point remains usable. No automatic corruption
repair, destructive restore or release of traffic is part of this installer.

## One rollout, with explicit stops

1. Approve and complete host quota/capacity maintenance. Confirm healthy apps/Longhorn before and after the host change.
2. Merge/release through normal review, never direct-main publication. Use a clean
   checkout of the published immutable tag/commit. Copy
   [deployment.example.yaml](deployment.example.yaml) outside Git with mode 0600;
   fill exact context/API/cluster UID, current source tag/root, node/disk identity,
   capacity, private endpoint/certificate and protected file paths. Put the exact
   storage inventory host in the `velero_storage` group. Keep receipts in
   a separate existing 0700 owner directory. Do not put physical IDs or keys in Git.
3. Verify the current composition. The compiled base in `deployment/base.yaml` is
   `local-grafana-sso` at commit
   `d95371627179fa090d935043619fd994e05b1437`, preserving Harbor data/app resources and the active
   Grafana SSO overlay. The operator source includes v0.31.2 fixes; the accepted
   runtime base remains v0.31.1. Harbor must finish functional acceptance first;
   merely selecting its root is not acceptance. The preflight requires Harbor
   Ready at its current generation, which still does not prove SSO/push/pull.
   The live source artifact must match that compiled base commit, even when its
   root path is unchanged. If a Harbor hotfix or another app advances the accepted
   source/root, integrate it and update this same MR before release/rollout.
   The selector preflight fails closed; it must never turn those apps off. Confirm
   actual `flux-system/cluster-root` and source `flux-system/cluster-config` names.
4. With exact foundation approval, run `install.yaml` stage `foundation`. It verifies
   the release, target and host; installs only the 13 pinned Velero CRDs (existing
   snapshot controller/CRDs remain owned elsewhere); creates scoped foundation,
   Longhorn V1/ext4 `type:snap` VolumeSnapshotClass and supplied immutable Secrets.
   It creates inactive runtime values. No app is started in this stage.
5. Approve stage `backend`. The installer saves old source/root identity, pauses root,
   promotes only the verified tag, then selects `local-velero` and resumes root using
   compare-and-swap guards. The new Garage release starts, Velero remains off.
   Helm histories live in their own namespaces, not other apps' Big Bang history.
6. Through an explicitly established `kubectl port-forward --address=127.0.0.1`
   to the **new** store Pod's admin 3903 port, run `bootstrap-store.yaml` with exact
   node ID, approved capacity, bucket and supplied private key/admin files. The
   playbook does not create a forward or credentials. A pending receipt means
   inspect the actual outcome before any retry; never delete receipts to bypass it.
7. Approve stage `activate`. It only transitions the owned runtime ConfigMap to the
   source-owned enabled values, waits for Velero/node-agent and the Available BSL.
   The generic wrapper EBS snapshot class is removed by its narrow postrenderer.
   Actual Longhorn class ownership remains with foundation. No schedules exist.
8. Approve and run the disposable `exercise.yaml`, including its new namespaces,
   two 1Gi claims, temporary CSI snapshots/mover storage and one graceful restart of
   the new Garage Pod. Verify exact operation UIDs, each source PVC UID, completed
   copied snapshot IDs, fresh target PVC/PV binding and identical SHA256 after
   repository reopen. Partial failures, warnings, missing/duplicate/wrong-UID
   transfers fail. All resources/evidence remain on failure; cleanup is explicit.
9. Review network/RBAC denial checks and runtime usage, then onboard an approved
   tenant through `recovery.yaml` and its reviewed app-specific native hooks.
   A synthetic byte pass does **not** prove database consistency or tenant service.
   Complete functional acceptance before scheduling or returning traffic.

Example invocation shape, only after approval and filled private inputs:

```sh
ansible-playbook -i /private/reviewed-inventory install.yaml -e @/private/deployment.yaml \
  -e '{"velero_install_apply":true,"velero_install_stage":"foundation","velero_install_scope":"velero-foundation-v1"}'
```

Use the corresponding `backend`/`activate` stage and scope for later stages. Plain
`ansible-playbook -i localhost, install.yaml` is the safe inert check. Secrets are
supplied, never generated or rotated: separate Garage admin/RPC material, a
bucket-scoped key, repository password, TLS leaf/key/CA and authorized registry
copy. Preserve repository-password and object-store recovery custody outside the
cluster. Never rebuild the repository with a different password.

On failure, do not rollback by deleting PVs, buckets, credentials or backups. Inspect
saved selector identity and current Flux state. If an explicit handback is approved,
pause root, restore only the recorded source tag/path after checking for intervening
app changes, then resume. `prune:false` prevents automatic old-resource removal but
is not a substitute for deliberate Velero/store suspension and retained-data review.
No automatic destructive cleanup or force recovery is supplied.

## Security and recovery acceptance

The server/node-agent is **trusted platform backup infrastructure**. The exact 1.18
CSI-only path does not need node-agent hostPath mounts: `disableHostPath:true` removes
them and fs-backup remains disabled. The namespace uses baseline admission because
CSI mover containers still run as root with access to copied tenant volumes. Global
PV/VSC authority can expose storage outside a namespace; Roles are not a tenant
sandbox. Explicit selected workers, independent key custody, source-owned RBAC and
actual admission/audit checks remain required. Never re-enable hostPath or legacy
filesystem backup as an unreviewed fallback. Runtime global writes are limited to PVs and
VolumeSnapshotContents needed by CSI exposure/rebinding; global reads include Pods
and Velero CRs because the exact node-agent uses all-namespace LIST with field
selectors. It cannot mutate arbitrary cluster RBAC or read all cluster Secrets.

Selected source namespaces receive workload read, native hook exec and snapshot
permissions. Only selected isolated restore targets receive workload write/delete
permissions. Flux/RBAC/ServiceAccount objects are excluded from recovery. Identity,
quota and operator-owned objects must be supplied by their existing source owners.
The installer does not patch a live-only admission exception. Test authorization
and actual snapshot/mover behavior; any missing permission must receive narrow
source review, not a cluster-admin workaround.

For real tenants, capture matching image digest, chart digest, app/platform/enrollment Git commits and
DB/schema version with each point. Native pre/post backup hooks must quiesce and
release the application with `onError:Fail`; restore hooks select the **target**
namespace in 1.18. Restore only into empty, separately budgeted storage with the
relevant Flux owners already suspended. Restore excludes Ingress, Service, network
policy, scheduled jobs and daemonsets, preserving target isolation instead of
replaying source routing. Only existing internal ClusterIP services are accepted;
the target has a default-deny network policy. Existing app/operator versions, dependent
services, database recovery and routing must be deliberately coordinated. Shared
DB tenants require DB-native selective recovery and are rejected by the generic
volume restore path. Never overwrite a shared DB volume to recover one tenant.

The copied-data path excludes cluster resource manifests intentionally. Exact 1.18
CSI restore consumes completed DataUpload results, clears the old volumeName and
creates DataDownload for fresh PVCs. It does not automatically preserve excluded
PV/VSC metadata. No snapshot-reference/native-PV fallback is accepted. The live
exercise is still required to validate this path with Longhorn 1.13 V1/ext4.

## Retention and schedules

Local TTL is 48h; future AWS TTL is 336h. Cadence/RPO is **undecided**, not implied by
TTL. `recovery.yaml` accepts valid numeric cron only to create a **paused** Schedule.
The source records the current PVC name/UID/PV catalog on the Backup or Schedule.
Native scheduled Backups inherit it. Restore compares the complete catalog with
actual DataUploads for that exact Backup UID, without requiring a manufactured
local acceptance receipt. A changed PVC set/UID fails coverage. App/DB versions and
PVC catalogs must be refreshed while schedules are paused during an upgrade; hooks
must reject a version mismatch, not merely run a generic sync command.
Review timezone/DST, maximum interval, overlapping runs, workload change rate,
restore duration, cost and missed-run handling before a separate activation.
Keep a fresh verified pre-upgrade point alive through the entire rollback window.
Do not start an upgrade using a nearly expired point, or assume a paused Schedule
extends Backup TTL. Arrange a separately reviewed longer-lived point if 48h cannot
cover the upgrade/recovery window.

TTL depends on running Velero deletion controllers and Kopia repository maintenance.
Observe BackupRepository readiness, last successful backup, expiry/deletion errors,
DataUpload failures, quota/free-space alerts and maintenance status before enabling
cadence. Vendor monitoring objects are initially disabled rather than granted extra
permissions silently. Do not add a blanket S3 object lifecycle rule that deletes
shared Kopia chunks. Test deletion/maintenance and verify actual capacity recovery.

## Future AWS configuration

The same Velero/chart/plugin, Kopia and recovery contracts apply with a durable S3
bucket, 336h TTL and EBS CSI driver `ebs.csi.aws.com`. There is no AWS provisioning root
or claimed operational AWS target in this repository; local/il2 remains supported.
The [AWS profile](profiles/aws.yaml) and offline preview record explicit proposed
region, endpoint/CA, bucket/prefix, identity/KMS and storage/snapshot mappings.

- Separate EBS CSI controller/node IAM and EBS KMS permissions from Velero's bucket
  access. CSI copied-data mode does not justify unused native EC2 snapshot grants.
- Choose EKS IRSA or supported EKS Pod Identity explicitly. Self-managed RKE2 needs
  its own reviewed OIDC/credential delivery path; these are not interchangeable.
  Pod Identity link-local credential endpoints need provider-specific network
  policy, not the local exact-host guard or a broad metadata-access exception.
- Scope S3 list/get/put/delete/multipart to the reviewed bucket/prefix, including
  Kopia repository objects. Review destination account/region and outage/custody
  boundaries before calling it independent DR. Off-worker storage alone proves none.
- Set bucket-default SSE-KMS and permissions for **both** plugin metadata and Kopia
  writes. An AWS-plugin-only `kmsKeyId` is not proof that Kopia uses that key. Test
  read/write/delete/maintenance and key-denial behavior with both actual clients.
- Map source and restore StorageClasses, EBS CSI VolumeSnapshotClass, filesystem,
  target AZ/topology and EBS encryption key for fresh restore. Review cross-zone or
  cross-region restore separately. Store repository-password recovery custody
  outside the cluster and include S3/KMS cost and retention in capacity planning.

## Verification limits

Offline tests check native Ansible default behavior/control flow, refusal paths,
exact chart rendering, scoped authority and unchanged old roots. API fixtures are
not Kubernetes integration, quota enforcement, S3 compatibility or data durability.
The official release index and native tests are verified, but a complete tagged
changelog/security audit was not available. The broader upstream Go semantic suite
did not run with uncached dependencies.
The later exact-client probes are narrower component evidence, not a substitute.

[Sanitized native evidence](../../../tests/fixtures/velero_native/evidence.json),
[exact AWS harness](../../../tests/fixtures/velero_native/aws_object_store_test.go),
[Kopia harness](../../../tests/fixtures/velero_native/kopia_client.go) and
[normalized Admin v2 fields](../../../tests/fixtures/velero_native/garage-admin-shapes.json)
preserve the tested implementation and limits. These fixtures are not auto-run by
unit tests. To reproduce, use an independently approved disposable Garage/TLS
fixture on loopback port 44390 with bucket `velero-probe` and a second ungranted
`other-probe` bucket. Set `PROBE_ROOT` to a private temporary directory. Supply
only synthetic `runtime/tls.crt`, `runtime/aws-credentials`, `runtime/key.json`
(`id`/`secret`) and `runtime/repository-password`; never production credentials.

Use the exact source/archive hashes in the evidence. In an AWS plugin 1.14.4
checkout, copy the AWS harness beside `object_store.go` and run `go test -v
object_store.go config.go helpers.go aws_object_store_test.go`. For Kopia, use a
new directory with the byte-identical Velero 1.18.4 `go.mod`/`go.sum`, copy the
harness as `main.go` and build it. Run `create`, stop/start Garage without removing
its data, then `restore`, `maintenance`, `restore-after-maintenance`, `negative`
and `cleanup`. Each operation uses its own cache; retain evidence and stop the
fixture afterward. The bootstrap repeat uses the ordinary documented
`bootstrap-store.yaml` against a separate empty disposable instance, not the
client test repository. Never apply this procedure to an existing app store.

References: [CSI data movement](https://velero.io/docs/v1.18/csi-snapshot-data-movement/),
[exact restore implementation](https://github.com/velero-io/velero/blob/v1.18.4/pkg/restore/actions/csi/pvc_action.go),
[Garage S3 compatibility](https://garagehq.deuxfleurs.fr/documentation/reference-manual/s3-compatibility/),
[Garage releases](https://garagehq.deuxfleurs.fr/_releases.html),
[Longhorn snapshot support](https://longhorn.io/docs/1.13.0/snapshots-and-backups/csi-snapshot-support/csi-volume-snapshot-associated-with-longhorn-snapshot/),
[Kubernetes local volumes](https://kubernetes.io/docs/concepts/storage/volumes/#local).
