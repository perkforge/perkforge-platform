# Full PerkForge realm administration — source proposal

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
26.8.1 role set; each must be noncomposite and belong to the same PerkForge
management client. Extra/missing/nested/cross-client/cross-realm children refuse
before writes. A future upgrade changing that expansion requires review.

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
exact built-in composite identity and its bounded expansion. Only the missing
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
