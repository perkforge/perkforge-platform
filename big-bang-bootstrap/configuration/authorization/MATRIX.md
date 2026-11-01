# Role-by-application review matrix

**Design intent and disabled review artifacts, not deployed authorization.**
No app is enabled by this matrix. Existing pilot patterns, offline renders and
current physical evidence are different evidence classes. Integration, migration,
revocation and adversarial acceptance remain separate per-app work and approvals.

## Six roles and shared identity

| Role | Canonical group | Intended scope |
|---|---|---|
| PA: platform-admin | `/platform/admins` | Cluster/platform administration and shared PerkForge user administration; platform secret values read/edit, tenant secret-name discovery only in the nominal OpenBao policy. Tenant value access requires a tenant grant or explicit emergency elevation. |
| PE: platform-engineer | `/platform/engineers` | Everyday platform code/MRs and proposed scoped diagnostics, not inherited PA. No global identity/RBAC/auth-policy or break-glass authority; no automatic platform/tenant secret values. Direct live writes and exact diagnostic scopes remain undecided. |
| PV: platform-viewer | `/platform/viewers` | Read approved platform health/status, no operational changes or secret values; not automatic access to tenant business data/private conversations. |
| TA: tenant-admin | `/tenants/<t>/admins` | Own namespace/apps/secrets and own approved group memberships; no cross-tenant/global account reset/deletion or promotion into platform roles. |
| TD: tenant-developer | `/tenants/<t>/developers` | Own deployment-related resources and standing read/list of own secret values; no secret creation/edit/deletion or permission administration. |
| TV: tenant-viewer | `/tenants/<t>/viewers` | Own status/reports and assigned collaboration channels, no operational changes or secret values. Posting chat in assigned channels is an explicit exception, not infrastructure mutation authority. |

One **PerkForge realm** (`perkforge`) contains shared user identities. Each supported
platform/tenant application has a separate client and audience, including separate
tenant-app instances; authentication protocol/edition exceptions below remain
unresolved rather than fabricated as OIDC clients. A user may hold multiple tenant
memberships; each grants only that explicit scope. Parent groups grant nothing.
No one global tenant-admin group binds every namespace. Claim disclosure must be
client-specific: the existing full-path mapper is a review specimen, not proof
that every app may see every other tenant membership.

Platform-engineer is a distinct role, not an alias for platform-admin or a grant
of all platform-viewer scopes. GitOps is the proposed change path: code/MRs still
need protected branch/owner review, especially identity, permission, credential,
pipeline and controller changes. It must not become self-grant through GitOps.
Exact diagnostic APIs, business-data visibility, secret paths and any direct live
writes remain explicit decisions; the renderer adds **no engineer Kubernetes or
OpenBao grant** while these are unresolved. Tenant portal/Nextcloud access is not
implicitly granted by operating their platform code. Machine/controller identities
and break-glass custody are separate from this human role.

PA's intended cluster/shared-identity power is an **administrative trust boundary**.
Standing Kubernetes cluster-admin can read Secrets or change workloads; identity
administrators may alter membership/reset identities; storage/backup/host operators
may recover data. Nominal app policy cannot guarantee tenant secrecy against
these administrators. Ordinary OpenBao policy intentionally has no tenant value
read or auth/policy self-grant; an accountable elevation design is still open.
Kubernetes Secret LIST returns values, so it cannot implement metadata-only access.
Never represent a cluster-admin binding as enforcing that privacy requirement.

## Core identity and infrastructure applications

Cells describe intended native scope, not grants already applied. A dash means no
standing human access; any additional scope needs review.

| Application | PA | PE | PV | TA | TD | TV |
|---|---|---|---|---|---|---|
| Keycloak | Shared realm user/group administration through reviewed APIs | Own profile; no identity administration | Approved identity audit/status only | Own tenant membership and allowlisted role assignments only | Own profile | Own profile |
| Kubernetes / Headlamp | Cluster administration (powerful bypass caveat above) | Proposed scoped diagnostic reads; GitOps MRs; live writes undecided | Read cluster status; no Secret API/exec | Own namespace resources/secrets; approved workload identities only | Own Deployments/scale, Services, ConfigMaps, Ingresses; own Secret get/list | Own workload/status reads; no Secret API/exec |
| Rancher | Global administration and cluster lifecycle | No default access; scoped diagnostics require review | Reviewed read-only platform role, not admin | —; use Headlamp | — | — |
| OpenBao | Platform KV values CRUD; LIST tenant names, no tenant data read | No default value grant; explicit path/scope decision required | Proposed platform names/status only | Own KV value management | Own KV values read/list, no writes | Proposed own names/status only, no values |
| Longhorn | Platform storage-admin entry only | Proposed metrics/diagnostics only; no storage-admin mutations | No standing UI until a safe read-only method exists | — | — | — |

### Enforcement and unresolved mechanics

- **Keycloak:** PA is not automatically master-realm administration. Shared user
  administration needs a reviewed permission model; TA must not reset/delete a
  user shared with other tenants. Native fine-grained administration versus a
  constrained membership API remains a decision. Test membership creation/removal,
  role-mapper injection, user creation into privileged groups, nested groups,
  cross-tenant users and self-elevation. Resolve the 26.8.0→fixed-image patch before
  delegation; a patched version alone is not authorization proof. Per-app clients
  do not themselves enforce app resource ownership.
- **Headlamp:** the API server independently validates issuer/audience/groups.
  Browser configuration alone does not grant Kubernetes access. Offline examples
  enumerate allowed APIs; no bind/escalate/impersonate, TokenRequest, namespace/PSA
  mutation, cross-tenant resources or exec for TD/TV. Deployment editing can mount
  Secrets/use workload SAs despite RBAC limits: admission, approved identities and
  network/storage boundaries are required. PV/TV status/log access must avoid
  disclosing plaintext secrets; no blanket confidential-data reader is implied.
- **Rancher:** initial local admin remains separate. Existing integration permits
  only PA; PV mapping is proposed and requires a tested read-only custom/global
  role and access restriction update. Never map tenant admins to global admin;
  no tenant Fleet/application ownership.
- **OpenBao:** proposed KV-v2 mounts `platform/` and `tenants/` separate data. LIST
  `tenants/metadata[/...]` discovers names; it is not READ `tenants/data/...`.
  READ metadata can expose custom metadata and version details and is separately
  scoped. Never put secret values in names/custom metadata. PA receives no
  standing `sys/auth`, ACL-policy management, tenant value grant or global `*`/sudo
  policy. Tenant-approved grants/emergency elevation, approvers, expiry, auditing,
  revocation and token lifetime are **not implemented**. UI helper endpoints and
  exact mount migration must be reviewed separately. Root/unseal custody is not
  an ordinary group mapping. Irreversible version destroy/retention is not
  automatically granted by these review examples. PA/TA metadata examples grant
  read/list only, not update/patch/delete; ordinary value writes and current-version
  soft delete use the data endpoint. Engine configuration and destroy endpoints
  receive no grant. Existing engine retention still governs version expiry; this
  is not a promise that writes retain every historical version forever.
- **Longhorn:** no native password/OIDC/fine-grained human RBAC. A verified Rancher
  proxy or authenticated PA-only proxy is a future choice; a proxy entry check
  does not create internal tenant roles. UI ingress stays off. No fake client.

## Observability and collaboration applications

| Application | PA | PE | PV | TA | TD | TV |
|---|---|---|---|---|---|---|
| Grafana | Server administration explicitly approved; platform/tenant organizations | Proposed scoped platform-org Viewer; dashboard MRs, no server admin | Explicit approved org Viewer | Admin of own tenant org, not server admin | Editor of own tenant org | Viewer of own tenant org |
| Mattermost | Explicit System Admin | Ordinary assigned team/channel member; chat allowed | Ordinary member of assigned teams/channels only | Own Team Admin, not System Admin | Assigned team/channel member | Assigned team/channel member; chat allowed |
| GitLab | Explicit instance admin | Developer on approved platform code projects; MRs, not instance admin | Approved read-only membership; no automatic paid Auditor | Owner of own tenant group/projects | Developer in own projects | Reporter/read-only project access as reviewed |
| Harbor | Explicit system administrator | Explicit approved build-project scope only; no all-project administration | Explicit approved projects/read-only role | Project Admin of own private projects | Developer/push-pull in own projects | Guest/pull in own projects |
| SonarQube | Explicit Administer System | Explicit project Browse/analysis scope; no system administration | Browse approved projects | Administer own project, not system | Own project analysis/issue capabilities with scoped CI identity | Browse own project reports |

### Product and isolation gates

- **Grafana OSS:** Generic OAuth org mappings can express org roles; Team Sync is
  Enterprise, not assumed. Every tenant org needs backend-scoped datasources;
  Viewer can query accessible org datasources. Folder/dashboard ACLs are not data
  isolation. Do not make any tenant-admin group resolve to global `Admin` in a
  general role expression: combined role/org mappings can choose the higher role
  and elevate other memberships. Multi-org tests must verify the actual selected
  org and datasource/query boundary, not just rendered dashboards.
- **Mattermost:** pinned 11.11.0 candidate is not proof of current Entry entitlement
  or generic OIDC support. Current Entry/paid offerings and Team Edition differ;
  verify exact image/license terms, including Entry history limits. OIDC group
  claims do not automatically synchronize team roles. Do not assume 12.1-era
  attribute access controls in 11.11. API reconciliation for teams/channels and
  membership removal is separate work. PV is not a reader of all private chats.
- **GitLab 19.4.2, unlicensed Free baseline:** OIDC login is available; OIDC
  membership-derived admin/auditor controls are Premium/Ultimate and do not
  themselves add users to GitLab groups. Do not silently require a paid license.
  Use explicitly reviewed native group/project membership APIs or decide on a
  licensed feature later. Tenant Owner is not instance administrator. CI variables,
  runners/tokens, protected branches and group-owner authority need separate
  secret/permission review; a TD secret-read intent does not bypass product limits.
- **Harbor 2.15.2:** native OIDC groups map to explicit private-project memberships
  and roles. A configured system-admin group must be PA only; tenant groups never
  become system administrators. Robot credentials/CLI secrets are separate machine
  identities. Review database→OIDC migration constraints before creating additional
  local accounts, and test project visibility, push/pull/delete and robot scope.
- **SonarQube Community Build 26.9:** current official Community docs list Keycloak
  SAML, trusted HTTP headers and GitLab/GitHub/etc. authentication, not a generic
  native Keycloak OIDC configuration. The all-app OIDC goal needs an explicit
  supported protocol/proxy/edition decision; no unreviewed plugin or false client.
  Community uses JIT provisioning; application groups/project permissions remain
  explicit. No paid MR/multi-branch analysis promise. Scanner credentials and
  analysis publication may reveal source/issues; they are not viewer credentials.

## Tenant applications and machine/control components

| Component | Human scope and enforcement | State / decision |
|---|---|---|
| PerkForge tenant portal | Own app client/audience; backend checks token and tenant/resource ownership. PA operational administration; TA own app membership/admin; TD own app/deployment role; TV read features. Exact business actions belong to that app. | Existing server verifies issuer/audience/RS256/sub/expiry, `azp`, `tenant-reader` and explicit home/platform groups for tenant listing. It does **not** implement this full six-role management model. |
| Nextcloud tenant example | Native app roles/shares/group administration need tenant-instance boundaries; TA is not shared-server super-admin. TD/TV business file access follows explicit shares, not Kubernetes role names. | Example only; inspect supported OIDC/user backend and edition/version before configuration. No physical deployment or new client claimed. |
| Prometheus / Loki | No ordinary direct tenant admin endpoints. Grafana access must use tenant-scoped query enforcement; names/labels/namespace collection opt-in are not data authorization. | Machine collectors and scoped query/ingest identities; Loki trusted tenant headers/proxy and Prometheus tenant separation remain implementation gates. |
| Alloy | Collector SA/token permissions only; no human role mapped to collector identity. Limit namespace/log discovery, redact secrets and audit collection. | Draft collection scope is not tenant RBAC isolation; no token generation. |
| Alertmanager / ntfy | Approved notification recipients/topics; no public alert mutation or publishing. Separate sending identities from viewers/subscribers. | Native rules retained; Grafana-managed forwarding/ntfy bridge remains off/unimplemented. Supported auth/proxy/topic ACL and secret handling need review. |
| Velero | Explicit platform backup/restore operator scope, separate off-cluster backup credentials; no default tenant-wide restore/delete grant. | Evaluation ticket only; tenant restore must preserve others and coordinate Flux ownership. Backups may contain Secrets; storage encryption/custody/access are separate. |
| Trivy | Scanner/service identity for approved images/reports; human visibility follows Harbor/project policy. | Evaluation only; no global registry credential or scan access granted by a viewer role. |
| Istio / Gateway API | Explicit platform network administration and delegated tenant route controls, with references/listeners/hostnames constrained. | Ticket-only future direction; no new controller, CRD, gateway or route implementation here. |

### Portal evidence and trust flow

Read-only source review at portal commit
[`89f3637`](https://github.com/perkforge/perkforge-portal/tree/89f3637e472802bf4be1ffcf99fea367ebae56e1)
examined [token checks](https://github.com/perkforge/perkforge-portal/blob/89f3637e472802bf4be1ffcf99fea367ebae56e1/server/security.mjs),
[API/BFF routes](https://github.com/perkforge/perkforge-portal/blob/89f3637e472802bf4be1ffcf99fea367ebae56e1/server/app.mjs)
and [authorization tests](https://github.com/perkforge/perkforge-portal/blob/89f3637e472802bf4be1ffcf99fea367ebae56e1/tests/security.test.mjs).
The BFF calls the bearer API; a browser cookie alone does not authorize that API.
Its approved chart fixture supports only `home` or `platform-admins` access policy
and disabled GitLab discovery. Extending shared tenancy, mutations or resource
ownership needs a small app MR and negative API tests; hiding buttons is not an
access boundary. An ID token for another app is not an authorized API access token.

## Who does what and why

1. The operator approves each app's initial admin access and independent recovery.
2. Ansible owns reviewed Keycloak realm/groups/clients and native application API
   configuration; Helm/Big Bang owns deployment, not realm import/membership.
3. Keycloak authenticates shared identities and issues per-client scoped claims;
   each app/API independently validates issuer, audience/client and group mapping.
4. Native app roles and namespace/org/project/tenant ownership enforce resources;
   infrastructure installers/runtime SAs are separate from human identities.
5. Test positive and negative identities, multi-tenant membership, client-specific
   claim disclosure, cross-app token replay, cross-tenant data queries and malicious
   workload/role-mapper changes. Offline RBAC models do not prove these boundaries.
6. Test tenant membership removal, grant expiry, session/token revocation and
   emergency recovery. Keep durable local recovery outside Keycloak/cluster in
   the operator password manager; bootstrap secrets are not automatically durable.

The disabled renderer implements six role-group definitions and bounded Kubernetes/OpenBao
review policies for already specified scopes only. It creates no users, tokens, clients, mounts or
grants. Other per-app mappings above are **design**, not an all-app apply payload.
Initial deployment can proceed app-by-app under separate approval without waiting
for every integration implementation. After foundation patch/stage gating: initial
OpenBao, Headlamp, Keycloak access → realm/groups → one-at-a-time SSO → monitoring →
Harbor/Mattermost/SonarQube/GitLab subject to edition/capacity decisions. This order
is a plan, not deployment authorization or automatic retargeting of stacked MRs.

## Primary guidance used for this review

- [OpenBao KV-v2 API](https://openbao.org/docs/api/secret/kv/kv-v2/) — separate LIST metadata, READ metadata and READ data.
- [Kubernetes RBAC good practices](https://kubernetes.io/docs/concepts/security/rbac-good-practices/) — workload/Secret and administrator bypass risks.
- [Keycloak administration](https://www.keycloak.org/docs/latest/server_admin/) — delegated administration requires version-specific testing, not a generic realm-admin mapping.
- [Headlamp OIDC](https://headlamp.dev/docs/latest/installation/in-cluster/oidc/) — API-server trust is independent of UI configuration.
- [Grafana Generic OAuth](https://grafana.com/docs/grafana/latest/setup-grafana/configure-access/configure-authentication/generic-oauth/) and [security](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/) — org roles, query access and edition distinctions.
- [Mattermost OIDC](https://docs.mattermost.com/administration-guide/onboard/sso-openidconnect) and [offerings](https://docs.mattermost.com/product-overview/editions-and-offerings) — verify pinned edition/version, not latest feature assumptions.
- [GitLab OIDC](https://docs.gitlab.com/administration/auth/oidc/) — login versus paid membership-derived controls.
- [Harbor OIDC](https://goharbor.io/docs/administration/configure-authentication/oidc-auth/) — app-native project role mapping/migration.
- [SonarQube Community authentication](https://docs.sonarsource.com/sonarqube-community-build/instance-administration/authentication/overview) — supported protocols and JIT provisioning.
