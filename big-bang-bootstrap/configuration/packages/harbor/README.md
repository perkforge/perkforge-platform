# Harbor initial administration — blocked inactive candidate (#25)

Installer accounts live in `bigbang`, alongside their HelmReleases. Target Roles
bind those exact identities; storageNamespace does not relocate impersonation.
Installer API token automount is disabled.

Exact Big Bang 3.35.1 package1.19.2-bb.3/app2.15.2 profile and checksummed source
render23 objects. Disabled/paused, no root inclusion, no prerequisite apply path.
No live deployment, credential generation or claim that the cumulative stack fits.

Initial admin and all encryption/token-signing/CSRF/job/registry/database/Redis
material use protected Secret references. Four vendor Secret objects render empty,
not sample passwords/generated keys. No public source cache contains real values.
Root/admin password is only part of recovery: preserve Harbor encryption/signing
material and consistent database plus registry content backups independently.
Do not overwrite existing stores or assume password replacement resets admin.

External PostgreSQL and Redis are deliberately UNCONFIGURED. Bundled dependencies
are off rather than deploying their vendor example passwords. PostgreSQL verify-full
is requested, but actual server CA/client trust mounts, Redis TLS, service endpoints
and supported versions need completion before selection. ClusterIP service TLS
references current physical `harbor-service-tls`; no auto self-signed cert, Ingress,
Istio or Gateway API changes. Backend/internal component transport and network
policies still need review; ClusterIP does not itself authenticate/isolate traffic.

Registry10Gi plus job logs1Gi proposes22Gi Longhorn scheduled data for two replicas,
excluding PostgreSQL/Redis, snapshots, backups and headroom. Workload requests and
actual push/pull/scanning load must join the whole queued-stack budget. No broad
low-resource tuning is claimed sufficient for this three-node cluster.

The selected chart creates no runtime RBAC. Its inactive installer has namespace
workload/Secret/Helm-history CRUD, no cluster/bind/escalate grants. Actual rendered
object kinds and initial/upgrade Helm Secret lookups are checked against the existing
synthetic API model; live authorizer, existing-secret conflicts, upgrade migrations,
TLS, push/pull authorization, persistence/restore and performance are untested.

**Scanner intentionally deferred, not silently secured:** Trivy is off in this
initial-access proposal, pending #26/#79 ingestion/scanning design and capacity/
DB egress policy. No scanned-image or supply-chain-security claim. Approve that
limited scope or enable a reviewed scanner before exposing a registry workflow.
SSO/groups/robots/CI publisher tokens and GitLab migration remain later decisions.
No obsolete direct Harbor installer found to remove; useful auth patterns retained.

Before activation: choose data services/capacity, protected input custody, exact
PKI and network boundaries, approve scoped grants/release selection, then verify
trusted admin login, authenticated push/pull and denial, retained data and isolated
restore. User owns any eventual temporary credential-cache migration.

[Exact package](https://repo1.dso.mil/big-bang/product/packages/harbor/-/tree/1.19.2-bb.3),
[Harbor chart](https://github.com/goharbor/harbor-helm/tree/v1.19.2),
[Harbor administration](https://goharbor.io/docs/).
