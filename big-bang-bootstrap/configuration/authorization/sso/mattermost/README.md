# Mattermost Keycloak SSO preparation

These entrypoints belong to the same Mattermost MR. They do not deploy or select
an app root. Default and check modes contact no APIs and read no private files.
All actual client creation, credential transmission, protected delivery and client
activation require separate explicit approval. Run from reviewed released source.

## One consistent identity contract

Use the same approved `mattermost_sso_origin` and `mattermost_sso_issuer` for
preparation and client reconciliation. The origin is the exact HTTPS app URL,
without a path or trailing slash. The issuer is the exact trusted Keycloak realm
URL, including `/auth` only when that installation uses it. Do not guess or accept
redirects. Public app DNS, ingress/TLS and Mattermost SiteURL must match this origin.

`prepare.yaml` writes a new owner-only directory containing a disabled confidential
`mattermost` client and public values overlay. Enable only `mattermost_sso_render`
to render; supply a fresh absolute output path and non-placeholder HTTPS endpoints.
The callback is exactly `<origin>/signup/openid/complete`. The Keycloak client
permits authorization code only, has no service account/password/implicit grants,
no full scopes, roles, group mapper or wildcard callback. Approved basic/profile/
email scope contracts are checked using the shared project verifier.

Other OIDC uses the app's native `MM_OPENIDSETTINGS` environment. The Big Bang
GitLab SSO shortcut remains off, signup closed and the app disabled/suspended.
An existing protected `mattermost-oidc-client` Secret supplies `client-secret`;
`mattermost-identity-ca` supplies only public `ca.crt`. No credential is placed in
rendered values. The CA mount must be present in the operator-generated workload;
source rendering alone does not establish actual TLS trust.

## Separately approved execution sequence

1. Decide the exact pinned edition/license and native OIDC support, app origin,
   issuer/CA, external database/storage, restricted route and recovery access.
   No image/license bypass or production entitlement is implied.
2. Prepare public payloads; review their values alongside the app candidate in the
   same release. Do not enable a second independent release path.
3. `reconcile-client.yaml` operation `prepare` creates only the disabled owned
   client using an already approved, privately held client secret. It refuses
   foreign/drifted clients and secret mismatches rather than adopting or rotating.
   Token/secret files must be operator-owned 0600 under 0700 directories; TLS CA
   validation, no redirects, no proxy/netrc and log redaction remain required.
4. `deliver-inputs.yaml` creates only the immutable Secret and public CA ConfigMap
   in the exact pre-existing `mattermost` namespace. Approval is
   `mattermost-sso-input-delivery-v1`; actual API, cluster UID, namespace UID and CA
   checksum must match. It checks both collisions and server dry-runs before
   creation, preserves matching repeats, and resumes a partial create without
   rotation. It creates no namespace, grant, registry input, app or deployment.
5. After approved app deployment, verify independent local recovery, exact edition,
   CA/hostname trust and explicit native account linking with signup closed.
   `activate` is separately gated by `mattermost_native_ready`,
   `mattermost_edition_verified` and `mattermost_linking_verified`; those are
   operator attestations, not automated proof. Approval for each client operation
   is `mattermost-client-<operation>-v1`, with `mattermost_client_run: true`.
6. Test a fresh Keycloak MFA login and native tenant/team/channel denial. This code
   does not provision/link Mattermost users, grant System Admin, synchronize groups
   or remove memberships. Those must be reviewed and accepted before human access.

`inspect` reads only the exact client/public scope configuration; `rollback`
disables only that owned client, preserving credentials and users. Disabling the
client is not session revocation or native account/membership removal. Local admin
recovery and explicit offboarding acceptance remain required.

PKCE is not imposed on the confidential client without proving that the exact
pinned Mattermost implementation sends it. Do not turn on a guessed requirement
that breaks login; native authorization-code/state/nonce behavior still needs
acceptance. Unit tests exercise real Ansible against disposable HTTPS/API and CLI
fixtures, not live Keycloak or the Mattermost binary.
