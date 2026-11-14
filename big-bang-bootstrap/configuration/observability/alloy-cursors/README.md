# Durable Kubernetes API log cursors (proposal, not activated)

Native pinned operator child chart 1.11.0 / Alloy v1.18.0 supports a singleton
StatefulSet and retained volumeClaimTemplates. The current Deployment stores
`--storage.path=/tmp/alloy` on emptyDir; replacing its pod loses its Kubernetes
API positions and can replay records outside Loki's per-stream ordering window.
The 168-hour global rejection cutoff does not fix that separate replay problem.

This default-off offline renderer prepares two values files: replicas=0 for the
transition and replicas=1 for operation. It does not select a root or mutate any
resource. The default 1Gi Longhorn claim is a proposed minimum operational volume,
not measured cursor growth or an automatic sizing decision. Target storage class,
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
   and prove no active writer before stage 1. A dedicated guarded migration
   implementation and native review are REQUIRED before executing this plan.
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
