# Authorization review — disabled, not deployed

Start with the [role-by-application matrix](MATRIX.md) and the zoomable C4
`authorization_review`, `authorization_roles`, `authorization_core_apps`,
`authorization_observability`, `authorization_collaboration` and
`authorization_tenant_apps` views. They separate confirmed intent, implemented
review rendering, existing pilot evidence and unimplemented integration mechanics.

**Merging does not configure a realm, create users/credentials, apply Kubernetes
or OpenBao grants, enable clients, or extend SSO.** Nothing in this folder is
selected by the platform root or existing API configurators. Live realm/tenant
migration and new app integration wiring remain incomplete.

## Review contract and current implementation

One PerkForge realm (`perkforge`) holds shared identities. Five canonical role
groups are proposed: `/platform/admins`, `/platform/viewers`, and tenant-qualified
`/tenants/<id>/{admins,developers,viewers}`. Multi-tenant memberships intentionally
grant their explicit scopes; parent groups grant nothing. Use separate clients
for supported platform/tenant apps, not one shared client or blanket realm roles.
Protocol/edition exceptions and client-specific claim disclosure remain decisions.

`desired.yaml` and Ansible/Jinja implement nonsecret **offline review artifacts**:

- `realm.yaml`: groups and only the three existing disabled client specimens
  (Headlamp, Rancher, OpenBao). No users, members, passwords, client secrets or
  realm-management grants. The all-app client inventory is design in the matrix,
  not fabricated clients for unsupported protocols.
- `kubernetes.yaml`: explicit platform-admin cluster-admin trust, a separate
  read-only platform-viewer role and per-tenant admin/developer/viewer examples.
  TD can read/list own Secret values and manage listed deployment resources but
  cannot mutate Secrets, RBAC or SAs or exec. TV has workload/status reads without
  Secret API/exec. **The platform-admin cluster-admin binding can bypass tenant
  privacy**; no deny rule or admission isolation is claimed against that actor.
- `openbao-roles.yaml`: exact OIDC group-bound roles with default policy disabled,
  platform KV values editable by PA, tenant names discoverable by PA, own tenant
  values managed by TA/read by TD, and proposed metadata-only viewer examples.
  No global `*`/sudo, standing tenant data read for PA, or auth/policy self-grant.
  LIST metadata, READ metadata and READ data are distinct. Proposed mount layout,
  helper endpoints, consent/elevation, retention and migration still need review.

The prior broad OpenBao administrative wildcard and developer-no-secret-read
specimens are superseded by the confirmed intent above. App policy does not
promise absolute privacy against cluster/identity/storage/backup administrators.
Tenant-approved grants and accountable emergency elevation are not implemented.

No changes are made to existing app deployments or proven pilot API owners:
Headlamp OIDC/group-to-Kubernetes patterns, OpenBao claim-bound roles/policies and
Rancher's default-off configurator remain reusable evidence. Their current physical
integration is not inferred. Helm deploys applications; Ansible owns separately
reviewed realm and native app API configuration. Never run competing import/API
owners. The existing OpenBao configurator additionally requires the independent
`platform_api_apply=true` gate; new review artifacts are not wired into it.

## Render locally, never apply

`preview.yaml` defaults to no writes and never authenticates or reads credentials.
Check mode also writes nothing. It **refuses** `authorization_apply=true` or enabled
integrations. Explicit render needs a fresh absolute output directory; existing
output is never overwritten. Output directory 0700/files 0600; no secret values.

```sh
ansible-playbook -i localhost, big-bang-bootstrap/configuration/authorization/preview.yaml
ansible-playbook -i localhost, big-bang-bootstrap/configuration/authorization/preview.yaml --check
```

To review synthetic tenants, supply `authorization_render=true`, a fresh protected
`authorization_output_directory` and explicit `authorization_tenants` using a
nonsecret YAML vars file. These are proposed representations, not approved import
payloads. Never run kubectl/app API apply against the generated review files.

## Everyday access and independent recovery

Everyday operator access is intended through Keycloak platform-admin SSO. Durable
local break-glass credentials belong in the operator password manager, independent
of Keycloak/cluster custody. Test supported local emergency access with SSO
unavailable. An app still needs its service/data to be available: off-cluster
custody is not a claim that login works during total cluster failure.

Temporary app flat files are at `~/src/perkforge-tmp-secrets/`, outside Git,
directory 0700/files 0600. Future approved app credential capture uses that path.
The operator owns password-manager migration and explicit temporary-copy cleanup.
Moving files is not rotation. Bootstrap root tokens, temporary master admins and
bootstrap passwords are not automatically permanent recovery identities. Review
per-app replacement/revocation separately; never remove the only tested recovery
path. CA signing, OpenBao unseal and SSH material stay outside this generic cache.

## Small implementation and acceptance stages

1. Resolve the fixed Keycloak image and stage-gated immutable release; initial
   app/local-admin access, trusted TLS and custody are separate approvals.
2. Review the matrix, exact realm/shared-user ownership, per-client claims and
   native app permissions. A tenant membership manager must not reset/delete a
   shared identity or assign an unapproved role. FGAP/API mechanics remain open.
3. Use small per-app MRs for idempotent read/compare/conflict refusal, approved
   credential references and explicit migration/revocation. No giant all-app apply.
4. Separately approve each change; verify positive and negative API/app identities,
   multi-tenant memberships, cross-app token replay, malicious workload/mapper
   attempts, cross-tenant queries and membership removal/session expiry.
5. Test independent recovery and retire temporary access only under explicit
   approval. Save safe evidence automatically and update C4 from proposed to
   observed only when evidence exists. Never equate login with authorization proof.

Offline tests render two synthetic tenants and model exact allow/deny rules;
preserved synthetic API tests cover create/idempotence/conflict/redaction. They
are not live authorizer, admission, OpenBao capability, app-login or data-isolation
acceptance. See matrix [primary guidance](MATRIX.md#primary-guidance-used-for-this-review).
