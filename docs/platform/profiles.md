# Add an impact-level profile

`profiles/il2` is a reusable selection label with existing Headlamp guardrails: no generated default ClusterRoleBinding and no unsafe service-account-token fallback. Actual IL2 preparation/hardening/evidence readiness is deferred. Neither this label, Big Bang adoption nor a copied il5 directory confers authorization.

1. Establish reviewed requirements and differences first. Copy `big-bang-bootstrap/profiles/il2/` to `profiles/il5/` as a structural starting point; author supported values and document the controls/gaps it actually contains. Do not treat IL5 as an environment or provider.
2. In the target's `kustomization.yaml`, replace the profile resource with `../../profiles/il5` and change the profile annotation. Its generator retains the `values-impact` ConfigMap name/key consumed by the umbrella. Set inventory impact_profile consistently; choose matching context in enrollment/app Git only when those are selected.
3. The profile merges after provider settings and before cluster values. Late cluster overrides can change values, so test effective rendered security invariants and reviewed exceptions rather than assuming directory placement enforces policy. Application profile settings cannot grant platform privileges or replace platform/enrollment controls.
4. Add profile-selection, mismatch and negative override tests under `big-bang-bootstrap/tests/configuration/` and `tests/security/`. Keep source/pin and safe-default checks. Existing synthetic tests exercise structural profile extension; they do not implement IL5 controls.

```sh
kubectl kustomize big-bang-bootstrap/profiles/il5
kubectl kustomize big-bang-bootstrap/clusters/<selected-target>
```

Then run the [full render/security checks](../../big-bang-bootstrap/tests/README.md) with explicit fixtures and inspect the resolved values. The operational playbooks currently guard local/il2; another profile needs reviewed guard/input support before execution. Do not weaken those gates to make a new label run. Deployment remains separately approved; compliance evidence and authorization remain their own work.
