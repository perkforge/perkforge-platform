# Mattermost tenant context acceptance

Portal is the first integrated PaaS pilot. The shared context owns tenant/app
names; the native Mattermost team, channel and user IDs must be resolved on the
selected instance and reviewed before applying membership. Keycloak groups carry
roles, but OIDC login is not native team/channel synchronization. Do not assume
paid group-sync or ABAC features in the selected Entry baseline.

Tenant viewers may participate in Mattermost channels and see channel alerts.
They receive no direct ntfy or other alert subscription. Platform engineers have
cross-tenant visibility, not an implicit Mattermost System Admin grant. Native
team/channel administration rights are not inferred from either decision.
The approved topology is one **PerkForge** team with private tenant channels.
Team-directory and direct-message visibility across tenants are accepted; private
channel content must remain scoped. Team/channel slugs and native IDs are explicit
contract inputs, not derived grants. Example slugs below do not establish that
those objects exist or approve additional membership.

## Inspect a configured native context

`inspect.yaml` is a GET-only acceptance check. It is inert by default and in
Ansible check mode. It neither configures the server nor provisions, removes or
synchronizes members, creates hooks, sends messages or modifies the Keycloak
client. Supply an already authorized read credential; no token creation is part
of this entrypoint. It requires a trusted HTTPS origin, public CA and owner-only
0600 token/contract files under 0700 directories. Never put the contract in Git:
webhook IDs reconstruct secret URLs.

A protected JSON contract has this shape (values below are symbolic, not valid
native IDs):

```json
{
  "schema_version": 1,
  "context_id": "portal",
  "team_name": "perkforge",
  "channel_name": "portal-alerts",
  "team_id": "RESOLVED_NATIVE_TEAM_ID",
  "channel_id": "RESOLVED_NATIVE_CHANNEL_ID",
  "publisher_user_id": "RESOLVED_DEDICATED_PUBLISHER_ID",
  "webhook_id": "PROTECTED_NATIVE_WEBHOOK_ID",
  "team_members": [{"user_id": "RESOLVED_USER_ID", "roles": "team_user"}],
  "channel_members": [{"user_id": "RESOLVED_USER_ID", "roles": "channel_user"}]
}
```

The team roster is the **entire shared team**, including other tenants. The
channel roster includes only the publisher and the approved Portal and platform
members. Shared-team membership must never imply private-channel membership.
Keep the team roster synchronized across all channel inspection contracts. Explicit native admins, if separately approved, are represented by
`team_user team_admin` or `channel_user channel_admin`; the tool does not grant
these roles. Do not invent IDs from email or a mutable display name. Resolve
Keycloak subject-to-native-account linkage separately. An app-global System Admin
can bypass channel membership, so the roster inspection is not a complete user
access audit and must not be presented as one.

```sh
ansible-playbook big-bang-bootstrap/configuration/authorization/sso/mattermost/context/inspect.yaml \
  -e @/protected/mattermost-context-inputs.yaml
```

Inputs: `mattermost_context_inspect: true`, `mattermost_context_origin`,
`mattermost_context_ca_file`, `mattermost_context_token_file` and
`mattermost_context_contract_file`. No live operation is authorized by an example.
The check refuses drift, deleted objects, public team/channel, open invitations,
wrong IDs, unexpected/missing members or roles, and a webhook not locked to the
exact channel. It requests the API's 200-entry maximum and refuses a full page,
rather than treating a truncated roster as complete. Larger teams require a
reviewed paginated implementation. All API responses and webhook identity remain
redacted. Successful repeats make no changes.

## Provisioning and delivery boundaries

Use one channel-locked incoming webhook per audience with a dedicated approved
publisher. Store the runtime webhook URL in OpenBao, deliver only to the approved
Grafana/GitLab consumer, and retain independent recovery inputs according to the
credential custody procedure. Never put the URL in an alert label, shared context
manifest or public values. The delivery payload must not contain a dynamic
`channel` override. [Incoming webhook documentation](https://docs.mattermost.com/integrations-guide/incoming-webhooks)
explains the native lock and secret URL behavior.

The selected v11.11.0 API shapes are the upstream
[IncomingWebhook model](https://github.com/mattermost/mattermost/blob/v11.11.0/server/public/model/incoming_webhook.go)
and [API definitions](https://github.com/mattermost/mattermost/tree/v11.11.0/api/v4/source).
A matching metadata check does not establish runtime edition entitlements,
network enforcement, real login, message delivery or wrong-tenant denial.
Acceptance still requires an actual ordinary Portal identity, a foreign tenant
identity, a platform engineer, native membership removal/offboarding, and channel
lock enforcement. Test firing/resolved notifications in this private channel and
the scoped ntfy route, with no direct alert subscription for tenant viewers.

Baseline deployment, data services/TLS, edition/security-patch review and operator
trust remain the package runbook's gates. This source adds no root selection or
live permission. The integrated Portal pilot must not skip those gates merely
because this verifier passes against fixtures.

## Required invitation-boundary acceptance before enablement

Private channels alone are not sufficient: the pinned v11.11.0 default
[`channel_user` role](https://github.com/mattermost/mattermost/blob/v11.11.0/server/public/model/role.go)
includes `manage_private_channel_members`. A normal member can therefore widen
membership unless the actual edition's supported policy prevents it. OIDC groups
do not change that default.

Before enabling the pilot, verify the exact deployed Entry edition supports the
approved restriction, then test with ordinary Portal admin, developer and viewer
identities that adding a foreign tenant to the private channel is denied. Test
the approved membership manager separately, plus foreign-tenant channel
discovery/content denial and PE access. Record binary/version, edition, effective
policy and test outcomes without tokens. Channel membership is platform-managed; tenants must not manage who joins.
The approved platform operator's concrete native identity and minimum required
rights must be resolved before apply; this runbook grants neither System Admin
nor team/channel admin automatically.

The GET-only inspector does **not** evaluate effective native role permissions,
invitation restriction, license entitlements or these denial tests. Its success
is not permission to enable. Do not bypass an edition limitation using unreviewed
role changes or assume a paid feature exists. Applying live permission settings
requires separate confirmation.

## Planned platform-managed reconciliation

The approved target is automated **exact** channel membership, not native paid
group sync. The authoritative desired human roster is the union of the exact
context's Keycloak admin/developer/viewer groups and explicit platform exceptions.
Include the separately approved publisher identity as a service exception.
A flat realm role is not context authorization: an admin in tenant A must not
gain tenant B membership or administration. No additional native admin rights
follow from tenant role labels.

The adapter must resolve pinned Keycloak group IDs and immutable subject-to-native
user-ID bindings, fetch complete membership and reject unresolved/ambiguous
identity, partial pagination, unavailable authority or empty/incomplete snapshots
before planning removals. An authoritative empty group is different from a failed
read. Protect all runtime identifiers and credentials; never match on display
names alone.

Plan mode should show exact additions/removals without granting access. Once
approved for live execution, reconcile only the named tenant channel, removing
**all** unauthorized members, including manually added users, and read back the
complete result. Loss of all authorized groups removes channel access; removal
from one group while another still authorizes membership does not. Preserve only
explicit approved platform/service exceptions. Do not delete users, remove shared
team memberships or alter other channels as a side effect. Re-fetch authority and
current membership immediately before apply; fail on changed assumptions, then
verify idempotent repeat and offboarding against the actual edition.

The default-off implementation below realizes this contract. Live enablement
still requires the invitation-boundary acceptance above and confirmation of the
concrete permission changes. The existing inspector and planner remain GET-only unless apply is separately enabled.

## Reconciliation implementation (default-off)

`plan.yaml` reads the four pinned Keycloak groups (Portal admins, developers,
viewers and `/platform/engineers`) and computes an exact private-channel delta.
Every platform engineer is included, with access to that channel's existing
history. Protected runtime group UUIDs must match those exact paths. It never
derives native identity from email: every enabled authoritative Keycloak subject
requires a protected binding to a native Mattermost user, whose `openid`
`auth_data` must match. Missing/redacted linkage blocks the operation. Non-exception authoritative users
must have only ordinary native global/team/channel roles; unexpected admin roles
block rather than being silently downgraded or bypassing invitation policy.

Use the inspector's protected files/TLS inputs plus
`mattermost_keycloak_origin`, `mattermost_keycloak_ca_file` and
`mattermost_keycloak_token_file`. The contract adds `groups` entries
(`id`, `path`), `bindings` entries (`subject`, `user_id`) and an
`exceptions` list of explicitly approved native service/operator IDs.
Only enabled authoritative group members are included. Direct group reads are
bounded to 199 members; full pages and nested subgroups block rather than silently
truncate. Empty successful groups authorize offboarding, not failed API calls.

Set `mattermost_membership_plan: true` to read and plan. Check/default modes
contact nothing. Exact `mp_add`/`mp_remove` lists stay in protected in-memory
Ansible facts; console output contains counts only. An approved operator can
consume those facts within the same protected execution. No plans containing
private IDs are written to Git or ordinary logs.

Applying additionally requires `mattermost_membership_apply: true`,
`mattermost_membership_apply_confirmed: true`,
`mattermost_invitation_boundary_verified: true`, and exact
`mattermost_membership_approved_add`/`mattermost_membership_approved_remove`
lists matching the reviewed plan. These flags record prerequisites, not substitute
for actual user authorization. The play re-reads authority immediately before
mutations, removes unauthorized channel members, adds ordinary members, then
reads back authority and membership. It does not grant native admin roles,
create accounts, join the shared team, change native global roles or schedule
itself. Missing shared-team membership blocks; account/team provisioning is a
separate approved step.

The multi-API operation is not transactional. Concurrent authority drift or a
mid-apply failure stops with a failed result; completed mutations are not rolled
back into unauthorized access. Re-plan from fresh reads before retrying.
Do not enable until effective invitation restrictions, packaged-edition behavior,
immutable linking and production read permissions have been accepted.

Synthetic HTTPS regression tests additionally cover changed authority before apply
(no mutations), an add failure after removal (no restoration of unauthorized
access), rejection of a stale retry delta, and a successful freshly planned retry.
Overlapping group membership retains access until the last authorizing group is
removed. These are fixture-based reconciler checks, not native edition, live
offboarding, invitation-policy or production API acceptance.


### Disposable edition evidence

A checksum-verified official 11.11.0 Enterprise binary selected Entry without
a trial or uploaded license. A synthetic test reproduced default unauthorized
invitation (201), then removed `manage_private_channel_members` from the global
`channel_user` role through the native API (200). Ordinary tenant personas and
a PE were denied further invitations (403); foreign channel/content reads were
403, PE read was 200, and a synthetic System Admin membership manager could add
members (201). Disposable server/database were stopped afterward.

This is a global default-role effect, not paid per-team schemes; it affects every
ordinary channel member. No live role change was made. It does not prove vendor
support entitlement, exact Iron Bank image equivalence, privileged native
team/channel-admin behavior, restart persistence, or Entry renewal behavior.
Those limits remain explicit pre-enable gates, not assumed successes.
