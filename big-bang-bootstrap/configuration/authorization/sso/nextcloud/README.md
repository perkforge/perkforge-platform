# Nextcloud SSO: disabled preparatory candidate

`ansible-playbook big-bang-bootstrap/configuration/authorization/sso/nextcloud/prepare.yaml`
is noncontacting by default and in check mode. Explicit `nextcloud_sso_render=true`
with external `nextcloud_sso_origin`, `nextcloud_sso_issuer` and fresh absolute
`nextcloud_sso_output` writes inert review files only. Existing files cause refusal;
interrupted output is preserved. No credentials are read, no client/user/role is
created and no existing app payload changes. The preparation entrypoint does not activate; the separate lifecycle requires operation-specific approval. The dedicated client is disabled, uses code/S256,
one exact explicitly selected callback, one own-client audience, basic subject scope and a
client-role mapper restricted to `nextcloud_roles`, and an ID-token-only full-name
claim. The name is a display label, never the immutable account identifier. It has no role grants, broad
membership mapper, implicit/password/service-account flow or cross-app claims.
The existing realm-admin coexistence allowlist remains unchanged: this lifecycle
uses only direct subject grants and does not add platform-admin group bindings.
Never import the client JSON as a realm or blindly PUT it over an existing client.

## Verified upstream behavior and pending decisions

Official [user_oidc v8.13.0 source](https://github.com/nextcloud/user_oidc/tree/58d557521b79f6650f7a87b2abab94b760fcf154)
declares Nextcloud 29–36 compatibility. The official built release is
[user_oidc-v8.13.0.tar.gz](https://github.com/nextcloud-releases/user_oidc/releases/download/v8.13.0/user_oidc-v8.13.0.tar.gz),
SHA256 `6f13fa0477144a6812d8648626c64cee91807d1d0b60ca41424543086b9e2775`.
Its release archive contains dependencies/signature metadata; source tarballs do
not substitute for it. App Git supplies a checksummed offline image-context
recipe; image build/publication and runtime installation are separate gates.

[LoginController](https://github.com/nextcloud/user_oidc/blob/v8.13.0/lib/Controller/LoginController.php)
checks audience/azp/nonce and restricts login by whitelisted claims before user
provisioning. Map immutable `sub`, never email/preferred_username. With
`auto_provision=false`, login looks up a local account by raw mapped subject;
that is NOT an approved safe pre-provisioning scheme. With auto provisioning,
`soft_auto_provision=false` refuses a foreign-backend conflict. The proposed bounded JIT mode below still requires separate activation approval.
The rendered provider is deliberately deny-all and has UNAPPROVED provisioning.
No username/email linking, user creation or account adoption occurs here.

[LocalIdService](https://github.com/nextcloud/user_oidc/blob/v8.13.0/lib/Service/LocalIdService.php)
computes `sha256(providerId + '_0_' + sub)` in unique-ID mode. It also transforms
OIDC group IDs. [ProvisioningService](https://github.com/nextcloud/user_oidc/blob/v8.13.0/lib/Service/ProvisioningService.php)
filters the raw group against the whitelist then transforms its ID. Consequently
an OIDC role/group `admin` does not mean membership of Nextcloud's native `admin`
group. `mapping-group-admin-for` grants group subadministration, not instance admin.
Do not turn unique IDs off to make admin work. Native admin remains local recovery
only until a reviewed exact provider/subject-to-native-admin mechanism handles
both grant and removal without changing recovery membership. No claim currently
grants native admin, including `/platform/admins`.

| Identity/claim | This candidate | Required activation decision |
|---|---|---|
| Existing local recovery admin | Retained unchanged | Verify separate working local login before each stage |
| Platform admin | No Nextcloud grant | Approve exact subject and native admin mapping/removal |
| Ordinary household subject | No enrollment/login | Review explicit own-client role, provisioning, non-admin tests |
| Missing/unknown/foreign role or audience | No grant; deny-all provider | Real signed-token/browser negative acceptance |
| Tenant automation | Existing scoped permissions | No realm/admin grants, arbitrary image/Secret access |

## Independent client lifecycle

`reconcile-client.yaml` defaults off and check mode contacts nothing. Future live
runs require `nextcloud_client_run=true`, operation X and exact approval
`nextcloud-client-X-v1`, verified recovery, external short-lived operator token,
existing client-secret file (0600), public CA, exact issuer and app origin.
No passwords/tokens/secrets are generated or rotated. Canonical drift and foreign
resources cause refusal, not automatic repair. Other applications are untouched.

- prepare creates only a missing disabled owned client, two noncomposite roles
  (`household`, `owner`) and their exact own-client scope. Partial preparation
  resumes without duplicate roles. Standard basic scope is independently checked.
- members accepts at most 20 external exact subject UUID/role records. It verifies
  existing users and direct/effective own-role equality, refuses inherited/unknown
  grants and changes only those own-client direct roles. It creates no users.
- activate requires native-ready and `own-client-role-jit-v1` approval, exact
  reviewed role recipients and zero group grants before enabling only this client.
- callback, with `nextcloud-client-callback-v1` approval and explicit pretty-route
  input, replaces only the sole same-origin `/index.php/apps/user_oidc/code` URI
  with the sole `/apps/user_oidc/code` URI. It also accepts an already-correct URI
  without writing. Unknown, foreign, multiple and wildcard URIs are refused. The
  entire client record is compared afterward, excluding only the intended redirect
  change. It tolerates only the known legacy missing name mapper/logout attribute
  so this correction can precede those separate upgrades; it does not add them.
- display-name, with `nextcloud-client-display-name-v1` approval, upgrades only an
  exact legacy two-mapper client by adding `nextcloud-display-name`. It emits `name`
  in the ID token only, not access tokens, userinfo or introspection. It changes no
  scopes, redirects, grants or users and is idempotent after the exact third mapper
  exists. Unknown/mismatched mappers still cause refusal. Select the already reviewed
  exact callback in the operator inputs; this operation never repairs callback drift.
- logout-redirect, with `nextcloud-client-logout-redirect-v1` approval, adds only
  the exact app origin plus `/` when the post-logout attribute is absent. Existing
  different/wildcard/multiple destinations are refused. It verifies the complete
  client record is otherwise unchanged; no session is logged out by this operation.
- inspect verifies ownership, settings, scopes, mappers and roles without mutation.
- rollback disables only this client, preserving users/roles/data and other apps.

Membership/activation requires `nextcloud_provisioning_approval=own-client-role-jit-v1`.
The candidate bounds JIT creation to explicit direct own-client role recipients;
activation compares actual role-user lists against the supplied reviewed roster.
Native configuration is `auto_provision=true`, `soft_auto_provision=false`, unique
immutable-sub IDs, no group provisioning and no bearer login/provisioning. This is
an explicit proposal requiring live approval, not open-ended household enrollment.
A role change to absent or owner demotion requires the exact subject in external
`nextcloud_native_revoked_subjects`: run native remove-subject FIRST. It disables
the account, removes native admin and revokes only Nextcloud tokens. Then change
this client's role; household resumption is independently verified. No global
Keycloak logout invalidates other app sessions. Direct grants deliberately avoid
platform-admin group mappings, so realm-admin coexistence remains unchanged.

App Git now implements independently gated prepare/apply/activate/rollback and
exact-subject admin/removal/resumption. Native admin requires an actual direct
owner grant read from the canonical owned client, plus hashed-account/backend
verification. Numeric provider identity and local recovery remain unchanged.
The initial provider renderer remains deny-all; it is review input, not deployment.

## Delivery, publication and live gates

App Git has a manually dispatched image-build REVIEW workflow, without registry
write permission. It creates an image archive/provenance metadata, not a published
runtime image. Review/scan and approve publication separately, resolve the actual
registry digest and feed it to unselected app/enrollment renderers. Enrollment's
renderer preserves the active policies and creates a candidate with only that
exact image and read-only public-CA/client-secret mounts. Its independently gated
input delivery consumes existing credentials and refuses rotation/adoption.
Neither renderer selects or applies a security boundary.

The official HTTP helper uses Nextcloud's private-address guard. Private Keycloak
needs `allow_local_remote_servers=true`; native apply requires separate
`oidc-private-issuer-egress-v1` approval. This expands the app HTTP address guard,
so exact tested egress is mandatory. Native apply/activate verify actual trusted
HTTPS discovery, issuer/endpoints, S256 and JWKS before enabling login. Shared
issuer-ingress /32 permits other virtual hosts at L3/L4; approve that exposure or
provide a dedicated endpoint. No TLS verification bypass or runtime app-store
permission is introduced.

Source fixture coverage does not establish live acceptance. Before relying on
SSO, independently test real signed-token/browser issuer/audience/azp/nonce/state
and callback denials, missing/unknown/foreign role denial, first-login conflict,
owner admin and household non-admin, grant removal, remember-me/app-password
revocation, client/provider rollback and unchanged other-app sessions. Record
numeric account/provider IDs, actual session limits and local recovery success.
No test here proves image execution/signature integrity, admission/CNI/NAT,
backup or household readiness. No live stage was performed by these PRs.

Keycloak role-member/group and scope endpoints follow the
[official Admin REST API](https://www.keycloak.org/docs-api/latest/rest-api/index.html).
Use `operator.example.yaml` only as an external input template; every run flag
and approval remains off/unapproved. Native routing can select only one exact
indexed or pretty callback path, and the app verifies its generated callback
against that selection before activation. Never register both as a convenience. The physical operator example selects
`/apps/user_oidc/code`, verified from the browser-facing redirect; the generic
indexed default is not evidence for this install. Keep client/native inputs equal
and rerun the browser verifier before activation.

## Confirmed people and retained recovery

Corey's existing Keycloak identity is the intended owner: preserve his existing
platform-admin authority and separately grant the dedicated Nextcloud client owner
role plus verified native Nextcloud admin. Resolve the existing immutable subject;
do not create a duplicate identity or link by username/email. Platform-admin group
membership alone is not evidence of native admin. Before relying on SSO, test the
actual browser account, native administration, removal/resumption and unchanged
platform access, with independent local recovery login before and after.

Jett is intended to become an ordinary household user, with no native admin or
platform authority from Nextcloud. Creation/enrollment/grants are deferred, so the
operator example keeps `nextcloud_subjects: []`. No account or credential is to be
created as part of recording this target. A later separately approved test must
prove ordinary access and denied admin operations. The current local admin stays
unchanged as recovery. Existing offline owner/household tests are synthetic and
are not live evidence for Corey or Jett.

The native provider must map its display name to `name` while retaining `sub` and
unique UID mapping. Existing accounts receive the readable name on their next SSO
login. Do not add broad profile/email scopes or rename/link an account to change its
label. Source changes do not apply the migration; both client and native stages
need their own explicit approval and verified recovery.

For legacy clients missing both additions, explicitly approve and run `display-name`
first, then `logout-redirect`. Only the named migration operations tolerate the absent
logout attribute; normal operations require the complete reviewed contract. Never
use `+`, `*` or multiple allowed logout destinations.

If correcting the known indexed-to-pretty physical callback, run the independently
approved `callback` operation first with `nextcloud_sso_callback_path=/apps/user_oidc/code`,
then the separately approved name/logout operations as needed. No operation selects
or repairs arbitrary routing; verify the actual browser-facing callback in app Git.
