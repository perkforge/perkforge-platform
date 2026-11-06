# Mattermost initial administration — BLOCKED inactive candidate (#109)

Both installer accounts live in `bigbang`, the HelmRelease namespace. Target-
namespace and cluster bindings refer to those exact identities; API token automount
is off. The operator runtime identity is separate and remains cluster-powerful.

Big Bang3.35.1 pins Mattermost11.11.0-bb.0/app11.11.0 and required operator
1.25.9-bb.1. Both exact charts render16 objects total, including three CRDs and
one Mattermost custom resource. They are disabled/paused and absent from the root;
there is no apply entrypoint. CR rendering is not proof of operator-generated
workloads, supported Kubernetes behavior or installed readiness.

## Who does what and why

A separately approved Ansible actor would prepare versioned prerequisites.
Helm-controller uses distinct `mattermost-installer`/`mattermost-operator-installer`.
The operator installer has named CRD/ClusterRole/binding rights and named
bind/escalate only `mattermost-operator`, no cluster-admin binding. That narrow
name **does not make runtime authority small**: upstream operator receives
cluster-wide wildcard verbs on Secrets, pods, service accounts, PVCs/workloads and
its CR groups. The chart exposes no namespace-watch/RBAC restriction knob.
**That trust decision is not approved** and blocks deployment; no silent RBAC fork.

Operator subsequently creates app deployments/services from Mattermost CR; initial
Helm objects alone cannot audit every future runtime API call/upgrade branch.
Installer CRUD/roleRef/escalation covers all16 rendered objects, including the
readiness Job. Its upstream helper also creates an unrestricted
`allow-egress-from-mattermost-wait-job-to-anywhere-any-port` policy despite general
networkPolicies=false. API-only egress replacement and actual controller resources
need review before activation; do not remove readiness merely to hide this gap.
The only selected template `lookup` is the disabled Elasticsearch password path;
no Elasticsearch, SSO or database sample password renders.

## Edition, storage and access decisions

`enterprise.enabled=false` means no license Secret, **not a proven entitlement or
feature claim** for the pinned image. Current vendor guidance describes free Entry,
paid plans and version-specific authentication differences. Verify the exact
11.11 image/edition terms, user limits and Keycloak/OIDC feature availability before
activation; no license acceptance/purchase, bypass or unlicensed enterprise promise.
Initial local administration is separate from future group integration.

App requests remain2CPU/4Gi plus operator100m/512Mi, external PostgreSQL and file
object storage/backup. No bundled sample-password PostgreSQL/MinIO/Elasticsearch.
Protected `mattermost-database` and `mattermost-filestore` references are required;
actual endpoints/certificates/data-service capacity remain unconfigured. The
rendered mattermost-envs Secret contains only public site URL/scope, no credentials.
No admin account/password exists from this draft; future first-user/bootstrap
creation must be controlled through trusted restricted access, never open public
signup. Initial human credentials/cache creation requires deployment-time approval.

No Ingress/controller route, Istio or Gateway API implementation. Actual physical
PKI, backend TLS/CA, network policies, recovery and cumulative stack capacity need
review. Database credentials/connection URLs must never enter public YAML/logs.
Before release selection: approve edition/runtime trust, exact data services and
protected inputs, then verify trusted admin access, basic messaging/file upload,
unauthorized denial, persistence and isolated restore. SSO/groups later.

No obsolete direct Mattermost installer found; no reusable auth tests/config were
removed. This is reviewable blocked implementation, not tomorrow's deployable claim.

[Exact package](https://repo1.dso.mil/big-bang/product/packages/mattermost/-/tree/11.11.0-bb.0),
[operator source](https://repo1.dso.mil/big-bang/product/packages/mattermost-operator/-/tree/1.25.9-bb.1),
[v11 release notes](https://docs.mattermost.com/product-overview/mattermost-v11-changelog),
[plans](https://docs.mattermost.com/product-overview/plans),
[OIDC](https://docs.mattermost.com/administration-guide/onboard/sso-openidconnect).

## Entry and Keycloak Other OIDC — owner-selected planning target

Plan for **Entry**, the free mode of the Enterprise Edition binary, not Team
Edition and not a paid subscription/trial. Current docs list Other OIDC/Keycloak
support for Entry, but the pinned chart/image is **11.11.0**. Verify that exact
Iron Bank binary's edition/features and applicable license terms before selection;
no registry credential, purchase, license key or image upgrade is authorized here.
Entry's visible channel-history limit is 10,000 messages; HA, compliance features
and delegated granular system-admin roles are excluded. No production/PaaS
capacity or support promise follows from free availability.

`sso-values.yaml` deliberately leaves Big Bang `sso.enabled=false`: that pinned
helper emits MM_GITLABSETTINGS, not Other OIDC. The optional unselected/paused
overlay uses MM_OPENIDSETTINGS and an existing Secret reference. New user creation
stays disabled: provisioning/linking and membership/offboarding must be implemented
and approved before a new IdP person can log in. Initial local admin comes first.
`sso-review.yaml` maps tenant-admin to **own Team Admin**, developer/viewer to
assigned team/channel Member (viewer chat is allowed), never global System Admin.
OIDC groups alone do not synchronize those memberships. Do not use v12.1 ABAC or
paid/group features as if they were verified for this pin. No native apply or live
SSO acceptance is claimed; existing operator trust and capacity blockers remain.

[Entry edition](https://docs.mattermost.com/product-overview/editions-and-offerings),
[Other OIDC](https://docs.mattermost.com/administration-guide/onboard/sso-openidconnect).

## Entry and tomorrow's SSO testing decision

[Edition/source review](edition-review.md) verifies the pinned source distribution
and documents official Entry OIDC support, patched-version and non-production
license decisions. Runtime edition/OIDC acceptance remains untested.
