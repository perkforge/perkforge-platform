# Admin-only Portal pilot

This optional root preserves the ntfy owner, query isolation and native ESO stages.
It selects the released enrollment's `local-nextcloud-portal` composition; the
Nextcloud objects are unchanged. It does not create credentials or replace the CA.

Before selecting this root, use the published enrollment operator procedure:

1. Configure the dedicated `portal-local` client with `platform-admins` policy.
   Use the existing signed platform group; do not map a tenant role to it.
2. Seed only Portal OIDC, approved GHCR pull credentials and the verified TLS leaf
   into the three scoped OpenBao records. Keep operator inputs outside Git.
3. Render and apply the Portal public trust, approved ingress/issuer egress and
   namespaced ESO consumers. Require valid Store, three synced consumers and
   exact runtime Secret payload equality before proceeding.
4. Apply the matching platform-owned runtime image contract, then promote this
   root through a verified immutable platform commit. Preserve existing apps.

The selected configuration uses app v0.3.1's immutable image, built and published
once by its normal release pipeline. Verify fresh Flux generations, Portal rollout,
trusted HTTPS, unauthenticated API/BFF denial and the native OIDC login redirect.
A displayed login page is not proof of a completed human sign-in. 
