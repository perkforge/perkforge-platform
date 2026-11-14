# PaaS context contract

Portal is the first integrated pilot for #16/#43, #218, #39, Mattermost and
GitLab #334. This platform-owned authored YAML is the common boundary input,
not a configuration generator, live inventory, identity grant or automatic sync.
Tenant code and alert labels cannot choose its own context or destinations.
Adapters must consume the reviewed contract rather than invent separate namespace
ownership lists. Names are desired identifiers; resolve immutable native IDs and
verify ownership before a separately approved apply.

```sh
python3 -B big-bang-bootstrap/configuration/authorization/contexts/verify.py \
  big-bang-bootstrap/configuration/authorization/contexts/*.yaml
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=big-bang-bootstrap/tests \
  python3 -m unittest security.test_paas_context -v
```

The verifier fails on duplicate YAML keys or contexts, wildcard/cross-context
paths, runtime/control overlap, public alert channels, assumed GitLab IDs,
activation and shared Grafana access. It is an offline boundary consistency
check, **not** proof that a backend authorizes queries or native app memberships.
Adding a context requires platform review of actual enrollment ownership, not
just a matching namespace prefix.

## Approved Portal boundary

- Keycloak groups `/tenants/portal/{admins,developers,viewers}` identify tenant
  roles. Assign roles to groups, people to appropriate groups; parent groups do
  not grant access. Existing `perkforge-role` group attributes are metadata, not
  Keycloak role mappings. The guarded native mapping workflow is documented in `../PORTAL-ROLES.md`; this contract itself does not apply it.
- Runtime `tenant-portal` only. `tenant-portal-config` and
  `tenant-portal-release` are control namespaces, not tenant runtime diagnostics.
- ntfy exact topic `tenant-portal-alerts`; a private Portal alerts channel.
  Mattermost uses the approved shared `perkforge` team and private
  `<context>-alerts` channel (`portal-alerts` for this pilot). These are desired
  names, not resolved native IDs or membership grants. Shared-team membership
  never grants access to a private channel; native system administration remains
  an explicit recovery exception, not a tenant role.
- Tenant viewers can see channel alerts only, with no other direct notifications.
  Adapter-specific recipients/permissions must enforce that rule; listing a group
  here does not grant it ntfy subscription or native administration.
- Platform engineers can see all tenant contexts as confirmed for this pilot.
  This does not infer tenant administrative writes or native system-admin roles.
  OpenBao is explicitly outside this effort.
- GitLab desired roles are tenant-admin Owner, tenant-developer Developer, and
  tenant-viewer Reporter. Numeric group/project IDs and live grants remain unresolved. Do not
  derive identity or permissions from display names, email or GitHub ownership.
- Generic future Grafana roles remain Admin/Editor/Viewer in the inactive contract.
  The separately reviewed current Portal `log_view_only` profile overrides all
  three to Viewer; it does not activate generic org-admin rights. Server-side
  query isolation and exact native mappings are required. Dashboard/folder/label
  filters do not establish that isolation.

No roles, memberships, credentials, app selection or Flux roots change by merging
this contract. Existing admin-only clients and independent recovery remain intact.

## Lifecycle and enforcement ownership

Keycloak owns human identity and group membership; each native service still owns
its authorization. Use exact subject UUIDs and explicit context mappings, not
email-based account linking. Reconciliation must detect replacement IDs, extra
memberships and inherited access and stop on unexplained ownership drift.
Native revocation/session tests must accompany admission tests. Group removal
alone must not be reported as completed offboarding while app sessions, tokens,
private channels, project memberships or topic credentials still permit access.
Revocation is complete only after native readback and negative access checks;
partial failure is actionable, never silent success.

Configuration remains Ansible/YAML. Subsequent adapters must default off and keep
API writes, credentials and security-sensitive changes behind their applicable
approval gates. This contract deliberately contains no live apply path. Native
role permissions not already confirmed are decisions for the platform owner,
not assumptions to encode because an app supplies a convenient default role.

## Supported lifecycle definition

[Provision, update, revoke, drift and native entitlement ownership](lifecycle.md)
defines the supported operator-driven pattern for #16. It distinguishes current
Portal overrides from inactive generic defaults and #43/#334 live acceptance.
