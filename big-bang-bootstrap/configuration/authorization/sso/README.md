# Independent application SSO stages

One coordinated source change; three independently reviewed live batches in order
Headlamp, Rancher, OpenBao. Headlamp owner acceptance is recorded below;
Rancher acceptance and OpenBao configuration are recorded below; OpenBao browser/data acceptance remains gated. `prepare.yaml` is a
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

## Current Rancher configuration and owner report

The approved #150 merged executor configured only Generic OIDC, the bounded
Rancher client role and the PA-only global-admin binding. Native/client repeats
passed 45/68 ok with zero changes. Local recovery and other providers were
preserved; Flux stayed v0.15.2 without restart. The owner reports initial local
setup followed by named-account login with local-cluster and pod visibility. GET-only first-login/server-URL settings
agree with completed setup. This does not verify effective per-user admin powers,
fresh owner factor prompts or rollback. The separately approved real no-grant
Rancher denial and exact cleanup passed below. No callback change was
made: the standard callback routes correctly with UI state.

### Rancher bounded denial acceptance — executed

**Observed 2026-11-03 17:06 UTC:** one owned no-group/no-admin-role account
completed password/TOTP and native S256 authentication, then received the exact
Rancher access-policy denial. No native session was issued. Run: 83 ok / 7 changed /
0 failed. Exact UID/session cleanup, UID404/empty-name lookup, rejected test bearer
and refresh, and generated credential-file removal passed. Realm/flow, human
membership/credential IDs, native provider/admin binding and post-test cluster
baseline were unchanged. This is a bounded live result, separate from the offline
fixtures. Corey's credentials/session were not used and his account was not changed.

The published default-off [Ansible runner](../rancher-denial-acceptance.yaml) reuses
owned disposable-account creation, test-only TOTP enrollment and exact UID cleanup.
Its [native verifier](../files/verify-rancher-denial.py) preserves Rancher's PKCE
cookie and requires the pinned v2.15.2 `Unauthorized` / `unauthorized` response
(after IdP authentication), not an arbitrary 401/403. The exact denial branch
is in the [pinned upstream provider](https://github.com/rancher/rancher/blob/v2.15.2/pkg/auth/providers/oidc/oidc_provider.go). Offline protocol fixtures and inert/check-mode tests are not
live acceptance or a full fake-API exercise of the Ansible lifecycle. Default and check mode are inert.

Any separately approved future repetition needs the existing protected human verifier inputs, a fresh
0700 evidence/private directory and a new 0600 `private/test.json` containing
only a unique `mfa-check-` plus 12 hex username and strong test password. No human
password/seed is used. Set `factor_evidence_dir` and explicitly approve
`rancher_denial_apply=true`; never pass secrets on command arguments.
An unexpected admission/response stops acceptance, deletes only the owned IdP
user, and retains private transaction material for exact native-session review.
It does not automatically delete Rancher users/tokens or assume a short TTL.
An interruption can require exact recorded-UID cleanup; never blindly rerun a
failed evidence directory or claim an `always` block survives process termination.

The executed procedure and stop conditions are:

1. Record trusted target/issuer, current provider/client/binding and realm/flow
   baseline. Create exactly one uniquely owned temporary Keycloak user with no
   groups, direct roles or inherited Rancher admin role. Generate private test-only
   password/TOTP material; never use Corey's credentials, factor or browser session.
2. Complete actual trusted-HTTPS authorization code/S256 authentication for that
   identity, preserving nonce/state and the Rancher PKCE cookie. Verify successful
   IdP authentication before treating a Rancher response as authorization evidence.
3. Submit only that identity's fresh code through the native Rancher login API.
   Require a native unauthorized response and no Rancher session/token issued.
   An unrelated TLS/client/code/nonce error is inconclusive, not a denial pass.
   Do not weaken group restrictions or grant a test role to make the flow work.
4. Revoke/delete only the exact test UID and its sessions and remove its generated
   credential files; verify cleanup and unchanged real accounts/groups/flow/app
   grants. Do not enumerate full user/token resources or inspect others' sessions.
   If unexpected admission creates Rancher state, stop and clean up only recorded
   test-owned session/identity IDs through supported APIs; uncertain ownership
   requires review. Do not assume a requested short login TTL is honored.
5. Finish health/resources and save sanitized status evidence. This covers one
   no-grant identity, not all roles or lost-IdP recovery. Live rollback remains a
   separate observed test; keep independent local recovery throughout.

## OpenBao named login and bounded native policy acceptance

Approved merged #153 source `701edff` executed at 2026-11-03 18:49 UTC. Owned
empty KV-v2 engines and OIDC method were prepared; a new dedicated confidential
client/secret and versioned PA policy/role were configured; only PA received the
own-client role and that client was enabled. Every repeat reported changed 0;
native/client repeats: 31/68 ok, failed 0. Exact policy, role, 900-second TTL and
3600-second maximum, independent recovery, trusted UI and native S256/state/nonce
redirect passed. Both managed engines remain empty. No human OpenBao token or
browser login was performed. Existing realms/apps/grants and cluster baseline
were preserved; Flux stays v0.15.2 with no restart/deployment.

Owner login: https://openbao.perkforge.home.arpa/ui/vault/auth?with=oidc ; role
`perkforge-sso-v1-platform-admin`, mount `oidc`. Public mount discovery does not
advertise OIDC; the pinned UI's `with` selector supports choosing it directly.
The default role stays empty. The owner subsequently reports successful named OIDC login. That is reported
browser acceptance; the separately approved bounded native ACL test and exact cleanup passed below.
No-group OIDC rejection and ordinary OIDC-token lifetime remain untested. Fresh factor prompting was not independently observed. Never use root in the
browser or capture the owner's credentials/tokens to manufacture acceptance.
Record/revoke only explicitly approved later test tokens; disabling the client
alone does not revoke native tokens. Retain engines and recovery on SSO rollback.

### Bounded native OpenBao policy test — one approved run passed

**Observed 2026-11-03 19:34 UTC, source `caa355a`: 58 ok / 12 changed / 0 failed.**
The one short-lived PA-policy actor passed platform create/update/read/soft-delete,
own-prefix tenant-name LIST, tenant-value/metadata403 and dangerous-capability
denials. It self-revoked; bearer403 and invalid exact accessor passed. Only both
marked dummy metadata records/versions were permanently removed and verified404;
the credential file was removed. Shared policy/root recovery and cluster baseline
were preserved. No actual user or Keycloak membership was involved. This is native
ACL acceptance, not no-group OIDC or ordinary OIDC-token-lifetime acceptance.

[accept-policy.yaml](accept-policy.yaml) defaults to no contact; explicit run and
`openbao-policy-acceptance-v1` approval are required. It mints one nonrenewable
5-minute token (10-minute explicit maximum) carrying the **actual PA policy**, no
default or identity policy. That policy can read platform values; the runner sends
KV requests only to its recorded `acceptance/openbao-check-<12hex>/sample` key in
each of `platform/` and `tenants/`. It does not use the owner's token, create a
Keycloak user, change shared group membership or alter the SSO role/client.

Approve the complete temporary scope before execution:

1. Verify trusted exact initialized store, root recovery, exact policy and owned
   KV-v2 engines. Require absent dummy keys and a new owner-only evidence directory.
2. Create ownership-marked dummy metadata and one synthetic tenant value with
   recovery authority; mint/record only the one private test token/accessor.
3. As the test token, create/update/read/soft-delete the platform dummy value and
   list only its own dummy tenant prefix. Require HTTP403 for the tenant dummy
   value and detailed metadata. Use current-token capabilities for auth/policy,
   token-creation, retention and destruction denial; never attempt dangerous
   writes to shared configuration to demonstrate them.
4. Self-revoke, require bearer rejection and verify the exact accessor invalid.
   On failure, root cleanup may revoke only the recorded accessor after ownership,
   policy and lifetime checks. No global token listing or other-user revocation.
5. With recovery authority, permanently delete **only both marked dummy metadata
   records and all their versions**, refusing unknown markers or unexpected
   version counts. Verify metadata404, unchanged shared policy/root recovery and
   remove the generated token file only when revocation is proven. Preserve all
   engines and existing credentials/identities. Finish the usual health snapshot.

A lost issuance response is inconclusive: retain its request marker, stop and
report bounded lifetime without inventing cleanup success. A data-cleanup failure
still attempts token revocation and retains exact ownership/scope evidence.
`always` cleanup is not a guarantee against process termination; never blindly
reuse a previous scope. Raw credentials/responses stay in no_log, owner-only
ignored evidence, never CI or public logs.

This verifies native ACLs with a root-minted test actor, **not** OIDC group denial,
claim validation or the owner's permissions/token lifetime. Owner-reported OIDC
login is recorded separately. The offline test runs this actual playbook through
verified TLS against an isolated in-memory OpenBao2.7.2 engine with synthetic
values: success, pre-existing-key/wrong-target refusal, unexpected admission,
cleanup interruption and uncertain issuance. Any live repetition requires a new approved scope; the single approved result is above.

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
### OpenBao self-session boundary — configured, live token tests pending

The candidate keeps `token_no_default_policy: true` and grants only these exact
self/UI operations alongside the existing platform-data and tenant-name rules:

| Path | Capability | Scope |
|---|---|---|
| `auth/token/lookup-self` | read | Current token metadata |
| `auth/token/renew-self` | update | Current token within its 1-hour explicit maximum |
| `auth/token/revoke-self` | update | Current token logout/revocation |
| `sys/capabilities-self` | update | Inspect current token permissions |
| `sys/internal/ui/resultant-acl` | read | Current UI permission map |

No wildcard `auth/` or `sys/` grant, token creation/lookup/renew/revoke for other
tokens, auth/policy management, tenant-value access, retention tuning or permanent
version destruction is added. The OpenBao 2.7.2 [UI auth service](https://github.com/openbao/openbao/blob/v2.7.2/ui/app/services/auth.js)
and [permission adapter](https://github.com/openbao/openbao/blob/v2.7.2/ui/app/adapters/permissions.js)
use these self-session/UI operations. The prior candidate denied them when the
default policy was absent. An administrator applies the reviewed policy through
Ansible; the resulting OIDC token exercises only its own session rights. The approved batch applied this exact policy and enabled its client as recorded
above; the offline fixture still does not prove live token/browser acceptance.

`test_sso_openbao_self_session.py` always checks the exact policy boundary. Its
optional real-engine fixture uses an existing OpenBao **2.7.2** binary, an isolated
loopback in-memory server and synthetic data/tokens; it never uses a kubeconfig,
operator token or live URL. `-dev-no-store-token` and before/after token-helper
metadata checks prevent writes to a user CLI credential cache. It reproduces the former five denials, verifies the
self/UI operations, rejects cross-token management and preserves platform CRUD
and tenant-value/retention/destruction/self-grant denials. Run it explicitly:

```sh
RUN_OPENBAO_POLICY_TESTS=1 OPENBAO_POLICY_TEST_BINARY=/path/to/verified/bao \
  python3 -m unittest discover -s big-bang-bootstrap/tests/integration -p test_sso_openbao_self_session.py -v
```

No download/install occurs. CI runs the policy contracts; real-engine cases skip
unless explicitly supplied that pinned binary. This is offline policy evidence,
not browser/OIDC acceptance. Initial application still requires reviewed empty
engines/auth mount, verified recovery, a dedicated client/secret and live approval.
Existing differing policies stop for migration review rather than overwrite.

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
Both applications retain their existing deployment. Rancher's native configuration
was subsequently approved/applied as recorded above; OpenBao configuration is applied; owner-reported named login is recorded; bounded native policy acceptance passed; no-group OIDC denial remains gated.
Publication alone activates neither and does not authorize repeating a prior batch.

1. **Rancher (configuration applied; remaining acceptance pending):** review exact environment/cluster/provider image and mounted issuer
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

## Nextcloud (unselected preparation)

[Nextcloud preparation](nextcloud/README.md) renders an independent disabled
client/provider candidate. Existing lifecycle adapters and coexistence inventory
remain unchanged. No activation or user provisioning is implemented by that stage.
