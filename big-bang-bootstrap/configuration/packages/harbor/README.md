# Harbor initial administration — blocked inactive candidate (#25)

Installer accounts live in `bigbang`, alongside their HelmReleases. Target Roles
bind those exact identities; storageNamespace does not relocate impersonation.
Installer API token automount is disabled.

Exact Big Bang3.35.1 package1.19.2-bb.3/app2.15.2 profile and checksummed source
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
is requested. Native `upstream.redis.external.tlsOptions.enable=true` renders
`rediss` URLs and registry `enableTLS`; `upstream.caBundleSecretName` references
`harbor-public-ca` key `ca.crt` at the native custom-CA mount in its consumers.
This is a public CA bundle only, never a signing key.
The same public-CA Secret is explicitly selected by `caSecretName` for core's
CA-download volume; leaving it empty with externally supplied service TLS makes
the pinned chart render an invalid empty Secret volume.
Actual container trust-store
loading, verified database/Redis server identities, service endpoints and supported
versions still need completion and live positive/negative TLS checks before selection.
ClusterIP service TLS
references current physical `harbor-service-tls`; no auto self-signed cert, Ingress,
Istio or Gateway API changes. Backend/internal component transport and network
policies still need review; ClusterIP does not itself authenticate/isolate traffic.

Core explicitly sets `PGSSLROOTCERT=/harbor_cust_cert/custom-ca.crt` so the
PostgreSQL driver selects the already mounted public CA, including its schema
migrator. A custom-CA mount/system trust update alone does not establish this
database-driver configuration. This follows the pinned [Harbor connection and
migration source](https://github.com/goharbor/harbor/blob/v2.15.2/src/common/dao/pgsql.go)
and its [pgx v5.10.0 environment/TLS parser](https://github.com/jackc/pgx/blob/v5.10.0/pgconn/config.go).
Exact image/runtime positive and wrong-CA/hostname tests remain required.
The single-core pilot bounds its database pool at 50 open/10 idle connections,
instead of the native 900/100 defaults; this is a ceiling, not a reservation or
proof of adequate PostgreSQL capacity. Exporter/scanner remain off.

Registry10Gi uses the accepted `longhorn-dedicated` class (two replicas, Retain,
expansion enabled) for future image/chart data. Job logs1Gi stay on `longhorn`.
This inactive source choice changes no existing claim or data. Together they propose22Gi Longhorn scheduled data for two replicas,
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

## Shortest isolated data-service path — approval still required

Use dedicated Harbor PostgreSQL and a dedicated TLS/authenticated Valkey instance;
do not add users/databases to the accepted GitLab/Nextcloud clusters or share their
credentials/cache. Harbor 2.15.2 [adopted Valkey](https://github.com/goharbor/harbor-helm/releases/tag/v1.19.2),
so the pinned existing Valkey chart is a candidate for reuse as a separate release,
not evidence that external TLS/authentication has passed. Keep the single-writer
Recreate/RWO design and distinct Redis indexes (core 0, jobs 1, registry 2);
password-only auth uses `REDIS_PASSWORD` from the dedicated `harbor-redis` Secret.
No Sentinel/cluster or new operator is needed for this pilot.

Reusing the shared CNPG operator requires an additive Harbor watch/namespace Role
review that preserves both current watches (`gitlab`, `tenant-home-nextcloud`).
Do not replace the current watch configuration or rerun provider installation.
The operator gains management of Harbor database workloads and Secrets; this is
an action-time access decision. A new namespaced data installer, immutable inputs,
database/cache certificates and public CA delivery also need reviewed source.
Database/cache PVC sizes and resource requests remain undecided: count two
Longhorn replicas plus existing registry/job-log 22Gi, snapshots and headroom
before selecting them. Small single instances accept downtime and do not provide
independent backup/restore by themselves.

Publish/apply the approved foundation and empty data-only stage before enabling
Harbor: verify TLS identities, wrong CA/hostname/password/plaintext denials,
cross-namespace denial, persistence and unchanged existing claims/services.
Then approve the scanner-deferred scope, deliver the Harbor-only protected inputs,
and select an empty platform-admin-only app pilot. Admin access, authenticated
push/pull/denial and isolated restore remain acceptance gates. No data stage,
credential, namespace grant, certificate or workload is created by this proposal.

[Exact package](https://repo1.dso.mil/big-bang/product/packages/harbor/-/tree/1.19.2-bb.3),
[Harbor chart](https://github.com/goharbor/harbor-helm/tree/v1.19.2),
[Harbor administration](https://goharbor.io/docs/).

## Keycloak OIDC review — native API ownership

`sso-review.yaml` records a disabled dedicated client and public Harbor
configuration payload. Future explicitly approved Ansible configuration owns the
API settings and protected client-secret delivery; no Helm hook, config-overwrite
secret literal or live apply is added. Verify the pinned server/schema first.

Configure OIDC before creating local non-admin users: those users block mode
migration. Keep and test the built-in local admin. Groups must be in the **ID
token**; the OIDC group filter does not restrict login. Only the explicit platform
admin group proposes system administration. Tenant admin/developer/viewer map to
own private project Admin/Developer/Guest, with membership/offboarding still
unimplemented. Project creation is admin-only; no public-project or unassigned-user
access claim is made. Rollback must preserve images/projects/robots and recovery,
not blindly switch authentication modes or assume issued tokens are revoked.

[Harbor OIDC](https://goharbor.io/docs/2.15.0/administration/configure-authentication/oidc-auth/),
[system settings](https://goharbor.io/docs/2.15.0/install-config/configure-system-settings-cli/).
