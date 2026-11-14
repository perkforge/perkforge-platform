# Durable Kubernetes API log cursors

Native pinned operator child chart 1.11.0 / Alloy v1.18.0 supports a singleton
StatefulSet and retained volumeClaimTemplates. The former Deployment stored
`--storage.path=/tmp/alloy` on emptyDir; replacing its pod loses its Kubernetes
API positions and can replay records outside Loki's per-stream ordering window.
The 168-hour global rejection cutoff does not fix that separate replay problem.

This default-off offline renderer prepares two values files: replicas=0 for the
transition and replicas=1 for operation. It does not select a root or mutate any
resource. The local deployment uses a reviewed 1Gi Longhorn claim. This is not a
long-term measured sizing recommendation or an automatic sizing decision. Target storage class,
size and eligible node selector are configurable; no hostPath or host changes.
The existing mount and component DataPath stay unchanged. CPU, memory, pinned
images, identities, network, processing stages and log data remain unchanged.

## Reviewed transition prerequisites (not an executable shortcut)

1. Freeze the latest reviewed composition, including Portal Viewer-only overlay
   when merged, Mattermost, current alerting and SSO. Render both stages against
   that exact base. Preserve every unrelated object, the complete CA volume and
   all existing mounts. Refuse an unexpected current volume list. Check actual
   worker scheduling requests, Longhorn capacity/replicas and restricted seeder
   image support before proposing live execution. No unrelated workload moves.
2. Read the exact existing pod UID, controller UID, Alloy component DataPath and
   positions file. Capture a **recent checkpoint before** deleting/replacing the
   old pod: native positions persistence uses atomic rename. Validate YAML/key
   schema, numeric cursor offsets, bounded size and timestamp freshness; preserve
   target keys byte-for-byte. Save only positions, not other state or log bodies,
   to a protected retained artifact with SHA256 and source UID/time receipt.
   Do not call it the final flushed cursor without actual proof.
3. Apply reviewed stage 0 through the same GitOps chain, wait for old Deployment
   and every old collector pod to terminate, and verify no active writer. Type
   change alone must not start a second writer. Do not assume RWO prevents two
   writers on the same node. Preserve the checkpoint if reconciliation fails.
4. Create/verify the exact retained claim `alloy-storage-alloy-alloy-logs-0`,
   matching the rendered StatefulSet claim template, size/class and ownership;
   never adopt or overwrite an unknown nonempty claim. Use one bounded restricted
   no-token seeder with the existing approved image/pull identity if its native
   runtime supports the operation. Seed only the exact component positions path;
   enforce correct UID/GID, hash readback and no other content. Remove the seeder
   and prove no active writer before stage 1. The default-off capture/prepare-claim/seed playbooks implement those gates;
   independent review and explicit live invocation remain REQUIRED.
5. Require checkpoint lag comfortably below the verified one-hour stream window
   (proposed hard guard 10 minutes), exact cluster/controller/claim identities and
   seed equality before stage 1. If timeout, remain stopped and report; do not
   enable an empty cursor or silently shorten collection history. Prepare the
   target claim before the bounded pause where safe to minimize that risk.
6. Start stage 1, verify same target keys/DataPath, persisted cursor advance and
   actual new log delivery. Check prior stored markers, fresh drop/retry metrics,
   source errors, memory/PVC use and all unrelated workload health. A later single
   controlled restart should prove cursor reuse, not merely PVC existence.

Fix forward on failure: retain claim and checkpoint, hold replicas=0 if migration
cannot be verified, correct reviewed source and resume only from validated state.
Do not revert to emptyDir or delete the PVC/checkpoint to make rollout green.
No live transition is included in this source proposal.

## Guarantees and gaps

Native API tailing saves offsets after passing entries to its internal handler,
**not after Loki acknowledgement**. Durable positions reduce restart replay;
they are not a delivery WAL, exactly-once guarantee or proof of no loss. Historical
batch errors are not retroactively recovered. Pod identity/target-key changes
also need separate lifecycle consideration; preserving the storage path alone
is not enough.

Current delivery alerts detect sustained writer drops/retries and missing writer
telemetry, not all source discovery failures. Pinned `loki.source.kubernetes`
reports component health only for invalid configuration and exposes no dedicated
source metrics; target debug metadata has latest line/error information. Do not
claim scrape-up proves collection completeness.

## Supported gated tooling

`render.yaml` emits values and exact claim manifest only. Checked-in stage-0 and
stage-1 artifacts are tested equal to renderer output; both selectable roots
inherit `local-portal-log-view`, so Viewer-only authorization is preserved.
Publish/review BOTH stages before any pause. Do not wait for a new PR while paused.
`local-logging-cursor-prepare` stops collection; successful Helm reconciliation at
replicas zero is not healthy collection. Existing missing telemetry alerts are
not silenced during the bounded maintenance window.

`prepare-claim.yaml` is create-only and requires explicit cluster identity and
approval. Existing claims require a separately verified UID, no adoption. This
physical-target activation wrapper is deliberately bound to Longhorn/1Gi; other
environments must supply a reviewed target-specific wrapper, not bypass guards.
Prepare and bind it while the old collector still runs where possible.

`capture.yaml` requires exact cluster/deployment/pod UIDs and a NEW protected
output directory. It copies native structured-key YAML without reserializing or
printing keys, verifies file sync freshness, and writes a digest/identity receipt.
Quiet pod offsets may legitimately be old: freshness applies to the checkpoint
capture/source-file modification time, not every individual offset.

`seed.yaml` requires a stopped old Deployment, zero matching collector pods,
expected zero-replica StatefulSet and exact retained claim UID. It checks the
checkpoint again before and after copying, uses the previous collector's exact
resolved image digest with restricted nonroot/no-token context, rejects unknown
volume content/symlinks (including nonempty, symlink or unreadable lost+found), verifies readback hash, and UID-checks temporary seeder
cleanup. It never starts the StatefulSet or selects a root. A partial incoming
file deliberately blocks a retry: inspect exact expected digest/ownership and
resolve through reviewed recovery, never blindly wipe it or other volume data.

After seeding, recheck the same UID/hash/freshness gates and zero writers before
selecting the already-published stage-1 path. Longhorn readiness, command support
in the pinned seeder image and actual admission remain runtime preflight gates;
o live transition has been performed by these offline tests.

Capture requires a new canonical nonsymlink directory and binds the pod through
its ReplicaSet to the expected Deployment. Native metadata verifier uses bounded
no-follow open/fstat/read, rejects changing/oversize/nonregular files, and prints
only digest/counts. Seed pins all component/claim paths, rejects every existing
namespace pod referencing the PVC (not only collector labels), and checks exact
StatefulSet selector, claim template, storage mount, observed generation and
zero replicas. Final controller resourceVersion/spec/claim UID and PVC-user
checks detect concurrent reconciliation; failures do not authorize stage 1.

### WaitForFirstConsumer preflight (before the bounded pause)

The physical Longhorn class uses WaitForFirstConsumer. After create-only claim
preparation, run separately approved `volume-preflight.yaml` while the original
collector remains running. It binds only the exact new claim using a short-lived
restricted helper, the current collector's resolved image, UID/GID/fsGroup473,
no API token, no added capabilities and a privately verified eligible target node.
It refuses other PVC users/unknown contents, verifies a tiny owned marker/hash,
removes that marker, proves two RW replicas and healthy volume state, then deletes
the exact helper UID and waits for detachment/no remaining PVC users. This is not
a checkpoint or collector cutover. Failure leaves the collector untouched and
blocks migration. No storage-class/kernel-module/host changes are performed.

Only after this preflight should a fresh checkpoint be captured and the already
published stage0→seed→stage1 sequence begin. Do not relax the seed Bound check to
work around first-consumer ordering. Current worker backup activity, scheduler
headroom and actual replica health must be considered before choosing the helper
node; reusable collector placement remains on eligible storage workers.

## Verified local deployment checkpoint: 2026-11-14 17:10 UTC

Reviewed PRs #457 and #459 were merged before migration. Immutable source
`052f0f07dc42d98c9bded7dab7b6ddb2f50064b7` selected
`clusters/local-logging-cursor-durable`, preserving the Portal Viewer-only,
Mattermost, Grafana and existing logging composition. This is a dated deployment
checkpoint, not a requirement for other environments to use the local storage
class, node placement or claim size.

- The separate restricted first-consumer preflight verified the new retained
  1Gi claim, writable filesystem, two healthy RW Longhorn replicas, owned marker
  cleanup and helper removal/detachment before the collector was paused.
- A recent 90,600-byte checkpoint contained 168 targets. Its exact SHA256 matched
  seed readback. Stage 0 was selected at 16:58:17 UTC; stage 1 at 17:01:44 UTC,
  when checkpoint age was 258 seconds, within the 600-second gate. The old
  Deployment was absent and there were no competing PVC writers during seeding.
- The replacement StatefulSet pod was created at 17:04:57 UTC on an eligible
  storage worker. Native Alloy upgrade succeeded at 17:05:02; root health passed
  at 17:07:03. Collection was deliberately paused during the transition; source
  selection is not the exact instant of stop/resume. Normal Helm values-watch
  reconciliation added delay. No rollback, second restart or emptyDir fallback
  was used to obtain this evidence.
- At 17:06:55 the collector was 2/2 Ready with zero restarts, using the retained
  claim and unchanged component path. All 168 prior target offsets were present
  and nondecreasing; 116 had advanced and five new targets were present. This
  proves checkpoint continuity and subsequent cursor progress, not a captured
  wire-level audit of every Kubernetes `SinceTime` request.
- At 17:10:34 the new writer had sent 11,294 entries / 1,802,242 bytes, with zero
  dropped entries, dropped bytes or retries since this process started. A fresh
  180-second Grafana datasource query returned HTTP 200 and 20 records across
  four streams. Platform Loki, legacy pilot Loki and Prometheus health checks
  remained successful. Collector cgroup memory was about 111MiB of 512MiB with
  no OOM/max events. These are bounded early recovery observations, not a
  long-term delivery guarantee.
- Separate household-backup recovery verification confirmed Nextcloud Ready,
  installed and out of maintenance, without a pending database upgrade. The
  separately authorized backup upload was still ongoing; no archive completion
  is implied by this logging checkpoint.

Native positions advance before downstream acknowledgement. Retained cursors
reduce restart replay but are not an end-to-end delivery WAL, exactly-once or
lossless guarantee. No additional collector restart was induced merely to prove
retention. Previous historical/mixed-age batch loss is not erased by this change.
Issue #38 remains open for remaining retention deletion evidence, coverage and
broader acceptance; configured 72-hour retention is not observed pruning proof.
The #449 delivery alerts are live and separately completed, but writer telemetry
is not proof of discovery completeness or universal application-log redaction.
