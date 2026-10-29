# Generic local enrollment activation selection

This adds only the protected enrollment repository to `local-identity`; it does
not name tenants or change existing Headlamp/Keycloak values. Each repo retains
its explicit local/environment/profile entrypoint. The new enrollment source and
Kustomization are explicitly unsuspended only for local. Bootstrap still seeds a
paused root; selecting this stage on the live cluster requires separate approval.

Apply `../../enrollments/foundation` separately after approval, before selecting
this stage. Its trusted platform root writer can create Flux sources/reconcilers
in `flux-system`, which is an indirect controller authority. It is not a tenant
identity, must never be mounted by workloads, and may consume only protected
platform Git. Per-tenant permissions/foundations belong in enrollment Git.

The selected published chain is enrollment v0.4.0 → app configuration v0.3.0 →
source image v0.3.0. Release evidence records resolved commits separately. The dependency is explicitly selected for local; additional targets require their own reviewed roots. No automatic discovery, new Flux lifecycle or broad stack enable.

The proposed portal adds 25m/64Mi requests, a 192Mi cap and no controller/PVC; the
enrollment plan documents credential, policy, TLS/network and runtime approval.
Existing active stage/source and all live services are untouched by these files.


Before live activation, approve and verify generic/tenant foundations, admission
dry-run denials, registry and OIDC/TLS/CA inputs, exact Keycloak client/admin-role
mapping and routing. Advance the root only after those prerequisites; Kustomize
file order is not a readiness dependency mechanism. No existing release settings
change in this stage. Existing released roots do not follow main or these moved paths automatically.

Containment: suspend cluster-root before the parent, then new enrollment/portal
child/source/HelmRelease; scale only portal to zero. Root suspension pauses manifest
updates, not existing running services or HelmRelease controller reconciliation.
Preserve credentials/foundations; select a reviewed paused stage before root resume.
