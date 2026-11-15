# Explicit Portal onboarding overlay

This optional source selection inherits the complete local application baseline.
It changes only the enrollment repository immutable ref and adds two native Flux
Kustomizations. Existing Nextcloud/Portal consumer paths, Grafana, logging, sharing
policy, alerts and workload values remain unchanged. No credential material or
bootstrap security grant is included here.

Prepublish/review the paired enrollment and platform stages before live work.
Enrollment A `ccfb231c3ad0e70af8682d535d320ca0449d2897` holds memberships;
B `e3c1878a219b402b7b7a1cb3776f1d2fab6e1328` releases only after actual issuer/SSA
acceptance. Both use the same released executable pins and Job inputs/names.
Preserve both commits through a normal merge commit, not squash/rebase.

The foundation-root creates the source-owned admission and controls reconcilers.
The declaration root depends directly on controls with the paired literal
foundation digest, current observedGeneration and Ready status. It intentionally
has no commonMetadata injection because that would alter the exact evidence CM.
Its health checks wait for foundation/attest in stage A, then also memberships in
B; an intentionally suspended membership phase is not falsely reported healthy.

Do not select this overlay until separate approved bootstrap guards/grants, exact
existing UID checks, native defaulting/admission/RBAC/SSA proofs, isolated ESO
custody and restricted private-volume initialization pass. The proposed adoption
authority includes named bind/escalate and two structurally bounded future-attempt
Role templates; that is additional explicit security consent, not inherited from
source review. Future profile, image, namespace or authority changes still require
review. The source does not automate Keycloak/provider bootstrap or late-login
retry, and unsupported storage profiles remain fail-closed.

Notify the owner immediately before the initializer and first Job. Recheck actual
scheduler/storage/household load; never stop the HGST copy implicitly. If live
nonempty issuer-data preservation and source readiness exceed the five-minute
receipt lifetime, use a new explicit attempt rather than weaken freshness.
Failed readiness retains claim/receipts and does not trigger blind rollback or
old-Job replay. See the paired enrollment `docs/identity/portal-activation.md` for
exact executable provenance, budgets and remaining acceptance limits.

First select corrected H through local-identity-child-pause and verify all three
children held on the corrected source. Only then select A at this path to resume
foundation/attest with memberships held. H remains pinned independently at B.
The new Job suffix is 54819c8b56bfc3e8; the actual prior foundation is bound at retry generation one, while the
explicit attestation predecessor remains empty because no issuer receipt existed.
