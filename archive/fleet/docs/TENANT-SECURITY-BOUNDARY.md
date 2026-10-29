# Tenant security boundary

## Purpose

This document describes the shared-cluster tenant model implemented in the
existing local-lab Fleet workflow. It is a design and evidence record, not a
claim of completed authorization, certification, or production readiness.

The initial test tenants are `tenant-alpha` and `tenant-bravo`. The intended
identity path is Keycloak → Rancher Keycloak OIDC → Rancher Project role
bindings → Kubernetes RBAC. Each tenant receives a Rancher Project and one or
more namespaces. Tenant namespaces carry stable tenant, environment, and
isolation labels used by quota, Pod Security Admission, network policy, and
observability configuration.

## Enforcement layers

| Layer | Intended enforcement | Current evidence/state |
|---|---|---|
| Identity | Keycloak role groups: `/tenants/<tenant>/{admins,developers,viewers}`; OIDC group claim in token | Synthetic Keycloak login and the Alpha viewer's mapped project visibility passed in Playwright; group removal/revocation and session-expiry behavior remain unverified |
| Rancher management | Per-cluster Rancher Project and least-privilege custom project RoleTemplates | Live checks found catalog-owned Projects, RoleTemplates, PRTBs, and namespace associations. Playwright reached Rancher as Alpha viewer, listed Alpha, and received HTTP 403 for Bravo; remaining roles and UI workflows need separate checks |
| Kubernetes authorization | Project role templates translate to scoped Kubernetes RBAC; no tenant cluster-admin bindings | Impersonated-group suite passed 94/94. The browser-issued Alpha viewer could list Alpha pods, could not list Bravo pods, and could not list secrets in either namespace |
| Namespace ownership | Protected tenant/environment labels and Rancher project association | Live quota preflight validated catalog tenant labels, Rancher project association, and reserved allocation for catalog namespaces |
| Network | Default-deny ingress/egress, same-tenant traffic, DNS, and explicit platform exceptions | Live probe suite passed 7/7 same-tenant, cross-tenant, Keycloak discovery, and DNS checks; broader egress/ingress/host paths remain untested |
| Runtime | Pod Security Admission Restricted labels, supplemented by admission policy where needed | Live server-side dry-run passed 9/9 Pod Security Admission cases; this verifies admission decisions, not runtime isolation or shared-kernel behavior |
| Resource governance | Rancher project aggregate quota plus per-namespace ResourceQuota and LimitRange | Live verifier passed 4/4 configuration and CPU/memory admission checks; aggregate project consumption and storage admission remain untested |
| Observability | Tenant/environment labels, kube-state-metrics allowlist, platform-only Prometheus/Grafana, optional OpenCost | Optional monitoring/OpenCost profile is disabled; tenant metric attribution, Grafana authorization, and cost reporting remain unverified |

## CAC authentication and test strategy

The local lab uses synthetic Keycloak identities. This validates group-to-role
mapping and tenant authorization behavior; it does not validate CAC/PIV
authentication or establish IL5 readiness.

For an environment whose approved identity architecture requires CAC, integrate
the approved enterprise identity provider or configure the approved Keycloak
X.509 authentication path as the system boundary requires. Certificate trust,
revocation checking, identity mapping, middleware, and proxy behavior must be
validated in that authorized environment. Keycloak supports X.509 browser-flow
authentication, but that feature alone does not establish a compliant DoD PKI
integration.

Playwright's built-in TLS client-certificate option expects certificate and
private-key PEM files or a PKCS#12/PFX bundle. Do not export a CAC private key
or place card PINs, certificates containing sensitive identifiers, session
cookies, or tokens in CI variables or evidence. A browser configured with the
approved smart-card middleware may be automatable after card insertion, but
certificate selection and PIN prompts can require an attended step and must
follow the environment's policy.

Use two complementary test layers:

1. Run routine automated claim, role-mapping, and positive/negative authorization
   tests with synthetic identities in a non-production test environment.
2. Run a separate, authorized CAC end-to-end test with an approved test identity
   and the approved browser/middleware stack. After authentication, verify the
   intended Rancher Project access and cross-tenant denials. If policy requires
   user presence, record the attended step and test evidence rather than
   bypassing it to make a pipeline unattended.

References: [Playwright client certificates](https://playwright.dev/docs/api/class-browser),
[Keycloak X.509 browser authentication](https://www.keycloak.org/docs/26.5.7/server_admin/index.html),
and [DoD PKI/PKE middleware](https://www.cyber.mil/pki-pke/end-users/middleware/).

## Role intent

- **Tenant administrator:** manages tenant workloads and tenant-owned secrets,
  but not Rancher Projects, cluster roles, other tenants, or platform policy.
- **Tenant developer:** deploys and troubleshoots workloads without secret
  read, RBAC mutation, or cluster-scoped permissions.
- **Tenant viewer:** reads workload status and approved metrics without
  mutation or secret access.
- **Platform administrator:** retains control of cluster-scoped security,
  tenant budgets, identity integration, shared services, and lifecycle actions.

The custom RoleTemplates and ProjectRoleTemplateBindings are applied. The
Kubernetes API impersonation matrix passed 94/94 checks. A separate Playwright
test authenticated the synthetic Alpha viewer through Keycloak into Rancher,
confirmed Alpha project visibility, and confirmed HTTP 403 for direct Bravo
project/pod API reads and secret listing. This verifies one role and a targeted
set of UI-session API permissions; it is not complete UI workflow coverage.
Hiding dashboard controls is not an authorization test. Group revocation,
session expiry, and CAC/PIV integration remain untested.

## Network boundary and caveats

The generated policy denies all pod ingress and egress by default, then allows
same-tenant namespace traffic, DNS to CoreDNS, egress to Keycloak's in-cluster
HTTP port, ingress from the RKE2 Traefik pods, and ingress from the selected
Prometheus collector for metrics scraping. The Keycloak exception uses the
dedicated `keycloak` namespace and TCP port 8080. The metrics exception is
limited to Pods labeled `app.kubernetes.io/name=prometheus` in the `monitoring`
namespace. Tenant workloads cannot initiate connections to Prometheus or
Grafana because their egress policy does not allow that path. Other platform
services and external destinations remain denied until a narrowly scoped
exception is reviewed and added. The local cluster's observed Traefik label is
`app.kubernetes.io/name=rke2-traefik`; CoreDNS uses `k8s-app=kube-dns`.
Platform monitoring, registry, and other shared-service flows must be added as
explicit, narrow exceptions only after their paths are identified.

Kubernetes NetworkPolicy does not by itself constrain node processes,
hostNetwork pods, all node-local services, or traffic outside the pod network.
The local CNI is Canal (Flannel plus Calico policy enforcement). The tested
pod-to-pod cross-tenant allow/deny paths passed; broader network paths remain
unverified.

## Shared-cluster limits

Rancher Projects, namespaces, RBAC, quotas, NetworkPolicies, and Pod Security
Admission provide layered controls but share Kubernetes control plane and
worker kernels. They do not provide hardware, kernel, or authorization-boundary
separation equivalent to a dedicated cluster. A dedicated node pool still
shares the cluster control plane. Dedicated clusters provide a stronger
separation option but still require independently designed identity, network,
operations, supply-chain, evidence, and authorization boundaries.

The homelab is an engineering test environment. It is not an IL6 environment,
does not handle classified information, and cannot establish IL6 authorization.
Any future DoD target must be assessed against the applicable system boundary,
current DISA guidance, mission-owner requirements, hosting constraints, and
authorizing officials. Do not advertise an isolation tier as operational until
its enforcement and negative tests pass.

## Exit criteria for the shared tier

1. Keycloak role groups issue the expected full-path group claim.
2. Rancher OIDC logins resolve the group principal names used by PRTBs.
3. Alpha and Bravo receive only their intended project roles.
4. Direct Kubernetes API positive and negative authorization checks pass.
5. Revoking group membership removes access after documented token/session
   expiry and synchronization behavior.
6. Live pod connectivity tests prove same-tenant, cross-tenant, DNS, ingress,
   and egress behavior.
7. Admission tests prove Restricted Pod Security and any supplemental runtime
   policies reject prohibited workloads.
8. Project-wide and namespace quota tests prove admission limits are enforced.
9. Evidence is timestamped, redacted, repeatable, and mapped to findings and
   remediation where checks fail.
