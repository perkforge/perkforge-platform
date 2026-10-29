# Generic local enrollment stage (inactive proposal)

This adds only the protected enrollment repository to `local-identity`; it does
not name tenants or change existing Headlamp/Keycloak values. Each repo retains
its explicit local/environment/profile entrypoint. The new enrollment source and
Kustomization remain suspended; bootstrap still seeds a paused root.

Apply `../../enrollments/foundation` separately after approval, before selecting
this stage. Its trusted platform root writer can create Flux sources/reconcilers
in `flux-system`, which is an indirect controller authority. It is not a tenant
identity, must never be mounted by workloads, and may consume only protected
platform Git. Per-tenant permissions/foundations belong in enrollment Git.

The selected published chain is enrollment v0.2.0 → app configuration v0.2.0 →
source image v0.3.0. Release evidence records resolved commits separately. The
shared enrollment dependency advances for local/dev; dev workload values remain
unchanged. No automatic discovery, new Flux lifecycle or broad stack enable.

The proposed portal adds 25m/64Mi requests, a 192Mi cap and no controller/PVC; the
enrollment plan documents credential, policy, TLS/network and runtime approval.
Existing active stage/source and all live services are untouched by these files.
