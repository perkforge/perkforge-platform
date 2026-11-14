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

The selected configuration uses the immutable image recorded by the published
enrollment/configuration chain in `release-evidence.json`, built and published
once by its normal release pipeline. Verify fresh Flux generations, Portal rollout,
trusted HTTPS, unauthenticated API/BFF denial and the native OIDC login redirect.
A displayed login page is not proof of a completed human sign-in. 

## Verified final current-state rollout (2026-11-14)

The selected durable logging composition reached Ready/Healthy at platform commit
`56dfa91962b40088e6339f746fbdad835134b233`, with enrollment v2.5.3
(`21c333a42816ae784dd923ddcb11cc19341a3940`), configuration v2.3.4
(`3cf1c5ac07f9ce06f68fbe507d029269501139ca`) and Portal v0.7.1's
published `sha256:1aff18f27bb6a2354661ddf89664b686796a01387658d6f0ed134114786b02a8`.
The full 104-object root comparison changed only the enrollment reference;
logging cursor storage, Viewer boundaries and notification composition were preserved.

Portal's native upgrade succeeded at 18:11:21 UTC (Helm revision 10), with one
available replica and matching desired/observed Deployment generation. Trusted-TLS
checks verified the login-only public shell, all three actual compiled assets denied
for anonymous GET/HEAD with `no-store`, encoded alias and API denials, correct
Keycloak callback/PKCE initiation and revoked guest-session denial. Mounted inventory
remained available, and the request-preview feature remained disabled. This is not
fresh owner-browser login or complete tenant-human acceptance evidence.

### Known transition-order limitation

Applying the new exact image contract before all child values converge can reject
an in-flight render that still uses the old image. During this rollout, failed Helm
revision 9 selected the new chart but its stored Deployment manifest still contained
the old v0.6.1 image. The new contract correctly rejected it. This was directly
verified from the failed manifest; it is not evidence of an admission informer race.

Before retrying, verify the exact source/configuration revisions, every ordered
`valuesFrom` input, the generated desired Deployment image and the live contract.
Render the published chart against those current inputs and require a server-side
admission dry-run to pass with unchanged identity settings. Once this was true,
normal supported Flux `resetAt`/`requestedAt` reconciliation completed the same
approved upgrade; no image-policy relaxation or direct Deployment patch was used.
Refresh normal child/parent health after recovery. Do not suppress failure routes,
force health, weaken the allowlist or assume a failed old render is now acceptable.
