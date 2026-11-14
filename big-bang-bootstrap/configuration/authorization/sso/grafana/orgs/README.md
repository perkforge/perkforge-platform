# Inactive native organization/entitlement mapping

Source preparation for #38/#218, not deployed tenant access. The default and
`--check` write nothing. `render.yaml` accepts explicit `grafana_org_contexts`
entries: `context` is an entire reviewed `paas_context`, `org_id` a separately
verified native integer greater than 1, and `query_identity` the exact
`pf-log-<context>-read`. Set `grafana_org_render=true` and a fresh absolute
`grafana_org_output` only to write review files. No API calls, credentials,
organization creation, group mapping or live activation are implemented here.

The existing Grafana own-client role mapper remains the claim authority. The
rendered entitlement proposal attaches new noncomposite Grafana client roles to
exact canonical context groups, never tenant roles to platform-admin. It is not
native ID discovery or evidence that those groups currently have members.
Existing `/platform/admins` app entitlement and recovery access remain unchanged.
The existing client configurator rejects group delegation: do not run it to apply
this proposal or remove that guard without a separately reviewed exact adapter.

Platform engineers receive a dedicated entitlement for Viewer in existing org 1,
retaining its dashboards. Each tenant receives a separate native organization,
with canonical Admin/Editor/Viewer mappings. No wildcard/default org assignment.
Only PA yields global GrafanaAdmin; recognized non-PA entitlements yield global
None, so Admin in tenant A cannot elevate Viewer in B. Unrecognized claims yield
no role. Native Grafana 13.2.1 tests caught that an unconditional None fallback
allows login even with strict mode, so the fallback is deliberately gated.

## Activation prerequisites and exact security batch

1. Verify issuer, Grafana client UUID, canonical group UUIDs, context ownership,
   existing org1 and target tenant org IDs through authorized metadata access.
   Supplied IDs in review artifacts are declarations, not attestation.
2. Review creation of only the listed noncomposite own-client roles and mapping
   each to its exact verified canonical group; no realm roles, new human group
   memberships, PA grant, composite roles or unrelated client changes.
3. Review native org creation if absent and exact OAuth role synchronization.
   Preserve org1 dashboards/PA recovery, with no global tenant Admin fallback.
4. Install tenant read-only datasource credentials only in that org, platform
   `pf-log-platform-read` only org1. No collector/write credential in Grafana.
   Credentials and source-owned datasource provisioning are separate protected
   custody/ESO work. Tenant org Admin can add datasources: backend credentials,
   API allowlists, network and SSRF restrictions MUST prevent alternate URLs,
   copied headers and org-ID spoofing from reaching another tenant/platform.
5. Verify actual OAuth login, org switching, `/api/ds/query`, proxy/resource APIs,
   mixed memberships, foreign-org IDs, and datasource-create bypass attempts.
   Renderer and synthetic OAuth tests alone do not prove Loki query isolation.

## Revocation is an implementation gate, not instant login synchronization

Native OAuth organization sync happens at login. Removing a Keycloak group or
client role does not by itself revoke an existing Grafana session or org grant.
Before tenant activation, a reviewed controller/operator procedure must remove
only the affected native org membership, revoke relevant Grafana sessions/tokens
and relevant IdP sessions, then verify a previously authenticated session cannot
query or switch to that org. Preserve other tenant membership and PA recovery.
Token refresh alone is not proven sufficient. No such continuous reconciler is
implemented by this renderer; do not claim immediate revocation or promote this
source as production tenant authorization until the negative native tests pass.

`test_grafana_org_oauth.py` uses the checksum-pinned Grafana binary and a disposable
localhost synthetic OAuth issuer/database, creates two fixture orgs, and checks
actual mixed Admin/Viewer, PE Viewer, PA and unknown-login outcomes. It is not a
live Keycloak group delegation or logging acceptance test. No custom image.

### Verified native revocation building blocks

Pinned Grafana routes: `DELETE /api/orgs/{orgId}/users/{userId}` removes exact
membership; `POST /api/admin/users/{id}/logout` invalidates that user's sessions
(across orgs, so disclose the interruption). The synthetic native fixture verifies
existing-cookie org switch denial after removal, preservation of tenant B Viewer,
then cookie rejection after logout and login-time sync retaining only B. It also
checks tenant first-login org lists, forced org1 switching and platform datasource
UID access denial. A forced header on `/api/org` alone is not a valid denial test:
Grafana may return the current authorized org rather than honoring that header.

Before ownership transfer: remove the exact client entitlement/group binding;
remove affected org memberships; revoke sessions and separately inventory/revoke
relevant non-session credentials; verify old-cookie/query denial; only then expose
the new ownership epoch. A still-valid old OAuth claim must not re-add membership:
revoke IdP sessions/tokens and verify newly issued claims before reopening login.
This is a bounded operator procedure proposal, NOT authority for a persistent
Grafana-admin reconciler. Live token/session/credential cleanup remains unproven.

Pinned native metadata routes are `GET /api/orgs/name/{name}/` (Grafana13.2.1)
and `GET /admin/realms/perkforge/group-by-path/{path}` (Keycloak26.8.1). Use exact
reviewed names/paths only through approved custody; do not enumerate humans or
invent missing IDs. No live metadata credential access was performed in this PR.

## Metadata and guarded organization adapter

`inspect.yaml` is a separate explicit read-only operation. Default/check touches
no private files or APIs. It accepts a pre-existing temporary operator token file
for Keycloak and a protected JSON file containing only the Grafana Authorization
header (both0600 under0700 owner directories), public CA, exact desired org name,
context and fresh private receipt path. It reads only org1, exact org name, owned
Grafana client and five exact canonical group paths. Missing org/groups are
reported absent, not created. It never issues tokens, reads human memberships or
client secrets, or discovers vault entries. Sanitized receipt IDs require review;
they are not authorization. Metadata API access still requires its scoped approval.

`ensure-org.yaml` is an unconnected include for an approved orchestrator, not an
entrypoint or grant. It accepts only exact inspected name, preserves org1, creates
only if404 and verifies the returned ID. Native org creation may associate the
performing recovery administrator with the new org; record and preserve that
already-global recovery identity explicitly, not as Keycloak-derived access.
No org deletion, invite, datasource, user role or membership API exists here.

The next exact Keycloak operation must create/reuse only each named noncomposite
Grafana role, require reviewed owned client UUID and exact canonical group UUID,
verify existing role description/container/composites, add only that role to that
group's own-client mapping, AND add it to the same Grafana client's own scope
mapping. `fullScopeAllowed=false` is retained; do not broaden realm/client scopes.
Read back exact additions and preserve previous role sets, especially the existing
`/platform/admins` role and subjects. Existing admin-only reconciler rejects these
new roles, so its narrow guard must not be repurposed or silently relaxed.

The unconnected `ensure-entitlement.yaml` and `ensure-role-binding.yaml` now encode
those exact additive operations. They require an explicit approval marker and
reviewed native IDs, re-read owned client/mapper and canonical path before writes,
refuse foreign/drifted roles, preserve all prior binding IDs, and make retries
idempotent. They do not authorize themselves or create missing canonical groups.
`test_grafana_org_adapter.py` exercises these task files with a disposable HTTPS
protocol fixture: role plus two bindings, no-op retry and changed-client denial.
This is mocked protocol evidence, NOT a live Keycloak grant/denial test.

Observed read-only pilot metadata (2026-11-14): org1 exists; desired profile name
`PerkForge Portal` is absent, as are all three Portal canonical tenant groups.
Platform canonical groups and owned Grafana client exist. Therefore tenant
activation also requires reviewed canonical group foundation, not guessed IDs or
adoption. No human membership was inspected or changed. Native IDs remain in
private operator evidence rather than this reusable source.

## Additive canonical foundation, never realm initialization

Exact further pilot metadata found the original managed `/tenants` parent but no
`/tenants/portal` or generic tenant roles. The unconnected `ensure-foundation.yaml`
therefore implements the minimum existing-policy foundation: four groups (context
parent plus three leaves), three managed noncomposite generic realm roles, and
one exact role mapping per leaf. It requires pinned existing parent ID and explicit
expected IDs/null for every path. Before any write it rejects foreign attributes,
role definitions or inherited mappings. It never updates/moves/deletes an existing
group, adopts a name, initializes a realm, or touches users. Newly assigned IDs
must be reviewed/pinned for retry; a null expectation will not adopt an object
created during an interrupted earlier attempt. Existing post-entitlement mappings
are deliberately not silently accepted by this initial foundation stage.

Run foundation only before entitlement application, then verify exact group/role
IDs and native direct/effective mappings. The entitlement include separately checks
each canonical ancestor plus leaf for unexpected direct/effective own-client roles:
parents must have none; leaf may contain only its exact noncomposite entitlement.
An inherited PA claim must stop the operation, not be preserved as harmless drift.

Pinned Grafana fixture now explicitly confirms org creation associates the existing
recovery creator as native org Admin. This is the already-global recovery exception,
not a claim of zero membership side effects or a Keycloak-derived new human grant.
Keep tenant exposure gated until real gateway namespace/ownership-epoch isolation
and negative query APIs pass; managed empty groups alone grant nobody access.
