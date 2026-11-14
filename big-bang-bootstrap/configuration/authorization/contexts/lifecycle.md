# Supported tenant identity lifecycle

This is the #16 **definition**, not a universal reconciliation service or proof of
all live #43 cases. The supported pattern is a serialized, reviewed operator change:
platform-owned intent → exact identity/native-ID inspection → bounded native
adapters → readback and denial evidence. SSO authenticates; each service still
owns its sessions, credentials and authorization. No paid automatic group sync is
assumed. No new daemon, datastore, credential authority or live grant is added here.

## One authoritative entitlement map

`portal.yaml` owns desired context identity, role paths, runtime/control namespaces,
apps and destination names. `verify.py` rejects ambiguous or cross-context inputs.
The published platform enrollment supplies actual namespace ownership, not a tenant
label or an application's claims. Resolve and bind immutable IDs in an operator's
private reviewed receipt; names alone, an email match or a well-formed UUID are not
ownership evidence. Pin the intent and native evidence to the same change revision.

| Boundary | Authoritative intent and native binding | Admission / revocation |
|---|---|---|
| Keycloak | Verified issuer/realm, immutable subject, exact `/tenants/<context>/{admins,developers,viewers}` group UUIDs; generic noncomposite tenant roles mapped to those groups | Generic role **and exact context group**; remove only selected membership, invalidate applicable IdP sessions/tokens, verify newly issued claims. Never infer admin B from admin A + viewer B |
| Runtime apps / Kubernetes | Enrollment's exact runtime namespaces, namespace UID and ownership epoch; control namespaces separate | App-specific authorization, never a blanket Kubernetes grant. Portal runtime only; config/release namespaces excluded. Unknown/shared namespaces platform-only |
| Grafana / Loki | Exact org ID, client-owned entitlement, org-local read-only datasource identity, fixed gateway scope and immutable namespace epoch | Current Portal override maps **all three roles to Viewer**, PA independent, PE org1 Viewer. Remove affected org membership and native sessions/tokens before transfer; no login-only revocation assumption |
| Mattermost | Shared `perkforge` team, private context channel ID, exact subject-bound native user ID | Ordinary member roles, approved canonical recipients and PE visibility; remove exact channel membership, preserve other contexts. Shared team membership is not private-channel access; recovery system-admin exception remains explicit |
| ntfy | Exact context topic and separate scoped publisher/subscriber identities | Tenant admins/developers direct alerts only when explicitly enrolled; viewers Mattermost-only. Remove topic ACL and relevant tokens before declaring revocation; do not rotate shared unrelated identities implicitly |
| GitLab | Private exact numeric group/project IDs, provider/subject-bound native user ID; Owner/Developer/Reporter desired roles | Inspect inherited and direct membership. Remove selected grant and separately review descendant/project grants, sessions, PATs and automation credentials; native group removal alone is not full offboarding |

The context's generic Grafana Admin/Editor/Viewer table is an **inactive future
capability**, not current Portal authority. The reviewed `log_view_only` profile is
the explicit current override. Native org Admin can invite existing accounts;
do not activate that generic capability under a claim that Keycloak alone owns
membership. Snapshots/public dashboards are globally disabled by the owner-selected
private-sharing profile; ordinary authenticated viewing remains available.

GitLab IDs intentionally remain unresolved in the generic contract. An approved
native inspection must bind actual IDs before any project grant. Do not invent IDs
or infer them from Portal's GitHub repositories. That is a fail-closed execution
prerequisite for #334, not an unspecified role-policy decision.

## Provision / admit

1. Review a source change to enrollment/context and the selected native capability
   profile. Establish namespace ownership and target IDs, exact realm/client scopes,
   group ancestry, direct/composite/inherited grants, and recovery exceptions.
   Treat existing unmatched objects as drift, not automatic adoption.
2. Establish only missing approved canonical foundation and noncomposite mappings
   with the existing bounded adapters. Never rerun the empty-realm initializer over
   populated groups. No human account creation, linking or membership is implied.
3. Verify each intended existing subject and authorize its exact role/context.
   Provision app boundary/credential scope before admitting users. Runtime secrets
   belong in OpenBao/ESO; independent recovery credentials remain in Bitwarden.
4. Apply only the reviewed per-app diff, re-read ownership before each write and
   after completion, then prove permitted access and foreign-context denial. Keep
   failed/unsupported integrations closed; do not report all-app success from SSO.

## Update / change role or ownership

Serialize identity operations; receipts are evidence, not a lock or authorization.
Re-read current IDs and memberships immediately before applying a reviewed diff.
Downgrades and ownership transfers revoke old access first, including independently
usable sessions/tokens. Never reuse a log ownership epoch for a new tenant. Retain
historical logs under their old authorized scope; handling/deletion needs a separate
policy. Only admit new ownership after denial of old access is verified.

An ordinary upgrade is an explicit native-role change, not a new platform role.
Preserve unrelated contexts: Admin A + Viewer B must remain Viewer B. Source
renames are not permission to adopt a replacement UUID or move an account by email.
Re-plan after concurrent changes; partial application is not transactional success.

## Deprovision / revoke

Disable new admission for the affected subject/context, remove its canonical grant,
and coordinate IdP session/token invalidation. Revoke native app membership and
credentials from the table above, then verify using prior authenticated sessions
where authorized. Preserve unaffected contexts and independent recovery.

A removed Keycloak group is **not** complete offboarding while Grafana sessions,
Mattermost channel membership, ntfy credentials, or GitLab grants/tokens remain.
If a native step fails, record the exact residual access, keep new admission closed,
and fix forward from fresh state. Do not delete users, tenant storage, backups,
logs or shared teams as a side effect of access revocation. Account deletion and
retention are separate owner decisions, not prerequisites for revoking access.

## Drift and audit

Before and after each change compare desired exact IDs/roles with native direct
and effective inherited grants. Unexpected composite roles, default/optional scope
mappers, ancestor authority, extra members, changed native ownership, incomplete
pagination or failed reads are blockers, not empty authoritative lists. Never
silently prune unowned state. Have the owner review adoption/removal where needed.

Retain a private sanitized receipt: source revision, target IDs, actor/approval,
intended diff, timestamps, pre/post evidence, successful steps, residual failures
and negative checks. No raw tokens, passwords, webhook URLs or log bodies. Retrying
must inspect first, preserve successful changes, and apply only the still-approved
missing diff. No continuous drift detection or immediate event-driven revocation
is claimed; schedule/daemon authority is a separate implementation choice.

## Existing implementations and acceptance boundary

- [Generic group-role mapping](../PORTAL-ROLES.md): guarded additive foundation;
  no human membership changes, no extra-parent/composite authority adoption.
- [Grafana native adapters and revocation](../sso/grafana/orgs/README.md) and
  [reviewed access design](../sso/grafana/orgs/access-design.md): own-client scope
  guards, org mapping, pinned native login/session fixtures and live machine probes.
- [Mattermost bounded plan/apply](../sso/mattermost/context/README.md): exact
  identities, approved add/remove list, pre/post-authority readback, removal-first;
  not a scheduled universal synchronizer.
- [GitLab inspection](../../packages/gitlab/context.md) and
  [native membership adapter](../../packages/gitlab/reconcile-membership.yaml):
  edition-supported explicit operations; full token/session offboarding separate.
- [Notification scope](../../packages/gitlab/events/README.md): destinations derive
  from reviewed context, never event payload overrides or raw sensitive content.

| #16 criterion | Defined outcome / evidence |
|---|---|
| Supported provision, update, deprovision | Serialized inspect/apply/readback procedures above; bounded existing adapters, residual-failure handling and separate data retention |
| Detect and handle drift | Exact ownership/effective-authority checks before/after each operation; reject incomplete reads and unexplained drift, reviewed remediation rather than silent adoption |
| Preserve tenant roles/groups | Generic role plus exact context, immutable subjects/IDs, cross-context downgrade tests, independent PA/PE and explicit recovery exceptions |
| One authoritative cross-app entitlement map | Context/enrollment inputs and native-binding table above; explicit Portal Viewer override, shared private Mattermost channels and unresolved GitLab IDs fail closed |

Acceptance of this definition does not claim a deployed continuous controller,
customer self-service CRUD, fresh human tests for every role/app, or complete live
offboarding. Those implementation/evidence items remain #43/#334 and the Portal
CRUD issue. No additional policy choice is needed to document this operator-driven
pattern; future automation and broader native admin rights require their own scope.
