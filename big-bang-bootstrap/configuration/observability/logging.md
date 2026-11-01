# Opt-in logging implementation candidate — inactive

Implements the pinned #38 candidate after [metrics](metrics.md); the root still
selects neither monitoring nor logging. This is not live log or auth acceptance.

## Who does what and why

The separately approved Ansible actor runs the default-off
[`logging-prerequisites.yaml`](../ansible/logging-prerequisites.yaml). It prepares
logging/alloy namespaces, installer identities, an opt-in pilot namespace, scoped
runtime log reader and ingress policies. Helm-controller impersonates separate
`logging:loki-installer` and `alloy:alloy-installer` accounts. Helm history stays in
each namespace. Installers can manage namespace Secrets; treat them as trusted
infrastructure, not ordinary human users. Alloy installer has named CRD rights
(create cannot be name-limited) and named Role bind/escalate, not cluster-admin.

The supported Alloy operator **ownNamespaceOnly** mode creates Roles instead of
ClusterRoles. Its Role still has broad Secret/workload/RBAC authority inside alloy;
cluster-scoped resource names in a Role do not grant cluster authority. The API
collector uses precreated `alloy-log-reader`, no host mounts, no added capabilities,
and only pods/log in `logging-pilot`. Pod discovery filters the opt-in label
`observability.perkforge.io/logs=true`; RBAC covers the namespace, so that label is
not an authorization boundary. No production namespace or auth/bootstrap logs are
selected. Operator-created workload behavior still needs live verification; a
rendered Alloy custom resource alone does not prove its generated PodSpec.

## Data and trust path

Alloy 1.18.0 reads the Kubernetes log API, applies a narrow password/token/secret
value replacement, and sends through authenticated HTTPS to the native Loki
gateway. This defense is not a guarantee of secret removal: producers must not log
secrets; arbitrary encodings/multiline data are outside the expression. Experimental
`loki.secretfilter` is deliberately off. No blind truncation of oversized entries.

Gateway Basic auth is backed by protected `.htpasswd` Secret `loki-gateway-auth`.
Every proxied location overwrites `X-Scope-OrgID` with the authenticated username
and strips upstream Authorization. Client-supplied tenant headers are not trusted.
Gateway verifies backend TLS against the current physical CA; backend and gateway
require their own correct service-DNS SANs. Loki itself is not an authentication
server. Namespace ingress policies prevent other namespaces bypassing the gateway;
all workloads in logging remain trusted. Verify real enforcement and negative
requests before expanding collection. No external Ingress/controller route exists.

Required future protected inputs (none created here): logging `loki-backend-tls`,
`loki-gateway-tls` (includes public ca.crt), `loki-gateway-auth`; alloy
`loki-client-auth` with chart-required username/password/tenantId/cert/key fields
(empty optional values only where supported), and public `loki-ca` ConfigMap.
An initial platform machine identity would have broad read/write access to its
Loki tenant, **not read-only Grafana or tenant-user isolation**. Choose/review that
identity before activation. Grafana Loki datasource credential delivery and
per-tenant query authorization remain blocked; no password or htpasswd is embedded
in these sources and no tenant UI is enabled. Do not reuse CA signing keys or app
bootstrap tokens for this purpose.

SingleBinary Loki 3.7.8 uses filesystem TSDB on one 10Gi Longhorn PVC with 72h
retention/compactor enabled; one Loki replica is not HA. Longhorn two-copy storage
is distinct from Loki replication_factor=1. Limits start at 1MB/s, 2MB burst,
5,000 streams and 256KB rejected maximum line size. At sustained 1MB/s the disk
would fill long before 72h: retention is not a quota. Measure real ingest,
compression, WAL/index/compaction and snapshots; stop or reduce ingest well before
reserve exhaustion. Operational retention does not define security/audit retention.
No MinIO, caches, canary, duplicated metrics collector or object-store backup.

## Evidence and remaining gates

Offline tests render the exact checksummed Big Bang 3.35.1 child pins, enumerate all
30 chart objects and roleRefs, check installer CRUD/bind/escalate, scoped CR fields,
TLS/tenant overwrite/retention, and run the default-off playbook with changed=0.
Source lookup review found Alloy's legacy upgrade migration lookup and Loki's
StatefulSet recreation lookup; both supported automatic migration/recreation
switches are explicitly off. This is not a proof of every future upgrade branch.

No Alloy/Loki binary validation, controller execution, network/auth allow/deny,
actual log ingestion/query/redaction/cardinality, disk retention/load, admin login,
upgrade/redeploy or independent restore has run. Preserve the Alloy CRD and data;
chart uninstall includes finalizer/removal hooks and needs separate approval.
No source selection or permissions are deployed by merging this inactive draft.
A later release/promotion requires reviewed capacity, PKI/credential delivery,
operator CRD compatibility and successful scoped pilot evidence. Never repair
an auth failure by allowing anonymous ingress or widening tenant headers/RBAC.

References: [pinned package sources](sources.yaml),
[Loki authentication](https://grafana.com/docs/loki/latest/operations/authentication/),
[Loki multi-tenancy](https://grafana.com/docs/loki/latest/operations/multi-tenancy/),
[Alloy processing](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.process/).
