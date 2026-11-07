# Disabled tenant recovery preparation

One common contract, local and future AWS profiles. Platform operators own Velero,
its API, repository keys and object store access. Tenants never run it or receive
those credentials. Namespace filters select content; they are **not authorization**.
A separately reviewed installer/controller/node-agent permission and admission
boundary is required. This directory is not selected by any root or valuesFrom.
There is no deploy/apply/backup/restore command here.

## What this source does

- Keeps the addon disabled, Flux suspended, node agent/backup/snapshot resources
  disabled, CRD hooks off and schedules empty. No new RBAC or credentials.
- Validates a reference-only recovery request through native Ansible and writes
  one private, non-applyable review bundle when explicitly requested. Default and
  check modes are inert. It never contacts Kubernetes, AWS, S3 or a tenant.
- Uses one tenant namespace per recovery request. Multi-namespace applications
  require a separately reviewed consistency and restore mapping extension.
- Prepares Backup/Restore **spec fragments**, a paused schedule plan and immutable
  release identity. It emits no actionable Backup or Restore objects.

Run the safe default or syntax check from this directory:

```sh
ansible-playbook -i localhost, prepare.yaml
ansible-playbook -i localhost, prepare.yaml --syntax-check
```

To review proposed disabled profile inputs, supply a public copy of `request.example.yaml` and an
existing private (0700) output directory. `velero_prepare` must be a YAML/JSON
boolean, not a string. Both profiles run the same playbook:

```sh
ansible-playbook -i localhost, prepare.yaml -e @/path/to/reviewed-request.yaml \
  -e '{"velero_prepare":true,"velero_environment":"local","velero_output_dir":"/path/to/private-review"}'
```

Use `aws` for the other profile. Preparation requires explicit proposed storage
classes, endpoint, region, bucket/prefix, CA/identity references and AWS KMS reference.
These can identify proposed resources; preparation does not connect or assert they
exist. Empty source-profile fields fail. It does **not** require an already-installed
Velero, backup or acceptance receipt. Recovery fields may remain empty and no backup,
schedule or restore spec fragment is emitted in that mode.

Only for a complete, separately reviewed recovery request, add the boolean
`velero_review_recovery: true`. This enables the stronger namespace, consistency,
immutable-version, retention, backing-capacity and recovery-point input checks and
includes the non-applyable spec fragments. Do not invent evidence to pass a guard.
Nonempty references and declared quota bytes do not prove approval, actual quota
installation, compatibility or successful recovery. A reviewer must inspect the
referenced evidence; every output still says readiness unverified and preserves
the local quota-maintenance blocker. `velero_apply`, tenant access or schedules cannot be
enabled by this procedure. No output is permission to activate anything.

## Actual pinned compatibility and remaining gates

[Compatibility evidence](compatibility.yaml) records Big Bang **3.35.1** selecting
Velero wrapper **12.2.1-bb.0**, upstream chart **12.2.1**, Velero **1.18.4** and AWS
plugin **1.14.4**. The exact wrapper archive and vendored dependencies were inspected.
The official plugin matrix pairs 1.18.x with 1.14.x; newer 1.19.x/1.15.x are not
selected. No shared pin is bumped. CSI support is integrated into modern Velero;
do not add the historical standalone CSI plugin listed in wrapper annotations.

Upstream 1.18 expects Kubernetes 1.18-latest but tests 1.33.7, 1.34.1 and 1.35.0.
The current target 1.36.5 needs explicit compatibility/recovery evidence; this is
**unverified**, not proof of incompatibility. Chart kubeVersion >=1.18 is not a
runtime acceptance test. Before activation, verify immutable image digests,
installer and runtime privileges, APIs/CRDs, hooks, S3 transport/plugin behavior,
node-agent placement/resources and a copied-byte restore on the actual target.

The wrapper auto-creates a generic `csi-volumesnapshotclass` with Delete policy
when `features: EnableCSI`, defaulting to the EBS driver. The inert candidate does
not set that feature. Before activation, suppress/replace that template through
the existing Flux post-render path and have the platform foundation own an explicit
provider-specific class, driver, parameters and cleanup policy. Do not deploy an
EBS class onto Longhorn. No VolumeSnapshotClass or Velero was installed at inspection;
snapshot CRDs/controller were available. Chart rendering is not driver acceptance.

## Local means filesystem space outside Longhorn

The proposed backend is a **separate S3-compatible service** on a dedicated bounded
directory/static local PV on worker-2, outside Longhorn replica/metadata paths.
It is not a Longhorn-provisioned backup PVC and must not reuse GitLab Garage,
its buckets or keys. Product selection, service resources and capacity are undecided.
The existing disk is one XFS filesystem, not spare unpartitioned space.

Read-only inspection on 2026-11-07 found about 931 GiB total/910 GiB free,
279 GiB Longhorn reserve, 49 GiB scheduled, 25% minimum-free and no overprovisioning.
Actual mount options include **noquota**. Free space is not an exclusive backup
allocation, Longhorn reserve is not a filesystem quota, and a PV capacity declaration
is not a disk quota. Operational recovery review requires references for enforced filesystem
quota plus reconciled Longhorn capacity reservation, bounded backend usage and
additional snapshot/temporary restore/cleanup headroom. Current noquota blocks that
acceptance until separately approved mount/quota maintenance. This PR selects no
capacity, creates no directories/mounts/PVs, and changes no reserve or host setting.
Use node affinity and Retain for the future static local PV; account for unavailable
worker-2 and manual reclaim. Same-node/disk recovery is **not independent disaster
recovery**. Keep an independent copy for node, disk, site or operator loss.

Longhorn 1.13.0 here uses the V1 engine with ext4. Favor CSI snapshot plus **Kopia
snapshot data movement** to copy PVC bytes into the repository, not snapshot
references alone. Validate actual DataUpload/DataDownload completion and restore
bytes independently of the source PV/snapshot. The spec fragments are **unvalidated
candidates**, restricted to completed CSI data movement for every selected PVC;
no snapshot-only/native-PV fallback is accepted. In pinned 1.18.4, the CSI PVC action
reads DataUpload results, clears the original volumeName and creates DataDownload
for the target. That explains the proposed cluster-resource exclusion without
assuming PV/VolumeSnapshotContent metadata is automatically included. The generic
resource filter can exclude those resources; accepting any non-moved volume would
need a different explicitly reviewed plan. Source inspection does not prove the
complete backup/restore flow. Read [the exact data-movement restore branch](https://github.com/velero-io/velero/blob/v1.18.4/pkg/restore/actions/csi/pvc_action.go)
and [upstream storage-class requirements](https://velero.io/docs/v1.18/csi-snapshot-data-movement/#configure-storage-class-on-target-cluster). Do not assume V2 linked-clone support.

## AWS uses the same recovery contract

The future profile changes retention to 336 hours, driver to `ebs.csi.aws.com`
and backing to durable S3. Require explicit source/restore StorageClass and
VolumeSnapshotClass mapping, topology/region, TLS endpoint/CA trust reference,
platform workload identity, least-privilege bucket policy and KMS references.
No AWS target, IAM grant, bucket, key, snapshot or credential is created here.
CSI plus data movement remains the proposed path rather than an EBS snapshot-only
DR claim. Review cross-zone/region/account recovery and object/KMS availability.
S3-compatible local service behavior with the pinned AWS SDK/plugin must be tested.

## Functional service recovery, not only PVC recovery

1. Approve the tenant and isolated restore namespace/capacity. Inventory every
   resource, config/Secret, PVC, object store and database dependency. Backups are
   confidential, including any selected application Secrets; custody is platform-only.
   Pre-create reviewed namespace/admission/network/quota and omit cluster-scoped
   resources, RBAC, service accounts and Flux control objects from tenant recovery.
2. Record exact immutable app image/chart digests, app/platform/enrollment commits,
   database engine and schema versions alongside the backup in the protected recovery
   catalog. Record which app Secrets/config versions must match without copying them
   into Git. Do not restore old data under a newer incompatible app/schema.
3. Use reviewed application-specific quiesce/checkpoint/freeze and thaw hooks with
   timeouts and fail-closed behavior. Guarantee thaw/rollback on hook, snapshot or
   upload failure in the operational plan. CSI snapshots alone are crash consistency,
   not application/database consistency. Shared database tenants need DB-native
   selective recovery; never restore a shared DB PVC over unrelated tenants.
4. Before upgrading, require a Completed backup with no partial failures and completed
   data uploads, known-good DB recovery point and sufficient rollback TTL. Failed
   backup, missing bytes or unproven thaw blocks upgrade. Keep the last known-good
   pre-upgrade point through the entire rollback window, including age before upgrade.
5. Explicitly suspend the relevant Flux app reconciliation and any database/application
   operators under a reviewed scoped plan before recovery. Restore into the approved
   isolated namespace, never overwrite a running tenant with existingResourcePolicy
   update. Map storage with the reviewed Velero change-storage-class mechanism and
   restore hooks; the spec fragment alone does not implement this mapping. Restore
   hook namespace selectors use the **target** namespace: pinned 1.18.4 groups exec
   hooks against the created Pod and maps init-hook selection to the target too.
   Backup hooks still use the source namespace. See the
   [native hook selector](https://github.com/velero-io/velero/blob/v1.18.4/internal/hook/item_hook_handler.go).
   Inspect backed-up Pod hook annotations too: they can override spec hooks.
6. Verify checksums/data, DB/schema consistency and real service login/read/write
   using the matching release/config. Account for tenant dependencies, endpoints,
   TLS/Secrets and identity. Then separately approve cutover and resume reconciliation
   against matching Git. Preserve the original failed volumes until accepted cleanup.
   Nextcloud currently fully allocates its two-PVC/48 GiB quota; isolated restore
   needs separately planned namespace/quota/capacity, not reuse of that allowance.

## Retention and schedules

Local proposed TTL is **48h**; AWS is **336h**. Cadence, maximum acceptable data loss
(RPO), rollback window and missed/partial backup alerts still need decisions. The optional recovery-review
contract rejects a rollback window plus RPO that consumes the TTL. Review the cron
against the stated RPO; syntax validation and a paused plan do not establish cadence.
No schedule is created or resumed. A future schedule must remain paused until
acceptance; prevent surprise first runs and do not owner-reference backups to it.

Velero expiration requires a running controller, backup deletion and Kopia repository
maintenance/garbage collection. Monitor stale backups, failed deletions, repository
health and backend usage; TTL is not a precise physical-space bound. Do not set a
blanket object-store lifecycle that deletes shared Kopia chunks by object age.
Encryption/repository-password custody and independent restore tests are separate
gates. Never expire the last valid recovery point merely because an upgrade failed.

## Verification

```sh
KUBECONFIG=/dev/null PYTHONPATH=big-bang-bootstrap/tests \
  python3 -m unittest bootstrap.test_velero_preparation -v
```

Run from the repository root. Tests use synthetic public references, local Ansible and a pure offline URL/cron
verifier (Python verifies inputs; Ansible/YAML alone owns configuration). Exact chart tests additionally need `VELERO_CHART_SOURCE` pointing
to the archive above after SHA256 verification, `PREFLIGHT_SOURCES_DIR` containing
the existing checksum-verified Big Bang fixture, and Helm on PATH. Missing fixtures
are explicit skips. All current cluster roots must remain byte-equivalent. No live
backup, upload, restore, credential, installer/RBAC or capacity acceptance is claimed.

Sources: [Velero CSI data movement](https://velero.io/docs/v1.18/csi-snapshot-data-movement/),
[backup](https://velero.io/docs/v1.18/backup-reference/),
[restore](https://velero.io/docs/v1.18/restore-reference/),
[Longhorn V1 CSI snapshots](https://longhorn.io/docs/1.13.0/snapshots-and-backups/csi-snapshot-support/csi-volume-snapshot-associated-with-longhorn-snapshot/),
[Kubernetes local volumes](https://kubernetes.io/docs/concepts/storage/volumes/#local).
