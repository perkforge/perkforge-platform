# Existing identity-root hold

This source-owned intermediate retains the current reviewed enrollment A
`dd675360a87bbd1df545e75f522666e9c6b22e6b`, keeps the foundation root active,
and declares the existing `flux-system/identity-portal` with `spec.suspend: true`.
Its remaining specification is byte-equivalent after YAML parsing to platform
A `5218175` (the previously selected stage). The full application composition,
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
  explicit workload-start notice after all runtime gates. The stale A health
  expectations here are intentional while suspended, not a new-source readiness
  claim. A later pin change requires coherent reviewed expectations before resume.

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
