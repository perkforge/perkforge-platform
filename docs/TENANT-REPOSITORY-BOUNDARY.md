# Tenant repository boundary plan

Status: proposed contract, **not newly enforced live**. Platform policy owns the
security envelope; a tenant repository gets its application running inside it.
Home/household applications have no exception. The portal's future privileged API
capabilities are separately authorized application capabilities, never authority
for its deployment repository to alter platform controls.

## Ownership and object contract

| Class | Objects/content | Conditions |
|---|---|---|
| Allowed application definitions | Deployment, StatefulSet, bounded Job/CronJob, application ConfigMap, ClusterIP Service | Fixed tenant namespace; reviewed images; resource limits; restricted pod settings; approved service identity only; no secret values in Git |
| Conditional requests | PVC, Ingress, certificate requests, operator custom resources | Platform reviews storage class/size/retention, internal hostname/TLS/routes/annotations, issuer scope and operator behavior before allowing specific objects; not blanket API-group access |
| Platform-only, forbidden in tenant repo | Namespace/Project, ServiceAccount and token resources, Role/RoleBinding/ClusterRole/ClusterRoleBinding, NetworkPolicy, ResourceQuota/LimitRange, admission policy/webhooks, CRD/operator installation, Fleet registration/workspace/policy/mapping | Platform owns creation and mutation; no tenant grants, policy overrides, wildcard or cluster scope |
| Secrets | References to separately approved platform-delivered secrets | Tenant cannot create/change/read arbitrary Secrets through deployment RBAC; mounting a secret is equivalent to reading it, so references require admission constraints |

For the first portal chart the allowlist is narrower: **Deployment and ClusterIP
Service only**. No PVC, Ingress, Secret, ServiceAccount, custom resource or Helm hook
is present. Platform will own the initial internal TLS ingress until a constrained
Ingress request path exists. ConfigMaps remain possible application configuration,
but the current chart expresses only non-secret env values and a secret reference.

## Enforcement layers and indirect bypasses

1. Dedicated Fleet workspace, exact repository allowlist, fixed target namespace,
   namespace creation disabled, required scoped deployer, and label-constrained
   mapping to the intended cluster. Pin reviewed tenant commits; application images
   need separate digest pins. A Fleet label is routing metadata, not user authority.
2. Namespace Role allowlists application resource types and verbs. No mutation of
   RBAC, policy, quota, namespace labels, service identities or cluster resources.
   No bind/escalate/impersonate, token creation, pods/exec or wildcard grants.
3. Platform-owned admission must constrain workload **fields**, not only kinds:
   serviceAccountName fixed to the unprivileged runtime identity, automount false,
   restricted Pod Security, no privileged containers/hostPath/hostNetwork/hostPID/
   hostIPC/hostPorts, no unsafe capabilities or node targeting, approved image
   registries/digests, resource bounds, and approved secret/PVC references. Cover
   init/ephemeral containers and templates inside every allowed workload kind.
4. Services must remain ClusterIP without externalIPs, LoadBalancer, NodePort or
   ExternalName. Conditional Ingress grants must constrain host/path, ingress class,
   TLS secret and annotations; block snippets, alternate backends and public exposure.
   Conditional PVCs must constrain class, size, volumeName/selector, snapshots/clones
   and retention. Operators can amplify a tenant CR into privileged resources;
   each CR/operator needs its own schema/behavior review and admission policy.
5. Render the complete chart including dependencies, `extraObjects`, hooks and
   CRDs. Reject forbidden output before merge. Helm hooks do not bypass RBAC, but
   hook Jobs can run arbitrary code and must satisfy the same restrictions. Do not
   give the deployer privilege just because an upstream chart asks for it.
6. Platform NetworkPolicy denies by default and allows exact approved peers/ports.
   Apply policies to the whole namespace so pod-label changes cannot escape the
   deny boundary. Validate CNI enforcement using positive and negative live tests
   only after explicit authorization. Quota/admission and policy are complementary.

Offline allowlist tests are useful review gates, not a security boundary against
someone able to change those tests. Enforcement must live in platform-owned RBAC
and admission. Repository protection/review and immutable Git pins add change control.

## Fleet/Helm release-storage blocker

The portal proposal deliberately gives no Secret access to the deployer. Helm
normally persists release state in Secrets; the exact Fleet agent impersonation
and storage behavior must be verified in an isolated test before activation.
Do not silently copy Nextcloud's broad Secret permission to make Helm work.
Resolve release storage/controller identity and least-privilege ownership through
platform review. `resourceNames` alone cannot safely constrain create, and namespace
Secret grants could expose OIDC credentials. Current RBAC is a proposed boundary,
not a claim that Fleet installation will succeed unchanged.

## Read-only audit of current examples

Portal tenant chart: no dependencies, hooks, CRDs or `extraObjects`; renders only
Deployment/Service when enabled, zero objects by default. Runtime account is a
reference owned by platform. Offline guards inspect fully rendered output.

Nextcloud (observed source; unchanged): its app values disable chart RBAC and use
restricted non-root pod settings, but `extraManifests` includes namespaced Issuer
and Certificate, its chart includes Ingress/PVC/CronJob, and its database is a CNPG
Cluster CR. Platform `nextcloud-support` deployer Role grants broad namespaced
Secret operations and deployment/custom-resource authority. That is a gap relative
to this proposed tighter contract: workload/CR authority can indirectly expose
secrets or influence operator-created resources. It needs a separate protected
migration review; this change does not revoke grants, change Nextcloud, or assert
that existing workloads violate live policy. No live admission/network audit was run.

## Adoption and exception process

First implement platform-owned deny tests/admission in an isolated environment:
reject policy/RBAC/namespace changes, alternate service accounts, secret references,
privileged/host workloads, public service/ingress mutations, forbidden hooks/CRDs,
and unapproved operator objects; positively test the intended minimal workload.
Then verify Fleet impersonation and Helm storage, namespace quota and CNI behavior.
Only after review approve tenant registration and activation with exact pins.

For an exception, the tenant submits a declarative request describing capability,
resource/fields, justification, data sensitivity and rollback/expiry. Platform
reviews and implements the narrow policy or service integration. No tenant-owned
RoleBinding or NetworkPolicy is an acceptable exception mechanism. Future portal
GitLab/Keycloak API features require separate scope/role/audit approval and must not
inherit the deployer's credentials or security-control authority.

## Executable portal implementation

The [optional portal contract](../local-lab/optional/portal/README.md) now supplies
platform-owned identity values and generated native admission policies, with
Kubernetes 1.36.5 CEL execution and pinned schema tests. All outputs remain outside
active Fleet/catalog paths, the registration is paused, and a missing approved
image makes workload admission fail closed. This is an implemented offline control
set, not newly verified live enforcement. The broader adoption plan above remains
applicable; Fleet/Helm Secret storage and independent privileged API authorization
are not solved by config injection.

The new Fleet 0.16 schema check found `allowNamespaceCreation` unsupported by that
API. New portal output does not use it. Existing Nextcloud sources are preserved;
confirm installed-version behavior separately instead of assuming this old field
constrains namespace creation. Namespace security relies on actual RBAC/admission.
