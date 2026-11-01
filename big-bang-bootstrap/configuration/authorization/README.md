# Authorization review — disabled, not deployed

Review after Keycloak is installed and initial local/break-glass access works.
This draft preserves proven pilot patterns while proposing the requested platform
and tenant roles. **Merging does not configure a realm, create users/credentials,
apply Kubernetes grants, enable clients or extend live SSO.** Nothing in this
folder is selected by the platform root or existing API configurators.

`desired.yaml` is the review contract; `preview.yaml` uses Ansible/YAML templates
to render a fresh owner-only local review directory only on explicit render.
Default/check mode calls no APIs, reads no secrets and writes no files. It refuses
`authorization_apply=true` and enabled integrations: this is intentionally not a
new live apply framework. The review artifacts are valid proposed representations,
not an approved import or a claim migration is implemented. Use existing Ansible
Admin API owners to implement reviewed, idempotent changes after approval;
Helm/Big Bang only deploys Keycloak. Never run both realm import and API ownership.

## Who does what and why

| Role label / canonical group | Intended effective authority |
|---|---|
| platform-admin → `/platform/admins` | Explicit Kubernetes cluster-admin, Rancher platform admin and proposed OpenBao administrative policy. This is broad infrastructure trust, not least privilege. It does **not** automatically grant Keycloak master/realm administration or provide OpenBao root/unseal material. |
| tenant-admin → `/tenants/<id>/admins` | One `tenant-<id>` namespace's workloads, data Secrets, service accounts, PVCs and pod exec/log/forward. No cross-tenant/cluster resources, namespace/PSA mutation, role/binding management, bind/escalate, impersonation, TokenRequest or storage-class/PV administration. |
| tenant-developer → `/tenants/<id>/developers` | Deployments/scale management, read workload status/services/events and pod logs. No direct Secret/SA/token, exec/forward, RBAC, namespace or storage administration. |

Parents `/platform`, `/tenants` and `/tenants/<id>` grant nothing. Do not create one
global tenant-admin group bound into every namespace. Membership in two explicit
tenants intentionally grants those two scopes; removal must revoke the intended
membership without silently deleting others. The old `/platform/developers`
observer pilot is preserved, not silently promoted to the new tenant-developer.
No users, default memberships, password resets or realm-management mappings are
included. Keep realm administration a separate reviewed identity responsibility.

**RBAC is necessary but insufficient for workload isolation.** Editing a Deployment
can run code that uses its pod's service account or mounts namespace Secrets, even
without direct Secret/token read permission. Before activating these grants,
review/enforce admission against privileged/host namespaces, hostPath, node and
runtime bypasses, unapproved service accounts and credential mounts; enforce
Restricted Pod Security, rejection of legacy service-account-token Secrets,
restricted PVC prebinding/storage-class selection, protected platform
policies/network boundaries, quotas
and approved workload identities. Do not place privileged SAs or platform secrets
inside tenant namespaces. Tenant-admin's explicit Secret/SA/exec authority is
powerful inside its namespace; do not pretend it provides isolation from its own
workloads. Developer logs may also contain app secrets; application redaction is
part of the trust boundary. The draft does not implement or prove those admission
controls, so namespace grants are **not activation-ready**.

## Per-app feasibility and protected inputs

| App | Proposed mapping / prerequisite |
|---|---|
| Headlamp | Reuse retained `packages/headlamp/oidc.yaml` and proven group/RBAC pattern. Native OIDC client `headlamp-local`; API server must independently trust exact issuer/audience, `sub` username and full-path `groups` with `oidc:` prefix. An issuer/API configuration change can restart the single control plane: separate maintenance approval. UI config alone does not enable API identity. Tenants use Headlamp; no tenant kubeconfigs are required. |
| Rancher | Reuse default-off Generic OIDC configurator with `required` access and only `/platform/admins` → existing admin GlobalRole. Retain local admin/recovery. No tenant access, Keycloak realm-admin grant or Fleet GitOps ownership. Verify actual token/userinfo group identifiers and callback; do not assume every mapper/PKCE setting from another client works. Rancher PKCE enforcement is left unresolved rather than blindly required. |
| OpenBao | Reuse proven exact `bound_claims.groups` role → ACL policy pattern. Review adds `groups_claim` for optional Identity aliases, but merely setting that claim does not create aliases/policies. Proposed broad platform policy is deliberately more powerful than the old KV-only pilot; explicit review required. Tenant admins get only their `tenants/data/<id>/*` and metadata paths; no sys/auth/policy/root access. Developers receive no human secret policy by default. OpenBao authentication/ACLs are not Kubernetes RBAC. |
| Longhorn | No native username/password, OIDC client or fine-grained group RBAC. Keep ingress off. Review a verified Rancher proxy path or external authenticated admin proxy, admitting platform-admin only; never treat it as internal tenant authorization. Proxy product/access method remains a decision; no fake Longhorn client is rendered. |

`realm.yaml.j2` proposes PerkForge display name with canonical `perkforge` issuer,
full-path groups and **disabled** confidential clients. No secrets are embedded.
Headlamp/OpenBao use the proven S256 pattern. Client audiences, allowed redirects,
CA trust, token/userinfo contents and each pinned app's actual support require
verification before enabling. A full-path membership mapper can disclose other
tenant memberships to a client; select and test an appropriate client-specific
claims strategy before use—no invented Keycloak regex/filter capability.
Do not paste tutorial sample realm/cluster-admin mappings as universal defaults.

`openbao-roles.yaml.j2` shows claim-bound roles and policy bodies, not an applied
auth mount. Platform administrative `sudo` is intentionally broad but cannot
replace root-only recovery operations. Reviewer must approve policy scope and
future Identity alias strategy. The existing configurator now additionally
requires `platform_api_apply=true`; default/check mode does not authenticate.

## Ordered review, migration and acceptance

1. Verify initial app/local-admin access, trusted TLS and independent recovery.
   Operator migrates the temporary localhost credential cache to proper custody;
   this draft does not read, migrate, delete or rotate it.
2. Review roles, explicit tenant IDs/namespaces, workload/secret/admission boundaries,
   client claims, OpenBao administrative policy and Longhorn proxy decision.
3. Render nonsecret examples with Ansible and inspect the diff. Never import this
   new-realm representation over an existing realm. Confirm ownership, existing
   memberships/default roles/composites and app bindings; unowned/conflicting
   objects must stop migration. Use idempotent read/compare/API operations with
   explicit revocation, not delete/reimport or competing reconcilers.
4. Separately approve the concrete realm/client/group/credential/API-server/app
   changes and deploy prerequisites in dependency order. Create no test users or
   client credentials until that scope and custody are approved. Preserve local
   break-glass paths until fresh SSO tests pass.
5. Test positive/negative identities: platform admin, tenant A admin/developer,
   tenant B equivalents, ungranted user and similarly named group. Verify cross-
   tenant denial, cluster/RBAC/Secret/SA/token/exec limits, issuer/audience/signature,
   inherited/default-role leakage and admission rejection of malicious PodSpecs.
   Verify real Headlamp access, OpenBao capabilities and Rancher platform-only
   access—not merely a successful browser login or group claim.
6. Revoke one grant, expire/revoke sessions/tokens as each app supports, and retest.
   Group removal may not invalidate existing tokens immediately. Retain independent
   recovery; approve retirement of temporary access and protected cache separately.
   Save redacted results automatically and update C4 from proposed to observed.

Offline tests render two synthetic tenant namespaces and model allow/deny rules;
existing real-Ansible synthetic API tests retain create/idempotence/conflict and
redaction coverage. These are not live authorizer, admission, token or app-login
acceptance. No new mandatory rehearsal framework is introduced.

Sources: [Keycloak admin model](https://www.keycloak.org/docs/latest/server_admin/),
[Headlamp OIDC](https://headlamp.dev/docs/latest/installation/in-cluster/oidc/),
[OpenBao OIDC roles](https://openbao.org/docs/api/auth/jwt/),
[Kubernetes RBAC escalation/bind](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#restrictions-on-role-creation-or-update),
[Kubernetes RBAC workload risks](https://kubernetes.io/docs/concepts/security/rbac-good-practices/).
