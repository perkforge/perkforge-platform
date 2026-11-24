# Longhorn backup stage diagnostics

Use this runbook when a stateful application resumes but its scheduled backup
has no new verified result. A healthy workload, a successful database dump, a
ready storage snapshot, a completed backup and a tested restore are **different
results**. Record each separately. This is read-only triage, not an activation,
retry or restore procedure.

## Triage one run

1. Verify the intended cluster/context, the app's PVC-to-PV-to-Longhorn volume
   mapping and the expected backup target. Use the approved read-only identity
   and explicit context, not a default cluster or elevated credentials. Compare
   the installed product/chart version and data engine with the reviewed GitOps
   selection; use the schema/docs for the installed version.
2. Correlate the scheduler invocation, capture status and storage events to one
   run ID and UTC window. Start with the orchestrator's stage receipts; if
   applicable, check the corresponding job/service's result and timestamps. For
   each row below, a missing receipt means unconfirmed, not automatically failed.
   Investigate the first failed or unconfirmed gate, not the last cleanup line.

| Stage | Evidence for this run | If missing or failed |
| --- | --- | --- |
| Database export and validation, if applicable | Export receipt plus the workload's validation result | Check the application-specific export/validation result. This cannot establish file/volume capture. |
| Prepare consistent capture | The required writer pause, flush and quiescence checks all passed | Distinguish a failed flush from inability to verify that writers stopped. Check whether workload recovery ran; do not leave writers paused to debug. |
| Storage snapshot | The expected snapshot is ready, matches the source volume and belongs to this invocation | Inspect the exact snapshot's status, error and events in the run window, then the volume's health/attachment and the controller's matching error class. An old ready snapshot or missing receipt is not proof of this run, or of a storage defect. |
| Upload and verify destination | A completed backup/artifact from that snapshot (and companion export, when required) is readable at the intended target and passes the workflow's integrity checks | If no upload started, stay upstream. Otherwise check this backup's state, then target reachability, capacity, authorization and overlap as indicated. In progress is not success. |
| Recover application | Writers resumed, workload ready and its scoped health check passed | Treat incomplete recovery as a separate incident. Preserve the failure that preceded it, even if recovery succeeds or produces another error. |

For orchestrators that back up only after writers resume, record the recovery
step before upload. The table is a list of evidence gates, not a reason to keep
writers paused longer than the workload's approved capture procedure.

Longhorn's native `Snapshot` resource in `longhorn.io` and Kubernetes' CSI
`VolumeSnapshot` in `snapshot.storage.k8s.io` are different resources. Inspect
the type that the workflow actually created. For a CSI capture, confirm the
bound content/source and `status.readyToUse` plus any reported error; for a native
capture, confirm the matching Longhorn volume and ready/error status. If using
Longhorn Backup, correlate the matching Backup record and completed target
result; if the orchestrator exports instead, check that system's destination
receipt, not an unrelated Longhorn Backup object.

If native Snapshot `status.error` identifies the snapshot-count limit, compare
the exact source Volume's `spec.snapshotMaxCount` with the running engine's
effective limit and snapshot inventory. A list of Snapshot objects can include
failed requests that never occupied an engine slot. A count-limit refusal before
Backup creation concerns the source volume; it does not test NFS or other
destinations.
Review the chain and known-good copies before any capacity or retention change.

Longhorn backup inventory refreshes asynchronously. Read `BackupTarget`
`status.available` and `status.lastSyncedAt` as reachability and freshness clues.
In [v1.13.0](https://github.com/longhorn/longhorn/blob/v1.13.0/chart/templates/crds.yaml#L831-L842),
the `LastBackupAt` printer column displays `spec.pollInterval`, not a backup time.
Stale inventory does not prove upload failure, and a fresh sync does not prove
this run completed. Require its matching destination receipt.

## Preserve evidence before changing anything

- Keep the **first failed stage and fixed reason code** even if subsequent
  cleanup overwrites current phase. Store separate recovery status and
  timestamps. If the exact step or reason is not known, report the interval and
  that it's unconfirmed. Example: database validation passed; snapshot not
  verified; no upload recorded; recovery passed; cause not yet known.
- A shareable receipt needs only run ID, UTC time, stage, sanitized reason,
  destination verification status and recovery status. Record the tested restore
  independently. Keep exact resource correlation and any necessary logs in
  restricted operator evidence; don't put credentials, target URLs, user paths,
  raw events or support bundles in public Git.
- Retain the last independently verified backup. A retry, suspension change,
  forced detach, deletion, retention adjustment, or workload restart is not a
  troubleshooting default. Review cause, current health, active/overlapping jobs
  and the normal next-run window first; obtain separate approval for changes.
- Validate an observability change on the next approved run by checking the
  same-run snapshot and destination receipt as well as application recovery.
  Verify recoverability separately using a disposable restore target, sample
  integrity checks and an application read (including matching database/files
  when required). No successful restore is implied by routine backup status.
  See [Restore and validate in isolation](https://github.com/perkforge/perkforge-portal/blob/main/docs/backup-restore.md#restore-and-validate-in-isolation)
  for the application-level checklist.

References: [Longhorn snapshots](https://longhorn.io/docs/1.13.0/snapshots-and-backups/setup-a-snapshot/),
[Longhorn backups](https://longhorn.io/docs/1.13.0/snapshots-and-backups/backup-and-restore/create-a-backup/),
[Kubernetes volume snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/).
