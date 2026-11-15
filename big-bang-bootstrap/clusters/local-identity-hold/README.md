# Existing identity-root hold

This reviewed second holding stage selects corrected enrollment A
`0732cff9aff9815d1bedec4b94ff2883ce75b577`, keeps the foundation root active,
and declares the existing `flux-system/identity-portal` with `spec.suspend: true`.
Its remaining specification preserves the previously selected platform A
`5218175`, with only the reviewed foundation readiness hash updated. The full application composition,
service account, dependencies, source, health checks and permission boundaries
are preserved. No Pod or Job is selected directly.

## Initial and follow-on use

- For initial setup this may create an already-suspended phase root; the
  foundation-only sibling is sufficient when no phase root has ever existed.
- For follow-on preparation, use this explicit hold rather than removing the
  phase root from a `prune: false` composition. Removing it would leave the old
  object independently reconciling. First select this hold with the **old**
  enrollment pin, then verify the exact native root has `spec.suspend: true`,
  its reconciliation is quiescent, and no phase child Kustomizations or Jobs
  exist. Only afterward may a separately reviewed source selection update the
  held enrollment pin and its foundation expectations. Do not combine these
  transitions or infer that a Ready condition proves suspension was observed.
- Suspending this parent does not suspend existing child Kustomizations, stop
  running Jobs, undo earlier writes, or cancel an in-flight reconciliation.
  This stage is appropriate only at the verified pre-child checkpoint. Stop
  and reassess if any child/workload exists; do not delete it as implicit cleanup.
- Resume only through a separately reviewed active onboarding composition and
  explicit workload-start notice after all runtime gates. The A health expectations remain explicit and must match before resume;
  suspension itself is not a new-source readiness claim.

The pinned [Flux kustomize-controller v1.9.5 reconciliation source](https://github.com/fluxcd/kustomize-controller/blob/v1.9.5/internal/controller/kustomization_controller.go#L168-L172)
returns for a suspended Kustomization before resolving its source, dependencies,
or applying manifests. This source inspection is not a live suspension test.
This overlay adds no grants, credentials, image changes, or automatic retries.

### Suspension readback

The pinned controller emits the INFO log `Reconciliation is suspended for this
object`, but no dedicated Suspended condition or Kubernetes event. Its deferred
status patch may retain old Ready/Reconciling conditions; observedGeneration is
not a reliable suspension acknowledgement. Verify the exact root UID and
`suspend: true`, the unchanged enrollment pin, and a post-hold suspension log
for this namespace/name from the single active controller leader. Controller
runtime serializes reconciliations of the same object, so observing that newer
suspension branch establishes that the previous same-key run has finished in
that controller. Recheck that no phase children or Jobs exist. If logs or leader
continuity cannot establish this, retain the old source and admission denial;
do not substitute an arbitrary sleep or stale Ready condition.

See [deferred status handling](https://github.com/fluxcd/kustomize-controller/blob/v1.9.5/internal/controller/kustomization_controller.go#L1192-L1215)
and [pinned same-key serialization](https://github.com/kubernetes-sigs/controller-runtime/blob/v0.24.1/pkg/internal/controller/controller.go#L272-L280).

### Ordered source transitions

1. First select this path at immutable platform ancestor
   `5992baf62f69d74ee22de75af473dae401d3e72e`. That version retains the old
   enrollment pin `dd675360a87bbd1df545e75f522666e9c6b22e6b`. Confirm native
   suspension and zero phase children/Jobs before moving further.
2. Then select this path at the reviewed corrected A platform stage. This
   version selects corrected enrollment A and keeps `suspend: true`. Verify
   foundation/admission readiness and the native kubelet preflight separately.
3. Only after those gates and the promised workload-start notice select the
   corresponding `local-identity-onboarding` A stage. Its explicit
   `suspend: false` resumes the existing parent; membership remains held in
   enrollment A. Do not rely on omission of the SSA-managed suspend field.
4. Select onboarding B only after real nonempty evidence survives metadata SSA
   and all freshness/identity gates pass. B changes only onboarding source,
   readiness hash and membership health selection; HOLD/foundation retain A.

The first old-pin hold and later corrected-source hold are separate selections.
Skipping the first verification could let an already running old reconcile see
newly admitted source shapes. This document authorizes no live transition.

### Safe selection when the hold path is new

Inspect every consumer of the enclosing GitRepository and the currently selected
path before changing its revision. A commit can contain a held overlay and an
unselected released overlay; changing the revision first while retaining the old
onboarding path can select the wrong stage. At the verified pre-child checkpoint,
if the current artifact lacks the new hold path, select that path first and wait
for the new root generation to report the expected missing-path ArtifactFailed
against the unchanged old artifact. The pinned controller returns before apply
or prune on this failure. Only then select the reviewed old-pin hold commit.
Continue with the suspension/quiescence proof above; do not treat the deliberate
missing-path failure itself as suspension. Preserve existing workloads throughout.

The pilot repository also feeds the Velero backend HelmChart with Revision
reconciliation. Its unchanged chart bytes can still cause a metadata-equivalent
Helm reconciliation when the source revision changes. Verify consumer templates,
values and hooks before selection; do not promise that no other reconciler runs.
