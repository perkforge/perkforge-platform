# Portal group-to-role mapping

`portal-role-mapping.yaml` is a separately gated, default-off workflow for #16/#43.
It preserves the agreed **generic roles, tenant-scoped groups** model:

| Realm role | Group |
| --- | --- |
| tenant-admin | /tenants/portal/admins |
| tenant-developer | /tenants/portal/developers |
| tenant-viewer | /tenants/portal/viewers |

These are non-composite realm roles, not Keycloak realm administration or native
application privileges. The original foundation's `perkforge-role` attribute is
metadata, not a mapping. Do not weaken or rerun the empty-group foundation after
real mappings exist. The new workflow does not change users, memberships, clients,
protocol mappers, client scopes, application roles or any other tenant's groups.

## Tenant context is mandatory

Generic role membership **never identifies a tenant**. Consumers must authorize
against the exact tenant-qualified group in the reviewed context, not combine a
flat generic role list with an unrelated tenant membership. For example, someone
in `/tenants/a/admins` and `/tenants/b/viewers` is **not** an administrator of b,
even though their realm role list includes `tenant-admin`. A role-only token, an
unknown tenant, or a missing exact group must fail closed. Consumers must validate
issuer, audience and signature before claims; this workflow does not configure
those consumers or activate any application grants. Native integration acceptance
must include that mixed-membership denial case and offboarding/token-expiry tests.

## Inspect, then separately approve apply

Default invocation and `--check` never contact APIs or read credentials. Use the
normal reviewed local bootstrap inventory, not a new target definition. Inspection
requires `pr_inspect=true`, the scope string
`portal-generic-group-role-mapping-v1`, recovery-preserved acknowledgement, the
physical cluster identity inputs, `pr_realm_id`, and exact immutable `pr_group_ids`
for `/tenants`, `/tenants/portal`, and all three child groups. Credential input
files must be existing owner-only mode-0600 regular files; CA verification is
mandatory. Follow existing credential custody procedures; never put values in Git.

After approval for the concrete live mapping, `pr_apply=true` creates only missing
managed generic roles and adds only missing Portal mappings. Existing foreign or
composite roles are rejected rather than adopted. Existing extra direct mappings,
parent mappings and client roles stop the operation. All group and role inspection
precedes writes; mappings and role IDs are re-read afterward. No removal, overwrite,
user provisioning, migration, or rollback is automatic. A partial failed apply can
be inspected and retried; this is not a transaction and does not roll back earlier
successful adds. Concurrent administrator changes are outside this workflow's
control; serialize approved identity operations.

Default roles and user-specific grants are not audited here. This is **group mapping
verification**, not proof of effective user or native-application authorization.

API reference: [Keycloak Admin REST API](https://www.keycloak.org/docs-api/latest/rest-api/index.html),
realm roles and group role-mappings endpoints. Local tests prove default/check-mode
safety, input rejection and the source write surface; live API compatibility and
positive/negative application access remain unrun until separately authorized.
