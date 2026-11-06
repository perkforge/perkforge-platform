# Shared CloudNativePG foundation — inactive preparation

Corey selected CloudNativePG as the reusable platform database operator. This is
an architectural decision, not installation approval. Chart 0.29.1/operator
1.30.1 is pinned; its HelmRelease remains suspended and no normal/review root
installs it. Installer identities and privileged bindings in `prerequisites.yaml`
are separately approved owner-admin foundation inputs, not self-applied resources.

The operator lives in `cnpg-system`. Initial WATCH_NAMESPACE is exactly `gitlab`
in both the public config and the actual post-rendered Deployment. The upstream
namespace-only Role is mirrored into the watched database namespace and bound to
the operator's real ServiceAccount; no global Secret-reading rule is added.
Future database namespaces require reviewed namespace Roles/bindings and matching
watch-list changes, not another instance or an implicit all-namespace watch.
The `local-nextcloud` stage explicitly sets both chart configuration and the
post-rendered Deployment to `gitlab,tenant-home-nextcloud`; other stages retain
`gitlab`. Apply the separately published Nextcloud foundation's operator-only Role
and RoleBinding before promoting this stage. Tenant identities gain none of these
permissions. This rolls only the controller at the same pinned version, briefly
pausing reconciliation; do not restart database Pods. Recheck GitLab readiness,
controller watch list and denied access in an unrelated namespace before creating
the Nextcloud database.

Its 11 CRDs and two fixed-name admission webhooks remain global. Node discovery,
ClusterImageCatalog reads and webhook get/patch are runtime cluster permissions.
Installer named bind/escalate and CRD/webhook authority are privileged; Kubernetes
cannot restrict create by object name. `authority-review.yaml` records the pinned
render inventory. Installation preflight must reject existing foreign operator,
CRD, webhook or Helm ownership; do not adopt or replace a spike installation.
Built-in view/edit/admin aggregation stays off. The chart emits CRDs as templates, so CRD Skip alone is insufficient.
Operator values explicitly set crds.create=false and its installer has no CRD
mutation permission. The owner-admin Ansible foundation downloads/checksums the
pinned chart into a private cache, renders in a fresh temporary directory, and
creates only missing owned CRDs. Existing foreign or changed schemas refuse.
CRD upgrades require an explicit procedure; disabling GitLab does not uninstall this shared
foundation or delete databases.

Dormant stage roots first select providers, then database CRs/data workloads only
after CRDs/operator readiness, then GitLab, then its runner. The combined review
profile remains disabled. Every live stage requires immutable release verification,
current ownership/cluster checks and owner approval; a directory is no permission.

Primary references: [pinned chart](https://github.com/cloudnative-pg/charts/tree/cloudnative-pg-v0.29.1),
[operator configuration](https://cloudnative-pg.io/documentation/1.30/operator_conf/).
