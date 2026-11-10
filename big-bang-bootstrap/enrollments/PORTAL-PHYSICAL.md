# Physical Portal enrollment release gates

Portal's first implementation targeted the retired VM lab. Restoring the small,
stateless, admin-only SSO baseline is separate from the later AI-driven UI work.
Do not treat the historical app/enrollment `v1.0.0` evidence as physical-compatible.
The existing application image `v0.3.0` alone does not supply physical configuration.

No new runnable source or parent is supplied here: compatible physical application
and enrollment release pins are not selected here yet. Invented future tags or a paused source
pointing at an incompatible old release would provide misleading deployment input.
All existing enrollment wiring and platform cluster roots remain unchanged.

## Independent source contract after review and release

- Use a distinct GitRepository **and** parent Kustomization named
  `portal-enrollments` in `flux-system`; source URL remains the platform-tenants
  repository. The parent must reference that distinct source, never
  `tenant-enrollments`, and use the existing `tenant-enrollment-admin` service
  account. Keep both suspended and retain `prune: false` until explicit activation.
- Select a verified, published immutable enrollment tag and its dedicated physical
  Portal root. The enrollment release must itself select the verified compatible
  Portal app configuration release. Confirm exact paths from those releases before
  authoring the additive source/parent pair; do not substitute a floating branch.
- The reviewed Portal foundation defines a `portal-enrollment` RoleBinding for
  enrollment-account GitRepository/Kustomization CRUD in `tenant-portal-config`.
  This is source-defined authority, not an existing live grant: apply the foundation
  only after approval. Reuse that scope; do not widen platform authority or
  repurpose the Nextcloud reconciler.
- Preserve the live selection reported at preparation: cluster-config `v0.34.3`,
  `./big-bang-bootstrap/clusters/local-velero`; tenant-enrollments `v1.5.4`,
  `./clusters/local-nextcloud`; Nextcloud app `v1.1.3`. Recheck actual selections
  before deployment. The old `enrollments/local` Portal specimen also uses the
  name `tenant-enrollments`; applying it would collide with Nextcloud. Do not apply
  or modify it to restore Portal. Existing `v1.0.0` evidence is retained as history.

Before activation, review the cross-repository physical host/issuer, app release,
admin-only role mapping, namespace/network isolation, public CA trust, dedicated
TLS leaf and narrowly scoped runtime-secret delivery contracts. The physical URL
is `https://portal.perkforge.home.arpa`; the issuer is
`https://keycloak.perkforge.home.arpa/auth/realms/perkforge`. Credential creation,
OpenBao/ESO delivery, enrollment foundation creation, DNS, source selection and
resume each require their appropriate action-specific approval. No live state,
credentials or physical addresses are included here.

Use the default-off [Portal-only DNS maintenance scope](../../infrastructure/ansible/DNS-MAINTENANCE.md)
only in a separately approved shared-DNS safe window. Preserve the active
Toshiba-to-Nextcloud transfer. Recheck capacity before deployment: the small
25m/64Mi app request is not proof of schedulability when worker CPU reservations
are near full. Real HTTPS, SSO/admin and non-admin denial acceptance, trust and
recovery checks remain required; source tests do not establish live success.
