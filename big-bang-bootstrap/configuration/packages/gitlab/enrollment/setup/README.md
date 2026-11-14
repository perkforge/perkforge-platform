# Disabled Keycloak reader preparation

Source component only. No target permissions or clients are configured by adding
these files. Native activation requires a separate exact security approval.

- Entrypoint: `run-kc-reader.sh --apply OPERATOR_TOKEN RECEIPT INPUTS_JSON`.
- Bare/default invocation is inert; `--validate` makes no requests or writes.
  Direct Ansible check mode is also inert.
- Only duplicate-key-free literal JSON is accepted before Ansible. The fixed
  wrapper owns an exact native context lock and validates protected ancestry,
  token/receipt type, ownership and modes through the existing reviewed guard.
- Inputs select context, source revision, origin, realm, CA, the three canonical
  group IDs, explicit run/scope, and explicit permission to enable FGAP. No
  arbitrary names, extra variables, policy fragments or callbacks are accepted.

## What apply does, after separate authorization

1. Verify Keycloak26.8.1, exact realm and three canonical leaf group paths/IDs.
2. Refuse foreign existing reader, policy and permission identities. Enable
   fine-grained admin permissions only if explicitly selected. Read back the
   realm's native admin-permissions client UUID against exact client lookup.
3. Create one **disabled** confidential service-account client with browser,
   password and implicit flows off and fullScopeAllowed false. Record native
   IDs immediately, verify configuration, service-account identity, absence of
   inherited groups and absence of realm-management role mappings.
4. Create a User policy bound only to that service-account UUID and a permission
   bound to exactly the three canonical groups, view/view-members scopes and
   the sole owned User policy. Verify native associations by exact identifiers.
5. Finish **PendingCustody**, keeping the reader disabled. This component never
   retrieves a client secret, requests a service token, enables the client,
   approves users or writes an OpenBao record. Durable custody and independent
   read/denial acceptance must be implemented before activation, not represented
   by a caller-supplied `custody_verified` boolean.

## Partial effects and retries

- Receipt records whether FGAP enablement was requested and whether it was
  subsequently observed, plus each returned client/policy/permission ID.
- Realm enablement response loss retains PermissionsEnablePending. A later
  guarded read can observe the realm's native permission client and resume.
  Previously observed permissions becoming disabled is drift, not permission
  to turn them back on silently.
- Lost client/policy creation responses without a recorded returned ID do not
  authorize adoption on retry. Stop for manual review, preserving native state.
- No rollback disables realm permissions, deletes shared admin-permissions,
  removes a foreign policy or deletes the disabled reader. Owned partial effects
  remain auditable; no success or activation is inferred from their presence.
- A bounded failure substage is emitted without raw API bodies or credentials.
  PendingCustody is not proof that the eventual client's access works.

## Native authority caveats

- The one-time operator needs administrative realm/client/authorization setup
  authority and the server-version preflight read. Routine jobs do not receive
  this operator token. Its actual identity/custody remains an activation gate.
- Fine-grained Groups view-members also implies user-profile viewing for the
  selected group's members and applies to descendants. Current groups must be
  leaves, but native permission is not immutable member-ID/field-only access.
  The observer minimizes output and rejects non-leaf drift; it cannot narrow
  the credential's underlying API authority. Ancestor group metadata may also
  appear in native filtered hierarchy queries.
- No broad realm view-users/manage-users roles are granted. A User policy is
  chosen because pinned view partial evaluation supports it; Client policy is
  not assumed equivalent.

## Pinned representation checks

The official26.8.1 [FGAP REST guide](https://github.com/keycloak/keycloak/blob/26.8.1/docs/documentation/server_admin/topics/admin-console-permissions/fine-grain-v2.adoc)
and native provider/resource code define the contract:

- Policy name search returns204 when absent; create returns201 with its ID.
- Client creation returns201 with an exact Location identifying the new client.
- Generic User policy config.users contains native service-account UUIDs.
- Permission resources have **internal authorization IDs**; their `name` is the
  canonical group UUID. Compare `/policy/{id}/resources` names, not internal IDs
  against group IDs. Compare `/scopes` names and `/associatedPolicies` exact ID.
- Typed policy GET without fields=* may omit associations. Omission is not proof
  of an empty permission and is never used as an authorization acceptance gate.

The synthetic HTTPS fixture uses these pinned shapes and dummy credentials. It
covers disabled preparation, no-op repeat, partial response recovery/refusal,
foreign resource drift and zero secret/token requests. Native target acceptance
is still required after the separately authorized custody/activation stage.
