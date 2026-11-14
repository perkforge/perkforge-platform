# Canonical Keycloak context snapshot (source-only)

`read-keycloak-context.py --read TOKEN FRESH_RECEIPT INPUTS.json` performs GETs
only. Bare/default is inert; `--validate` performs no authentication or writes.
It is not an account provisioner, Keycloak policy manager or membership writer.

- The explicit selected context is bound to the existing platform-owned context
  document by SHA256. Only Keycloak realm/group paths and GitLab role mappings are
  consumed. This is group-to-GitLab-role policy, not proof of a conjunction with
  generic realm-role claims. Role fields filtered by native caller visibility
  cannot prove absence. Unrelated old Grafana/Mattermost activation fields are
  not authority.
- Protected inputs supply exact native leaf IDs, never a search by user email or
  an inferred app-folder tenant. Live group IDs/paths and absence of nested groups
  must match; membership is bounded to 500 per role and duplicate/conflicting
  role assignments fail closed rather than silently selecting higher privilege.
- Two complete reads must agree. Output retains only immutable subjects, enabled
  flags, canonical roles, exact group bindings and provenance/timestamp. Native
  usernames/emails are deliberately discarded. Two reads are not an atomic
  database snapshot or continuous membership synchronization. Pinned
  `getMembers` checks group-level view-members and then returns the direct member
  stream without additional per-user authorization filtering.
- A fresh private receipt is exclusively reserved; API/parse/drift failure removes
  only the owned incomplete receipt. Existing successful receipts are not reused
  or overwritten. Caller must impose an overall process deadline and treat any
  nonzero/expired invocation as unavailable, never as an empty desired roster.

## Actual authority and activation gate

Pinned Keycloak26.8.1 `GroupResource.getMembers` requires view-members on the
selected group. Both FGAP evaluators support specific-group permission; broad
realm view-users/manage-users bypass that fine-grained boundary. Do not call a
wrapper-selected request list an RBAC restriction. Runtime requires a dedicated
service identity with exact view and view-members permissions for the canonical
leaves, no broad realm roles, and verified foreign-group/write denial.

Current live inspection on 2026-11-14 found PerkForge realm fine-grained admin
permissions disabled (`adminPermissionsEnabled=false`) and no permissions client;
legacy group management-permissions reads returned501. No narrow reader is
configured yet. Enabling and configuring it is a separate reviewed security
change. This helper must not be activated with the existing bootstrap admin just
to work around that missing boundary.

Source references: official Keycloak tag26.8.1, services/resources/admin/
`GroupResource.java`, `fgap/GroupPermissions.java` and `GroupPermissionsV2.java`.

## Phase contract, not an installed orchestration

1. Verified explicit enrollment revision selects a canonical context; the group
   foundation returns GroupReady only after this invocation's native readback.
2. The isolated identity stage reads a fresh canonical snapshot and resolves each
   immutable subject with the separate GitLab read-only attestor. Missing users
   remain PendingFirstLogin; blocked users remain PendingAccountApproval. No
   auto-approval, email linking or new human accounts.
3. Only issuer-owned, revision/contract-bound fresh receipts may cross to the
   writer. Exact named ConfigMap custody plus admission/RBAC must prevent a caller
   from supplying self-attested JSON. Neither admin-reader credential crosses.
4. Writer grants require current canonical entitlement and fresh exact identity;
   removals require protected owned prior grant receipts and a complete current
   snapshot. Snapshot failure, truncation or ambiguous roles authorizes no removals.
   Large/empty roster changes require an explicit reviewed change plan, not blind
   absence-driven mass revocation.
5. MembershipReady follows native writer readback, not GroupReady, identity-only
   success or generic JobComplete. Role changes remain PendingRoleChange until a
   reviewed transition exists. Arbitrary Keycloak changes do not yet trigger this
   revision-based path; the ongoing-sync follow-up remains separate.

No executable multi-phase orchestration or issuer-only receipt transport is
claimed by this source. Native reader grants, runtime/image selection, phase
retry/status delivery, negative acceptance and the Portal project/event path
remain open #334 integration gates.
