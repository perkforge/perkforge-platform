# Full PerkForge realm administration — mapping applied; rerun blocked

The user explicitly clarified full authority over everything within PerkForge,
not only users/clients. This supersedes the earlier `realm_admin: false` intent
for platform-admin. `desired.yaml` now records `realm_admin: true` and
`master_admin: false` for PA only; other roles stay unchanged. These are reviewed
intent flags, not an activation mechanism. The preview template still emits no
realm-management grant, and no existing workflow invokes this operation.

## Exact scope

Map **perkforge realm → realm-management client → realm-admin** to the exact
owned **/platform/admins leaf**. This one built-in composite includes full realm
administration: users, groups, roles, clients/scopes, identity providers,
authentication flows, realm settings, events, authorization and organizations.
**It includes impersonation.** Credential resets, group/role mapping, client
secrets/redirects/service accounts and authentication policies are trusted PA
powers, not tenant isolation or a privacy boundary against administrators.

This does **not** grant access to master or other realms, broker master login,
create a master identity, or retire independent recovery. Master authentication
is used privately by Ansible solely as the existing configuration-owner
credential. No role is placed on `/platform`, defaults, other platform/tenant
groups, or individuals. Application-specific Headlamp/Kubernetes/OpenBao/Rancher
permissions and SSO are separate; realm authority can influence app identities,
so it is powerful even without direct app mappings.

The previously prepared five-role users/clients subset was never applied. It is
not the revised grant, and existing explicit child-role mappings cause refusal
rather than automatic replacement/deletion. The approved intent is one exact
composite. Its 21 expected built-in children are pinned to the reviewed Keycloak
26.8.1 role set; the complete 22-role catalog must belong to the same PerkForge management
client. Keycloak 26.8.1 legitimately nests `view-users` → `query-users`,
`query-groups`; `view-clients` → `query-clients`; and `view-organizations` →
`query-organizations`. Each canonical role's name/ID/client/composite flag and
every immediate edge (including empty leaf edges) must match that bounded DAG.
Its transitive closure is exactly the root plus the 21 reviewed roles, with IDs
deduplicated. Unexpected/missing edges, cycles, replaced IDs or cross-client/
cross-realm references refuse before writes. A future upgrade changing that expansion requires review.

## Owner and approval gates

Ansible/YAML owns native API mappings; Big Bang/Helm owns deployment. No automatic
Flux execution. `administer-perkforge.yaml` defaults off. Default and check mode
never contact APIs or read credentials. Publication/merge does not authorize a
live grant. Approve the exact full realm scope including impersonation,
parent/admin UUIDs, physical UID, trusted CA/endpoint and independent recovery
custody before apply. Use a private vars file with references only:

```yaml
perkforge_admin_apply: true
perkforge_admin_scope: perkforge-full-realm-admin-v1
perkforge_admin_recovery_preserved: true
perkforge_admin_group_id: REVIEWED-EXISTING-ADMIN-UUID
perkforge_admin_parent_id: REVIEWED-EXISTING-PARENT-UUID
perkforge_admin_ca: /PRIVATE/EXISTING-CA
perkforge_admin_username_file: /PRIVATE/EXISTING-MASTER-USERNAME
perkforge_admin_password_file: /PRIVATE/EXISTING-MASTER-PASSWORD
target_kubeconfig: /PRIVATE/EXISTING-PHYSICAL-KUBECONFIG
target_context: REVIEWED-PHYSICAL-CONTEXT
expected_cluster_uid: REVIEWED-KUBE-SYSTEM-UID
```

Use the normal configuration Ansible inventory and reviewed private file only
following separate action approval. GET-only inspection sets apply false and
`perkforge_admin_inspect: true`, retaining scope/recovery/identity gates.
Credential references must be owned nonsymlink regular mode-0600 files; verify
protected parent custody separately. TLS/hostname validation is mandatory;
redirects, proxy and netrc are disabled. Sensitive URI payloads use `no_log`;
no verbose/callback/fact-cache dumps, credential output or inline secrets.

The operation checks physical UID before authenticating, exact realm/group
ownership and UUIDs, no nested admin groups, no default/parent role inheritance,
exact built-in composite identity, bounded canonical catalog and complete role graph. Only the missing
single role mapping is added. Direct and effective readback plus a zero-write
repeat verify representation. An uncertain response is inspected/resumed, never
blindly resubmitted or automatically rolled back. Unexpected grants refuse
without deletion/adoption. No users, client definitions, credentials, policies,
MFA flows or master settings are changed by the operation itself; the delegated
administrator will have authority to change PerkForge settings after activation.
Withdrawal needs separately reviewed removal and session/token revocation.

The older foundation/enrollment workflows intentionally require empty group
mappings and refuse after delegation. Do not weaken these pre-delegation guards
to force a repeat. Use this play's inspection path; future enrollment lifecycle
work must explicitly account for full PA authority.

## Acceptance and console

Realm console:
`https://keycloak.perkforge.home.arpa/auth/admin/perkforge/console/`.
The account console `/auth/realms/perkforge/account/` only manages one's profile.
Master console/recovery is separate; no master delegation is implemented.

Real-Ansible synthetic HTTPS fixtures cover defaults/check gates, the single
composite and complete effective expansion, idempotence/inspection, uncertain
write resume, ownership/default/parent/nested-group refusal, unexpected direct
roles and composite drift (including master/other-client roles), scope/target/
TLS/auth/private-file refusal and log redaction. These are not live browser or
permission-denial proof. Effective mapping semantics follow the Keycloak 26.8.1
Admin API, including the root composite plus its expanded children.

After independent live approval, the operator uses fresh MFA to verify full
PerkForge console controls, including realm/authentication settings and explicit
impersonation capability. Any write tests use disposable reviewed objects and a
separate cleanup plan; never reset real people or weaken MFA as a casual test.
Negative acceptance verifies master/other-realm denial and ungranted engineer,
viewer and tenant denial. Preserve independent recovery and verify it before/
after. No live acceptance or credentials/SSO deployment is claimed here.

References: [Keycloak administration](https://www.keycloak.org/docs/latest/server_admin/index.html),
[26.8.1 effective client-role mappings](https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/services/resources/admin/ClientRoleMappingsResource.java).

## Current correction checkpoint — no grant

#135 merged the intended full-realm operation, but GET-only preparation found a
fixture mismatch: the old guard required all root children to be noncomposite.
Actual Keycloak 26.8.1 and upstream `RealmManager.addQueryCompositeRoles` both
contain the three nested view composites above. The merged guard would safely
refuse them. Parent/admin group mappings remain empty; no role grant was made.

The correction resolves canonical IDs from a bounded `roles?first=0&max=23`
catalog and requires exactly the reviewed 22 roles, preventing truncated-page
acceptance. It queries edges on all 22 nodes and verifies every target's exact
name/ID/client/composite flag. The exact DAG permits the legitimate nesting but
not arbitrary nested or cyclic authority. Existing direct/effective mapping and
post-write identity checks remain. Fixtures model the real flags, edges and
deduplicated effective closure; no real IDs or raw private evidence are copied.
The corrected play also passed forced inspect-only execution against the actual
service (35 tasks, changed=0, failed=0): target/file/ownership/catalog/graph guards
accepted the real responses, while parent/admin mappings stayed empty. This is
GET-only pre-write validation, not live grant, delegated login or post-grant
idempotence evidence. Source correction and live approval are separate; live
application stays on hold.

Upstream edge definition: [Keycloak 26.8.1 RealmManager](https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/services/managers/RealmManager.java).

The strengthened real-Ansible fixture set takes 237.567s locally versus 112.260s
for the old assumptions. Hosted baseline selection already took 18m42s under a
20-minute job cap. The correction raises only that offline job budget to 30
minutes; it preserves every test, timeout inside individual operations, and all
release/live-approval boundaries. No test is skipped to hide the mismatch.

## Applied mapping and remaining rerun guard

The separately approved corrected #136 operation applied one mapping (37 ok,
changed 1, failed 0). Independent direct/effective readback confirms realm-admin
only and exactly 22 canonical roles. Non-target/master/other-realm group mappings,
master verifier mappings/access, realm security settings, role definitions/edges
and node/Keycloak health were preserved. No human authentication, extra identities,
credential resets or other app grants occurred.

The normal second run made no changes but failed (11 ok, changed 0, failed 1):
`group-by-path` now includes the intended `clientRoles` representation, while the
early guard still requires that field empty. This is a remaining API fixture/
representation mismatch, not an unwanted role grant. Preserve the correct grant;
do not bypass or remove it. Successful idempotence is NOT claimed. The follow-up
must recognize only the exact intended representation while retaining independent
UUID/client/direct/effective checks and rejection of every unrelated role.

The owner reports signing out, signing back in with MFA and seeing the expected
Keycloak console access. This is user-reported fresh-login/console acceptance,
not automated personal login evidence or proof of every management operation.
Master-denial checks remain an operator action. Current access is active; earlier
source/pre-write checkpoints above are historical. Publication of this correction
and acceptance evidence is separately approved.

## Prepared post-grant representation correction

The local correction accepts only `{}` or
`{realm-management: [realm-admin]}` on the owned admin leaf, then requires that
name-only representation to agree exactly with independent direct-role metadata.
All UUID/client/composite/expanded-role checks remain. Parent and realm-role
representations remain empty; extra roles/clients, fabricated or hidden mappings
and foreign authority refuse. Readback assertions also run in inspect mode when
the existing root mapping is present, so the entire post-grant guard path is
checked without enabling writes.

Fixtures now derive group `realmRoles`/`clientRoles` from direct mappings, matching
real pre/post-grant responses. The merged apply succeeds and its second call
reproduces the failure; the corrected source accepts the same mapped state with
changed=0. Actual corrected GET-only execution passed 38 tasks, changed=0,
failed=0, including all later guards. This is not a new normal merged-source
rerun, and no live write was performed for the correction. Source publication
and subsequent merged-source verification remain separate.

## Merged-source no-change acceptance — 2026-11-02

MR #137 merged as `e7cac52fcc328249de9ef7d704757d6484996b4a`.
Both exact post-merge workflows passed (`41494971414`, `41494971826`), including
configuration/release checks and the release job. The separately approved normal
Ansible invocation from that clean merged checkout passed: **38 ok, changed=0,
failed=0, skipped=1**. This supersedes the historical rerun failure above; no
additional mapping was written. Independent before/after metadata again verified
realm-admin only, exactly 22 effective roles, unchanged non-target/master mappings,
management definitions/edges, realm security and master verifier access. All three
nodes Ready; Keycloak/database Ready with zero restarts. No personal authentication,
credential reset, new identity or application SSO grant occurred. The owner separately
reports fresh MFA console access; not every management operation/master-denial
scenario was tested. Local documentation of this final result is unpublished.

## Explicit SSO coexistence (disabled by default)

After a separately approved app stage, the optional
`perkforge_admin_expected_sso_clients` input records only reviewed headlamp/rancher/
openbao client names, UUIDs and noncomposite app-role UUIDs. The empty default retains
the original refusal of every app role. The play independently checks canonical
ownership, role catalog/edges and exact direct/aggregate role mappings; it never
grants, repairs or removes app roles. Unexpected/foreign/expanded roles still stop.
Remove only the expected entry after that app's completed rollback, then verify
realm-admin repeat changed=0. See [the coordinated procedure](sso/README.md).
