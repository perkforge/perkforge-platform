# Authorization review — disabled, not deployed

Start with the [role-by-application matrix](MATRIX.md) and the zoomable C4
`authorization_review`, `authorization_roles`, `authorization_core_apps`,
`authorization_observability`, `authorization_collaboration` and
`authorization_tenant_apps` views. They separate confirmed intent, implemented
review rendering, existing pilot evidence and unimplemented integration mechanics.

**Merging does not configure a realm, create users/credentials, apply Kubernetes
or OpenBao grants, enable clients, or extend SSO.** Nothing in this folder is
selected by the platform root or existing API configurators. The separately approved platform-only realm/group foundation below is live-tested; tenant migration, memberships and new app integration wiring remain incomplete.

## Review contract and current implementation

One PerkForge realm (`perkforge`) holds shared identities. Six canonical role
groups are proposed: `/platform/admins`, `/platform/engineers`, `/platform/viewers`, and tenant-qualified
`/tenants/<id>/{admins,developers,viewers}`. Multi-tenant memberships intentionally
grant their explicit scopes; parent groups grant nothing. Use separate clients
for supported platform/tenant apps, not one shared client or blanket realm roles.
Protocol/edition exceptions and client-specific claim disclosure remain decisions.

`desired.yaml` and Ansible/Jinja implement nonsecret **offline review artifacts**:

- `realm.yaml`: groups and only the three existing disabled client specimens
  (Headlamp, Rancher, OpenBao). No users, members, passwords, client secrets or
  realm-management grants. The all-app client inventory is design in the matrix,
  not fabricated clients for unsupported protocols.
- Platform-engineer adds only a disabled group specimen. Scoped diagnostics,
  secret access and direct live writes remain decisions; there is no engineer
  Kubernetes/OpenBao binding or inherited admin, identity or recovery authority.
- `kubernetes.yaml`: explicit platform-admin cluster-admin trust, a separate
  read-only platform-viewer role and per-tenant admin/developer/viewer examples.
  TD can read/list own Secret values and manage listed deployment resources but
  cannot mutate Secrets, RBAC or SAs or exec. TV has workload/status reads without
  Secret API/exec. **The platform-admin cluster-admin binding can bypass tenant
  privacy**; no deny rule or admission isolation is claimed against that actor.
- `openbao-roles.yaml`: exact OIDC group-bound roles with default policy disabled,
  platform KV values editable by PA, tenant names discoverable by PA, own tenant
  values managed by TA/read by TD, and proposed metadata-only viewer examples.
  No global `*`/sudo, standing tenant data read for PA, or auth/policy self-grant.
  LIST metadata, READ metadata and READ data are distinct. Admin metadata is
  read/list only: no metadata update (retention change), metadata delete (all-version
  deletion), engine configuration or destroy endpoint. Value writes and current-
  version soft delete remain separate. Proposed mount layout,
  helper endpoints, consent/elevation, retention and migration still need review.

The prior broad OpenBao administrative wildcard and developer-no-secret-read
specimens are superseded by the confirmed intent above. App policy does not
promise absolute privacy against cluster/identity/storage/backup administrators.
Tenant-approved grants and accountable emergency elevation are not implemented.

No changes are made to existing app deployments or proven pilot API owners:
Headlamp OIDC/group-to-Kubernetes patterns, OpenBao claim-bound roles/policies and
Rancher's default-off configurator remain reusable evidence. Their current physical
integration is not inferred. Helm deploys applications; Ansible owns separately
reviewed realm and native app API configuration. Never run competing import/API
owners. The existing OpenBao configurator additionally requires the independent
`platform_api_apply=true` gate; new review artifacts are not wired into it.

## Render locally, never apply

`preview.yaml` defaults to no writes and never authenticates or reads credentials.
Check mode also writes nothing. It **refuses** `authorization_apply=true` or enabled
integrations. Explicit render needs a fresh absolute output directory; existing
output is never overwritten. Output directory 0700/files 0600; no secret values.

```sh
ansible-playbook -i localhost, big-bang-bootstrap/configuration/authorization/preview.yaml
ansible-playbook -i localhost, big-bang-bootstrap/configuration/authorization/preview.yaml --check
```

To review synthetic tenants, supply `authorization_render=true`, a fresh protected
`authorization_output_directory` and explicit `authorization_tenants` using a
nonsecret YAML vars file. These are proposed representations, not approved import
payloads. Never run kubectl/app API apply against the generated review files.

## Everyday access and independent recovery

Everyday operator access is intended through Keycloak platform-admin SSO. Durable
local break-glass credentials belong in the operator password manager, independent
of Keycloak/cluster custody. Test supported local emergency access with SSO
unavailable. An app still needs its service/data to be available: off-cluster
custody is not a claim that login works during total cluster failure.

Temporary app flat files are at `~/src/perkforge-tmp-secrets/`, outside Git,
directory 0700/files 0600. Future approved app credential capture uses that path.
The operator owns password-manager migration and explicit temporary-copy cleanup.
Moving files is not rotation. Bootstrap root tokens, temporary master admins and
bootstrap passwords are not automatically permanent recovery identities. Review
per-app replacement/revocation separately; never remove the only tested recovery
path. CA signing, OpenBao unseal and SSH material stay outside this generic cache.

## Small implementation and acceptance stages

1. Resolve the fixed Keycloak image and stage-gated immutable release; initial
   app/local-admin access, trusted TLS and custody are separate approvals.
2. Review the matrix, exact realm/shared-user ownership, per-client claims and
   native app permissions. A tenant membership manager must not reset/delete a
   shared identity or assign an unapproved role. FGAP/API mechanics remain open.
3. Use small per-app MRs for idempotent read/compare/conflict refusal, approved
   credential references and explicit migration/revocation. No giant all-app apply.
4. Separately approve each change; verify positive and negative API/app identities,
   multi-tenant memberships, cross-app token replay, malicious workload/mapper
   attempts, cross-tenant queries and membership removal/session expiry.
5. Test independent recovery and retire temporary access only under explicit
   approval. Save safe evidence automatically and update C4 from proposed to
   observed only when evidence exists. Never equate login with authorization proof.

Offline tests render two synthetic tenants and model exact allow/deny rules;
preserved synthetic API tests cover create/idempotence/conflict/redaction. They
are not live authorizer, admission, OpenBao capability, app-login or data-isolation
acceptance. See matrix [primary guidance](MATRIX.md#primary-guidance-used-for-this-review).

## Realm/group foundation

[foundation.yaml](foundation.yaml) is the first operational step, separate from
`preview.yaml`. Big Bang still owns deployment; Ansible owns this Admin API state.
It reuses the established TLS/private-login, ownership-marker, exact-group and
empty-role-mapping patterns from the earlier Ansible API owners. It deliberately
**does not invoke** the older `keycloak-realm.yaml` trial bootstrap, which creates
trial users and an app client, or import the review renderer's disabled clients.

### Who does what and why

1. Review this code, target UID, CA/HTTPS URL and explicit tenant IDs. Keep tested
   master recovery access and its independent protected custody intact. No new
   administrator, service account, credentials, user or membership is created.
2. Default/check mode performs no API calls or credential reads. Explicit
   `realm_foundation_inspect=true` authenticates/read-compares without writes;
   `realm_foundation_apply=true` separately permits the bounded writes below.
3. Verify the physical Kubernetes target UID, then authenticate the existing master
   administrator through verified HTTPS using owner-only username/password files.
   No redirects/proxy/netrc, token persistence or credential output. The existing
   master credential is powerful; the playbook's scope is not a narrower credential.
4. Create only a missing owned `perkforge` realm (display name PerkForge; registration
   and password reset off, brute-force protection and bounded sessions on). An
   existing realm must match declared security settings and ownership purpose;
   unknown/legacy realms are refused, never adopted, PUT, deleted or reimported.
   Keycloak supplies its normal built-in clients/roles; this playbook adds no app
   clients or privileged role mappings and assigns none to users.
5. Read all desired exact group paths and direct role mappings before group writes.
   Create only missing parent-first groups without IDs, moves, updates or grants.
   `/platform/{admins,engineers,viewers}` and `/tenants` are always defined. Only
   explicitly supplied tenants get `/tenants/<id>/{admins,developers,viewers}`.
   Empty tenant input creates no fictional tenant. The six role **families** are
   not six globally privileged realm roles. Parent groups and leaves have no
   Keycloak role mappings; merely belonging to one does not authorize an app.
6. Reread paths/mappings. A rerun makes no writes when owned state matches. Partial
   successful creates survive a later failure; a reviewed rerun adds missing paths
   only. Conflicts/default groups/unexpected mappings/concurrent appearance stop
   the run. No rollback, pruning, password reset or membership cleanup occurs.

The playbook intentionally does not enumerate/change shared users, assign members,
reset passwords, delete identities, enable delegated administration/FGAP, create
client claims, or apply Kubernetes/OpenBao/app permissions. Multi-tenant identity
membership stays unchanged: tenant-admin membership management needs a separately
reviewed allowlist/API owner; no tenant may reset/delete a shared user or grant a
role in another tenant. Platform-engineer remains an empty group with unsettled
diagnostics/secret/live-write scope, never inherited administrator authority.

### Proposed live approval and inputs

An action-time approval would permit authenticating the existing master admin,
creating the missing realm and canonical empty groups for the **explicitly reviewed
tenant list**, and readback. It grants no human/app permissions. Required private
inputs: target kubeconfig/context/expected UID; exact HTTPS URL and public CA;
`realm_foundation_username_file`/`realm_foundation_password_file` (regular owner-only
0600 files); `realm_foundation_recovery_preserved=true`; `authorization_tenants`.
Default URL is `https://keycloak.perkforge.home.arpa/auth`. No new credential or
Secret delivery, release promotion, chart change or cluster RBAC is needed. Keep
safe output automatically in the operator's existing protected evidence directory;
never log API bodies/tokens. Check mode is offline validation, **not** a live diff.
The explicit inspect mode supplies the authenticated read-only comparison.

Future approved apply uses the existing bootstrap inventory and a protected vars
file with [foundation.yaml](foundation.yaml), not the review artifacts. No runnable
live command or private target inputs are embedded here. Bootstrap retirement and
permanent recovery remain separate approvals. A foundation group is not proof of
working six-role authorization: each subsequent app/membership MR needs allowed/
denied tests, token/session revocation and multi-tenant isolation acceptance.

### Tests and limits

Real Ansible runs against a synthetic localhost HTTPS Keycloak-shaped API cover
create, idempotence, read-only inspection, interrupted creation/resume, canonical
multi-tenant paths, unchanged shared memberships, refusal of ownership/role/default
inheritance conflicts, wrong target/CA and denied access, and credential redaction.
These are offline protocol/safety tests, not actual Keycloak authorizer or human
login evidence. Live platform-only creation/readback and second-run zero-change
acceptance subsequently passed as recorded below. Tenant creation, human/app
permission denial and independent recovery drills remain unexecuted. No app
integration is enabled.

Versioned API contract: [Keycloak 26.8.1 Admin REST API](https://www.keycloak.org/docs-api/26.8.1/rest-api/index.html)
(realm create/read, exact group-by-path, child creation, role mappings). Group-create
requests carry no existing ID and accept only Created; concurrent conflicts stop.
The API is not transactional; inspect state after any uncertain request outcome.

### Observed platform-only execution — 2026-11-01 20:20:07 UTC

Explicitly approved `authorization_tenants: []` used clean merged #127. The realm
was absent before writes. Inspect changed 0; initial apply changed 6 (realm plus
five groups); second apply changed 0, failed/unreachable 0. Independent API readback
verified exactly `/platform`, its `admins`/`engineers`/`viewers` children, and
`/tenants`; all memberships and custom group mappings empty, users 0, default groups
0, custom app clients 0. Normal Keycloak built-ins are expected and were verified.
Existing master access, source/root specifications, application readiness and
Keycloak/database pod identities remained intact. No new credential, user, app
client, role grant, tenant group or SSO was created. Protected automatic evidence
contains recaps/readback only; credential values were absent from saved logs.

This is proof of structural creation and idempotence, **not human authorization**.
Future tenant/member/client operations and permanent recovery/bootstrap retirement
still require review and action-specific approval. Nothing here authorizes reruns
or expands platform-engineer rights. No cluster release promotion was required;
source remains v0.14.0/local-keycloak, while reviewed Ansible came from merged #127.
