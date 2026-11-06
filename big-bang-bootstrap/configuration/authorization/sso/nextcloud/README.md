# Nextcloud SSO: disabled preparatory candidate

`ansible-playbook big-bang-bootstrap/configuration/authorization/sso/nextcloud/prepare.yaml`
is noncontacting by default and in check mode. Explicit `nextcloud_sso_render=true`
with external `nextcloud_sso_origin`, `nextcloud_sso_issuer` and fresh absolute
`nextcloud_sso_output` writes inert review files only. Existing files cause refusal;
interrupted output is preserved. No credentials are read, no client/user/role is
created and no existing app payload changes. There is deliberately no activation
operation in this candidate. The dedicated client is disabled, uses code/S256,
exact index.php callback, one own-client audience, basic subject scope and a
client-role mapper restricted to `nextcloud_roles`. It has no role grants, broad
membership mapper, implicit/password/service-account flow or cross-app claims.
The existing realm-admin coexistence allowlist remains unchanged until an actual
Nextcloud client/role lifecycle and its exact UUID checks are reviewed together.
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
`soft_auto_provision=false` refuses a foreign-backend conflict. Neither mode is
authorized for activation: choose/review a bounded enrollment mechanism first.
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

## Coordinated implementation and acceptance gates

1. Review app image recipe, build and publish separately, record immutable image
   digest and integrity evidence; no runtime app-store download. Do not select it.
2. Enrollment owns exact image/ConfigMap/Secret/admission changes and reviewed
   /32 issuer egress/public CA delivery. Its unselected renderer changes no live
   boundary. Test actual CNI/NAT and shared-ingress reachability limitations.
3. Implement client/native inspect/prepare/apply/activate/rollback with exact
   issuer/client/audience/callback/provider identity, foreign-resource conflict
   refusal, private external file inputs, interrupted-run recovery and idempotence.
   Extend realm-admin coexistence only with exact approved client/role UUIDs.
   This preparation PR does NOT yet implement these mutation stages.
4. Approve provisioning and native admin versus household mapping. Enforce
   code/S256, keep issuer/azp/audience/nonce verification and disable bearer/API
   token provisioning. Verify local login and wrong identity/CA refusals first.
5. Perform separately authorized signed-token/browser tests: intended owner admin,
   ordinary household non-admin, unknown/missing roles, foreign issuer/audience,
   callback/state/nonce errors, account conflict and unchanged other app access.
6. Prove own-client role removal denies a NEW login; existing Nextcloud sessions,
   remember-me and app passwords may outlive a Keycloak grant/client change.
   Measure actual session/revocation limits, implement bounded revocation and test
   back-channel logout before claiming immediate offboarding. No session limit is
   inferred from token expiry. Recheck provider/account IDs and synthetic data.
7. Roll back by independently disabling this client and native login, revoking
   only affected sessions, then removing reviewed delivery/egress after quiescence.
   Keep the numeric provider ID, user identity mappings, local recovery, PVCs,
   database, files, image/schema compatibility and other clients. Do not delete
   users/providers/groups, rotate shared secrets or restore old schemas as rollback.

Offline tests exercise real Ansible preparation and conflict/check behavior plus
artifact/selection contracts. They do not validate live native identity/session
behavior, admission, network isolation, image execution, signature verification,
backup or household readiness. Remaining gates are intentional blockers to
activation, not successful acceptance claims.
