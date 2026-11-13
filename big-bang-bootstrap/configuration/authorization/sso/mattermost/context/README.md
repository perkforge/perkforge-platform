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
The private Portal alerts channel is `alerts` in the desired `tenant-portal`
team. These names do not establish that those objects exist.

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
  "team_name": "tenant-portal",
  "channel_name": "alerts",
  "team_id": "RESOLVED_NATIVE_TEAM_ID",
  "channel_id": "RESOLVED_NATIVE_CHANNEL_ID",
  "publisher_user_id": "RESOLVED_DEDICATED_PUBLISHER_ID",
  "webhook_id": "PROTECTED_NATIVE_WEBHOOK_ID",
  "team_members": [{"user_id": "RESOLVED_USER_ID", "roles": "team_user"}],
  "channel_members": [{"user_id": "RESOLVED_USER_ID", "roles": "channel_user"}]
}
```

Include the publisher and all approved platform/tenant members in each actual
roster. Explicit native admins, if separately approved, are represented by
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
