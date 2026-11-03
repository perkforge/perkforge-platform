# Independent application SSO stages

One coordinated source change; three independently reviewed live batches in order
Headlamp, Rancher, OpenBao. Headlamp owner acceptance is recorded below;
Rancher/OpenBao remain gated. `prepare.yaml` is a
no-contact nonsecret renderer. The four `reconcile-*.yaml` entrypoints default to
no contact, including check mode. They use built-in Ansible modules and existing
operator credentials only. No play installs software, deploys a HelmRelease, restarts
RKE2, imports a realm, creates a person or resets any password/factor.

## Current Headlamp owner acceptance

Published v0.15.2 passed all post-merge checks and is selected by Flux with the
Headlamp SSO stage. The existing client/secret were reused. The effective chart
PKCE flag is present; exact API/workload trust checks passed before creating the
single owned platform-admin cluster binding. Only the Headlamp app role was
mapped to the admin group and its client enabled. Native/client repeats made
zero changes; inspect-only post-acceptance checks also made zero changes.

The owner confirms named-account login and visibility of nodes/pods. Automation
verified trusted HTTPS/discovery and the expected S256 redirect, without human
credentials or token capture. Synthetic native authorization checks are separate:
admin allowed, ungranted group and runtime-SA cluster Secret access denied.
A separately approved one-user real denial drill passed: no groups/admin roles,
actual Headlamp OIDC/S256 and test-only TOTP, exact UID authenticated, nodes/pods
403 through Headlamp and direct API, Secret-list access reviews denied. Exact
UID/session cleanup and generated credential removal passed; realm/flow/existing
admin grants unchanged. Corey was never targeted. This is bounded real denial
acceptance, not proof of every role/verb/resource. Fresh owner MFA challenge
timing was not independently observed.

The test ID token still authenticated just after user deletion, with resource
reads still denied. Its 300-second lifetime ended nominally at
2026-11-03T13:08:12Z; expiry was not independently awaited after local token
removal. Revoking sessions/deleting a user is not instant offline JWT revocation.

The chart requires `upstream.config.oidc.usePKCE: true` to emit the existing
Secret reference; merely storing OIDC_USE_PKCE does not configure the application.
Pinned-render and stateful fixtures enforce the exact six OIDC arguments and
reject missing/extra/duplicate flags, literal credentials and trust/config drift.
API maintenance was unchanged by this app correction: retain the v0.15.1 host
transaction/rollback source. No additional restart or secret rotation occurred.
Independent certificate API admin and protected Keycloak recovery authentication
remain verified; no outage/restore/forced rollback acceptance is implied.
Rancher/OpenBao require their own reviewed live batches.

## Environment and credential delivery

Copy `operator.example.yaml` to a private location outside the repository. Review
all origins, realm, exact callback paths, distinct client IDs, cluster UID/context,
canonical parent/leaf group UUIDs, OpenBao cluster ID/accessor and trusted public CA bundle.
Place existing independently authorized recovery credentials and three distinct
client secrets in owned regular mode-0600 files; no symlinks. These plays do not
mint, print, rotate or commit client secrets. Supplying/generating new credentials
and live application are separate approvals. Never put credential values into
`-e`, shell history, tracked vars, logs or MR/CI artifacts. Retain the designated
private files through acceptance/rollback; final custody/removal is operator owned.

The same client-secret file is passed to the shared Keycloak adapter and the
corresponding native adapter. Keycloak inspection compares the existing server
credential privately; it never calls a secret-generation endpoint. Headlamp's
separate `deliver` operation creates only its dedicated immutable Secret and
public ConfigMap through private stdin. Repeats compare exactly; changed material
or unowned objects stop instead of rotation/adoption. A public bundle must contain
certificates and no private key. Rancher stores the supplied secret using its
existing provider machinery; public trust must already be mounted in the server's
system CA directory. Its `certificate` field is not a CA-only field; unexpected client-certificate or
private-key settings refuse instead of adopting another credential. OpenBao sends
the same supplied secret only for an initially empty OIDC configuration; existing
public configuration must already agree. The SSO Rancher adapter also omits `clientSecret` on every update to an already
configured provider, including public-setting drift and re-enable; it never
rotates the existing credential implicitly. Credential rotation is not hidden in
a repeat or drift repair.

No secret is rendered. Ansible protects credential and object contents with
`no_log`, redirects are disabled for URI operations, and native command inputs
containing credentials use stdin. Ansible local/remote temp paths and caches must
remain private. Never enable debug/diff or retain failed task payload dumps.

## Approval and sequencing

Set exactly the entrypoint's `*_run` flag and explicit scope for one reviewed
operation; keep all other flags false. `sso_apps.*.apply` remains false because
those are review-renderer flags, not live switches. No orchestrator advances stages.

| Entrypoint | Operations | Exact scope input |
|---|---|---|
| `reconcile-client.yaml` | `prepare`, `inspect`, `activate`, `rollback` | `<app>-client-<operation>-v1` in `sso_client_reviewed_scope` |
| `reconcile-headlamp.yaml` | `deliver` | `headlamp-sso-delivery-v1` |
| `reconcile-headlamp.yaml` | `inspect`, `activate`, `rollback` | `headlamp-sso-v1` |
| `reconcile-rancher.yaml` | `inspect`, `apply`, `rollback` | `rancher-sso-v1` |
| `reconcile-openbao.yaml` | `prepare-data` | `openbao-data-v1` |
| `reconcile-openbao.yaml` | `prepare` | `openbao-sso-prepare-v1` |
| `reconcile-openbao.yaml` | `inspect`, `apply`, `rollback` | `openbao-sso-v1` |

First render/review the four nonsecret payloads in a fresh private output directory.
For each app, verify independent recovery without authenticating as the owner.
Then obtain approval for the exact private inputs and intended writes. Run the
shared client `prepare`: a disabled owned client, two exact bounded mappers, one
noncomposite own-client role and exact scope mapping. No human group role is added
by preparation. Wrong/duplicate/unowned clients, mapper/scope drift, credential
mismatch and unexpected roles stop. A partial disabled preparation can be inspected
and resumed; never delete/recreate it merely because a request was uncertain.

For Headlamp, separately approve `deliver`, review the generated `gitops_values`
overlay and promote it through normal GitOps review. Do not manually patch the
Deployment. API OIDC trust is a provisioning prerequisite, not an application
side effect; absent trust requires separate approved RKE2 work and restart/health
acceptance. The rendered `provisioning_fragment` is an append-only RKE2 candidate
parameterized from the same reviewed environment/issuer/client/CA-path inputs;
it is not installed by an app play, does not replace base RKE2 config or inject
hosts aliases, and must not duplicate RKE2's automatic CA mount. The native `activate` refuses missing/mismatched API flags, azp/audience,
issuer, algorithm/claims/prefixes/CA mount, workload version/configuration/trust or
credential contents before creating the single PA cluster-admin binding.

### Headlamp source selection and release gate

The optional `clusters/local-headlamp-sso` root retains every selected package in
`local-keycloak` and replaces only the final `values-app-stage` Headlamp values
with this adapter's nonsecret `gitops_values` contract. Earlier roots retain their
token-mode behavior. This local target uses the versioned Secret/CA object names;
issuer, callback, client ID and client secret remain external delivery inputs.
Other environments must review their own target selection against rendered inputs.

Publish an immutable release **containing this stage**, verify its tag/commit and
review the tag/path promotion together. Publishing #139 or selecting a release
that lacks this root cannot enable the overlay. The observed cluster remains
v0.14.0/local-keycloak; neither adding this directory nor merging it changes Flux.
Never repin to main/a feature branch, patch Flux-owned values or repeat bootstrap.

Before selecting `./big-bang-bootstrap/clusters/local-headlamp-sso`, obtain a
separate live-batch approval: independent certificate/SSH recovery; disabled
Keycloak client and protected secret custody; immutable credential/public-CA
delivery; exact API issuer/audience/required azp/claim prefixes/RS256/CA configuration;
and a controlled RKE2 restart with API recovery. The lab has one control-plane,
so that restart temporarily interrupts API/Flux control operations. Only then
promote the approved release/stage and verify Headlamp workload readiness before
native PA binding and client/group activation. No Rancher/OpenBao activation is
implied. Operator fresh-MFA access and positive/negative native authorization,
no-change repeats and independent recovery remain required live acceptance.

For rollback, remove only owned native Headlamp authority and disable/unmap only
its client, then restore the previously approved immutable GitOps tag/path.
Preserve existing realm administration, other apps, independent certificate/SSH
recovery and credential/CA objects until references are removed. Restore only the
new API configuration over SSH with an explicitly approved restart if needed;
rolling back app values alone does not remove API OIDC flags or revoke all JWTs.

For Rancher, `apply` requires the supported v2.15.2 Generic OIDC shape, exact cluster,
public system-trust material/mount, local recovery, no competing external provider,
owned/empty Generic OIDC settings and exact PA-only GlobalRoleBinding. Native
Keycloak OIDC is a different implementation; no provider migration is automatic.
PKCE uses the actual `pkceMethod: S256` field. No Keycloak user-directory query grant
is needed for this Generic OIDC configuration.

The pinned Rancher 2.15.2 chart mounts `tls-ca-additional` at
`/etc/pki/trust/anchors/ca-additional.pem` and `/etc/rancher/ssl/ca-additional.pem`,
both read-only with `subPath: ca-additional.pem` and Secret mode 0400. The native
guard verifies those exact mounts and compares the public CA contents; it does
not infer a path from another distribution or change the Deployment to satisfy
the guard. A pinned-chart render cross-checks the stateful fixture. This source
correction does not activate the provider or prove a real OIDC login/recovery.

For installed OpenBao 2.7.2, a separately approved `prepare` can enable only a missing OIDC method
with an ownership description and bounded lease defaults. It returns only the
nonsecret accessor for review; no client config, role, policy or identity is added.
Repeat preparation accepts only that owned mount and verifies non-target methods
unchanged. Existing unrelated mounts require migration review, not adoption.
Record the accessor in external inputs before the next batch. `apply` requires the exact healthy cluster/accessor and an existing OIDC
mount; it never enables mounts itself or touches Kubernetes/machine auth, retention,
unseal/recovery or secret engines. It creates only versioned PA policy/role and an
initial matching public OIDC config with explicit code/query flow (native PKCE),
verbose token logging disabled and policy-claim templating disabled. Existing different role/policy/configuration
stops; the legacy broader platform/tenant policies are not adopted. Any unrelated login
role on this accessor also blocks activation; re-enabling the same issuer/client
must not revive a legacy broad role. No automatic role migration or deletion. Existing `platform/` and `tenants/` mounts must be KV-v2; missing/wrong data
engines stop before policy writes and require separate provisioning approval.
The default-off `prepare-data` operation fills that prerequisite only after explicit
`openbao-data-v1` approval: create missing `platform/` and `tenants/` KV-v2 engines,
with a versioned ownership description and otherwise upstream defaults. It requires
the verified healthy cluster, public CA and existing protected operator credential,
but no OIDC accessor/client secret. It never creates values, edits retention, enables
auth or grants policies. Existing engines must match type/version/ownership; foreign
engines stop before any creation. Partial creation resumes without replacing the
first engine; repeat must report changed=0. Other engine representations compare
equal before/after. There is deliberately no engine-delete rollback: disabling an
engine can destroy data. Leave engines intact during SSO rollback and request
separate reviewed data cleanup only if needed. See the [2.7.x mount API](https://openbao.org/docs/api/system/mounts/).
No default login role or default token policy, no tenant values or auth/policy
self-grant.
Role `bound_claims` uses the bounded groups claim; `groups_claim` is deliberately
absent so it does not create external group aliases. Existing aliases on this
accessor are checked for entity/group policy inheritance; ambiguity requires a
separate migration decision, never automatic entity cleanup or privilege removal.

After the native stage is ready, separately approve shared client `activate`.
`sso_client_native_ready` records operator-reviewed native readiness, not an
automated personal login assertion. Only then does it add the own-client role to
exact `/platform/admins` and enable that app. Canonical client lookup is by UUID;
brief list responses are not assumed complete. The exact owned parent must remain
unprivileged, defaults empty and the admin leaf without nested inheritors. Standard
basic/profile/email scope definitions are checked against nonsecret 26.8.1 mapper
shapes; unexpected group/role disclosure refuses before client creation. Actual
assigned default/optional scope UUIDs are checked independently. `basic` is retained
for access-token subject/auth-time; create-time userinfo normalization is explicit.
No authentication-flow override may bypass the realm browser MFA contract. Enable/disable PUT contains only
`clientId` and `enabled`, never masked or server-managed credential fields. Repeats
must report changed=0 and independent readback must preserve all other mappings.

## Coexistence with realm administration

The realm-admin play's default still rejects every app mapping. After an approved
SSO stage, supply `perkforge_admin_expected_sso_clients` in reviewed external vars:
keys are only headlamp/rancher/openbao; each value has `client_name`, `client_id`
(canonical UUID) and `role_id` (canonical UUID). This permits recognition only,
not an app grant. It verifies the owned enabled client, sole noncomposite canonical
role, empty composite edges and exact direct/aggregate binding IDs. Unexpected,
unowned or expanded roles still refuse. Update this contract only after independent
readback of actual approved state; never infer trust from live names or labels alone.
After app rollback removes the role, remove only that entry from the reviewed
expected-state input. Re-run realm administration with changed=0; its root grant
and 22-role expansion must remain unchanged throughout. No master delegation.

## Live acceptance and independent rollback

Offline fixtures establish API request/state-machine behavior, not actual product
token enforcement or UI usability. Live acceptance remains gated. Use the owner's
manual fresh MFA login for PA UI checks; never automate their password, factor or
session. Record user-reported UI evidence separately from API authorization checks.
No disposable users, tenants, values or production mutations are authorized merely
by this source. If existing approved negative identities/test data are unavailable,
request that bounded test batch separately; do not borrow another person's account.

For each app verify PA positive and no-group/tenant/engineer negative, correct
issuer/audience/azp/signature/expiry, client-specific claim disclosure, callback
state/nonce/PKCE and rejection of another client's token/code through the native
flow. A UI menu or a mocked server accepting a policy is not authorization proof.
For Kubernetes use token-specific SelfSubjectAccessReview decisions and reviewed
read-only API requests, including wrong-audience rejection. Do not create workloads
or read real Secrets merely to prove write or secret authority. Rancher requires
native protected API/group authorization and re-login after membership removal.
OpenBao requires native capability checks plus separately approved disposable
platform/tenant test paths: PA denied tenant values, no policy/auth self-grant,
no default-policy inheritance, own-tenant versus cross-tenant and deletion/destroy
boundaries. Initial payloads grant PA only; tenant/engineer/PV roles stay deferred.

Test wrong role/group and stale sessions as well as successful admission. Measure
native enforcement after removal: old issued ID/access tokens, refresh tokens,
Rancher sessions and OpenBao tokens are not universally revoked by disabling a
Keycloak client. Record observed expiry/revocation limits; never promise universal
instant invalidation. Keep local recovery available and confirm it after each stage.

Rollback one app only: remove the native grant first, then run that client's
`rollback`. Headlamp deletes only its exact owned binding with UID/resource-version
preconditions; leaves credential/CA objects for GitOps references and recovery.
Rancher disables only its owned Generic OIDC provider and deletes only its exact
owned group binding with preconditions, preserving local auth. OpenBao deletes only
the exact versioned human role/policy, retaining OIDC config, machine auth, mounts
and independent operator recovery. Shared client rollback disables only that client
and removes only its direct app-role mapping, preserving the realm-admin grant and
other applications. Poll native protected authorization until denial, then repeat
rollback and verify changed=0. Never remove another app's client or global user
sessions. Flux rollback of Headlamp values is a separately reviewed source change;
no play restarts it. Unexpected object identity/drift stops for review.

## Offline checks

`RUN_PLATFORM_SSO_TESTS=1` enables the new fixture suites. Synthetic HTTPS suites
also require `RUN_PLATFORM_CONFIG_TESTS=1`. `.github/workflows/gitops-selection.yml`
runs them in a separate offline `platform-sso` job, with KUBECONFIG=/dev/null and
no service credentials. The existing long selection job retains all existing core
regressions and the explicit realm-admin/app coexistence test. Fixtures cover
apply/repeat/inspection, interrupted preparation/delivery/binding/config writes,
independent rollback, private-input handling, foreign identities/roles/providers,
CA/UID/issuer mismatch and inherited OpenBao policy refusal. Actual live acceptance
and recovery outcomes must be added only after separately approved execution.

Transport trust follows [the TLS lifecycle contract](../../../../docs/platform/tls.md).
Client-to-ingress TLS checks do not close the documented internal HTTP/database
transport gaps or establish production compliance. Before any API-server OIDC
change, verify issuer DNS/trust from the static API-server environment without
personal hosts aliases, direct recovery and the approved restart/rollback window.

Pinned compatibility references:

- [Keycloak 26.8.1 client-role mapper](https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/mappers/UserClientRoleMappingMapper.java).
- [Keycloak create-time mapper normalization](https://github.com/keycloak/keycloak/blob/26.8.1/server-spi-private/src/main/java/org/keycloak/migration/migrators/MigrationUtils.java).
- [Rancher 2.15.2 OIDC configuration fields](https://github.com/rancher/rancher/blob/v2.15.2/pkg/apis/management.cattle.io/v3/authn_types.go).
- [Rancher certificate/system-root handling](https://github.com/rancher/rancher/blob/v2.15.2/pkg/auth/providers/oidc/oidc_client.go).
- [OpenBao 2.7.2 native code-flow PKCE](https://github.com/openbao/openbao/blob/v2.7.2/internal/builtin/credential/jwt/path_oidc.go).

## Headlamp activation prerequisites — focused maintenance and routing gates

Keep the release PR on hold until it includes both entrypoints below. Verify the
new immutable release's exact contents/checks; then request approval for the live
batch, not just publication. Current preflight found trusted issuer discovery and
SSH available, but sudo required a local password and Headlamp had no TLS/Ingress.
Nothing was activated by that inspection.

1. Owner runs the released [API maintenance procedure](../../../../infrastructure/ansible/API-OIDC.md)
   locally with `--ask-become-pass`, initially `inspect` only after inspection
   approval. Review its base hash, exact install/cluster identity and independent
   certificate/SSH recovery before approving apply/restart. No passwordless sudo,
   installation rerun, `/etc/hosts` mount, new credential or worker change.
2. Reuse `configuration/ansible/platform-tls.yaml` with only
   `platform_tls_applications: [headlamp]` and the existing reviewed leaf/key/public
   root bundle. Explicit TLS-delivery approval creates `headlamp/headlamp-local-tls`
   and the existing public `headlamp/identity-ca` contract; no issuance or global
   trust change. Do not run the PKI issuance play again. Validate bundle ownership,
   hostname, lifetime and current public fingerprint first.
3. Separately approve `reconcile-headlamp-routing.yaml` with
   `headlamp_route_run=true`, operation `apply`, scope `headlamp-https-route-v1`,
   recovery verification, exact target kubeconfig/context/cluster UID, environment
   HTTPS origin, public CA/fingerprint, and published `config_tag` plus nonsecret
   `config_release_evidence`. It pins a clean matching checkout, emits only the
   TLS certificate/type from kubectl, validates hostname/chain and backend
   port, and creates only the missing authored `headlamp-identity` Ingress with
   ownership label. It verifies trusted HTTPS; failed acceptance leaves the owned
   route for inspection/retry. No shared routing kustomization, Keycloak route,
   NetworkPolicy, Secret, RBAC or Deployment mutation. `inspect` is read-only and
   requires the route already present; default/check mode makes no API calls.
   Kubernetes Secret GET retrieves the full object inside kubectl; its private key
   never leaves that process, enters Ansible output or gets copied by this gate.
4. Prepare the disabled Headlamp client and versioned credential/CA objects through
   the existing separate gates. Keep its issuer/client consistent with host inputs.
   Approve API maintenance apply/restart and verify recovery before promoting the
   released `local-headlamp-sso` stage. Verify native readiness before its binding,
   exact expected-client contract and client/group enablement. Other app gates stay
   off. Complete fresh owner MFA, positive/negative native authorization, independent
   recovery and no-change repeats; fixtures are not live acceptance.

Routing rollback uses operation `rollback` with the same exact target/origin and
published source: only the owned matching Ingress is deleted with UID/resourceVersion
preconditions, never a blind retry. It preserves TLS/public-CA objects and every
other route. Native/client/GitOps rollback precedes removal of callback routing;
API rollback is the separate owner-local maintenance operation. Neither rollback
silently removes existing certificates, signing keys, shared trust or recovery.
Source tests cover routing isolation, missing/mismatched trust, partial creation,
repeat and concurrent-delete refusal. No live TLS delivery, privileged write,
restart, SSO or owner-browser acceptance has occurred.

## Remaining Rancher and OpenBao activation batches

The adapters and shared Keycloak client lifecycle were already merged in #139;
this change does not duplicate them or require a Rancher Helm selection overlay.
Both applications remain on their existing deployment and independently gated
native configuration path. Publishing/merging this code activates neither.

1. **Rancher:** review exact environment/cluster/provider image and mounted issuer
   CA, existing local recovery, dedicated confidential client/secret and current
   provider state. Approve disabled-client preparation separately from native
   `apply`/PA global binding and client activation. Stop on foreign provider or
   secret drift. Prove owner fresh-MFA login, intended global authority, rejection
   outside the approved group and no-change repeats. Disable only the owned provider
   and remove only the owned binding before rolling back that client's activation;
   recheck local recovery and other apps. Existing native fixtures cover these
   configuration transactions, not real browser login or live RBAC acceptance.
2. **OpenBao:** inspect exact initialized/unsealed cluster and independent operator
   recovery. If the two logical engines are absent, approve `prepare-data` alone;
   review persistent storage/backup implications before enabling empty engines.
   Separately approve owned OIDC-mount `prepare`, record its public accessor, then
   approve versioned human policy/role and client activation. No reinitialization,
   unseal changes, root-token browser login or machine-auth migration. Prove platform
   values CRUD with a separately approved disposable path, tenant-name LIST, tenant
   value and policy/auth self-grant denial; no real tenant values are needed. Measure
   old-token/session behavior. Roll back only the owned human role/policy and client
   grant; preserve engines, machine auth, recovery and other apps.
3. Finish each app's health/resource report and recovery check before the next.
   Live acceptance, disposable test values and cleanup each need exact approval;
   fixture passes are not deployed evidence. No automatic orchestration advances
   these stages, and Headlamp correction/acceptance remains independently owned.
