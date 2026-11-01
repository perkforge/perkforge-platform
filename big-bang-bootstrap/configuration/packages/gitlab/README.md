# GitLab initial administration — blocked inactive candidate (#78)

Installer accounts live in `bigbang`, alongside their HelmReleases. Target-namespace
Roles bind those exact identities; targetNamespace/storageNamespace do not relocate
the impersonated account. No API token automount on installer accounts.

Big Bang 3.35.1 pins package10.4.2-bb.0 / GitLab19.4.2. The actual candidate renders
75 objects at RKE2 Kubernetes1.36.5; this is syntax/resource review, not a vendor
support certification or successful installation. Root does not include this file;
package disabled/paused, hostname/data-service addresses deliberately UNCONFIGURED.
No deployment/prerequisite-apply entrypoint is exposed while these gates remain.

## What is implemented

`candidate-values.yaml` selects neither app nor permissions. A test-only override
renders the real child with protected initial-root-password/database/Redis/object-
store references, EE **unlicensed Free baseline**, no license Secret, no OmniAuth.
A license is not required for the Free tier; do not enable paid features/security
reports as an initial prerequisite. Optional later license input is
`global.gitlab.license.secret/key` **inside the package values**; the vendor only
loads it at installation, later renewals use Admin UI. No license purchased/read.

No bundled ingress controller/cert-manager/Prometheus/runner/registry, AI gateway,
Zoekt or separate embedded OpenBao. This avoids duplicating current controllers,
monitoring, future Harbor and platform OpenBao. No Istio or Gateway API deployment.
Reusable public template, checksummed source and actual render tests are committed;
protected per-node/app inputs remain outside Git.

`prerequisites/` is versioned inactive Kubernetes YAML for the separately approved
Ansible actor, not permission for Flux to self-grant. No cluster-scoped chart RBAC
or cluster-admin. Installer has trusted namespace Secret/workload CRUD and named
bind/escalate only `gitlab-shared-secrets`. Its runtime shared-secrets Job can
get/list/create/patch namespace Secrets and generates application recovery material;
this needs separate approval/custody, not merely an admin password cache. All75
rendered kinds/roleRefs are checked. Matching initial and upgrade Helm server-dry-run paths passed against the existing
synthetic API with namespace Secret reads and no cluster-role lookup; this is not
proof of live authorization or existing-store migration behavior.

The chart unconditionally emits31 public DoD/partner CA bundle Secrets. The profile
clears customCA mounts, so those bundles are not trusted by workloads. They are
public certificates, not app credentials, but unnecessary objects still need an
explicit package/post-render review before deployment. Do not silently replace
current physical CA trust with vendor bundle defaults.

## Actual blockers, not tomorrow activation promises

GitLab chart10 **does not bundle PostgreSQL/Redis/object storage**. Their supported
versions, providers, TLS/credentials, persistence/backup and resource budget must
be decided and supplied. This draft references placeholders rather than pretending
those services exist. Gitaly alone proposes10Gi Longhorn; repositories, object
buckets, DB, Redis persistence, backups/replica overhead are additional.

Preserved vendor requests include toolbox3.5Gi, sidekiq3GB, **two webservice pods
with2.5GB Rails +2.5GB workhorse each**, shell2x300Mi, Gitaly600Mi, plus init/jobs
and external services. This is already about17Gi requested app memory before DB/
Redis/object storage, monitoring and other queued apps; all queued apps cannot
be accepted from the earlier idle snapshot. No dishonest request shrinking or
unsupported all-in-one install has been made. Review selective activation/capacity
before making it deployable. Current three16Gi nodes also run RKE2/Rancher/Longhorn.

Before release/activation: complete vendor Kubernetes/DB compatibility review,
exact current physical PKI/hostname/backend TLS, namespace network/access boundary,
protected bootstrap and generated-secret custody, database/object/repository backups,
review rendered upgrade/lookups and approve exact grants/source promotion. First
verify trusted local-admin access, project clone/push, persistence and backup/restore;
SSO/groups, runners/ingestion/scanning(#79), migration/dev-home promotion(#80) later.
No credential, existing repo, retained test data or node has been touched here.

[GitLab chart secrets/initial license](https://docs.gitlab.com/charts/installation/secrets/),
[GitLab chart architecture](https://docs.gitlab.com/charts/architecture/),
[exact package](https://repo1.dso.mil/big-bang/product/packages/gitlab/-/tree/10.4.2-bb.0).
