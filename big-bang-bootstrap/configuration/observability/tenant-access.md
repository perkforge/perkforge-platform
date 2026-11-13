# Portal tenant observability boundary (#218)

Status: **design contract, not deployed query authorization**. Portal is the first
integrated PaaS pilot. This review does not add a Grafana organization, datasource,
user, native role, backend identity, collector or network rule. Keep existing
platform access unchanged. Notification delivery may proceed with scoped content
while tenant query access remains blocked.

## Authoritative context and ownership

Use the platform-owned Portal context from #16/#43, not claims, labels, a query
parameter, an application annotation or a notification payload as the source of
namespace ownership. The reviewed enrollment identifies runtime `tenant-portal`
and control namespaces `tenant-portal-config` and `tenant-portal-release`. Runtime
visibility does **not** imply access to the two control namespaces. Additional
applications/namespaces require an explicit context update and acceptance.

The identity work owns Keycloak groups and roles. This layer consumes the effective
context entitlement; it must not independently invent roles or membership. Users
in multiple tenants get separate explicitly authorized contexts, not a wildcard
query credential. Unknown or removed contexts receive no tenant datasource access.

Access matrix: Corey approved tenant Admin/Editor/Viewer mapping; no grants are
enabled until the backend and every access path enforce tenant isolation.

| Actor | Candidate access | Not implied |
|---|---|---|
| Platform administrator | Preserve current platform monitoring | New tenant membership or new credentials |
| Platform engineer | Corey selected visibility across all tenants ("God mode"); native Grafana role still to be selected | OpenBao access or any unrequested credential/secret grant |
| Portal tenant administrator | Grafana organization Admin, only after genuinely tenant-isolated data exists | Grafana server admin, control namespaces, other tenants |
| Portal tenant developer | Grafana Editor within tenant-isolated data | Datasource/backend administration or other tenant access |
| Portal tenant viewer | Grafana Viewer within tenant-isolated data; Mattermost channel alerts, no direct alert delivery | Dashboard edits or other tenant access |
| Unmapped/removed identity | Deny | Fallback organization or default datasource |
| Collector | Explicit namespace read + ingest identity | Query or administration identity |
| Grafana backend client | Read-only authorized datastore scope | Ingest, rule administration, storage deletion, arbitrary tenant header |

Changing namespace ownership does not automatically relabel historical data. Block
access during ambiguous transitions, decide historical custody explicitly, then
reconcile native memberships and credentials. Login-time role sync is not immediate
session revocation. Removal acceptance must exercise an already-established session
and cached/native membership, not just a new login.

## Current pinned baseline and limits

Source pins are in [sources.yaml](sources.yaml) and the existing package fixtures.
They are not a fresh live inventory.

| Component | Source pin | Boundary implication |
|---|---|---|
| Grafana | chart 13.2.4-bb.0 / app 13.2.1 | Current own-client admin-only SSO does not implement tenant organization mapping. In OSS, a user can query all datasources in their organization; folders and dashboard filters do not restrict the underlying queries. |
| Monitoring | chart 91.4.1-bb.1 / operator 0.94.0 | The shared Prometheus store exposes its whole dataset to query clients. Namespace selectors in dashboards are not authorization. |
| Loki | chart 6.55.0-bb.9 / app 3.7.8 | Native tenant partitioning exists, but an authenticating gateway must choose the tenant; the current pilot machine credential allows read/write and cannot be handed to tenants. |
| Alloy | chart 4.3.2-bb.2 / binary 1.18.0 | Collection namespace/RBAC scope and trusted ingest routing must establish data ownership before query isolation can be meaningful. |

Grafana datasource permissions and label-based controls cannot be assumed available
in this OSS baseline; Enterprise/Cloud features require a separate edition/license
decision. Native organization separation can separate datasource *configuration*,
but cannot fix a datasource credential that can read the entire backend.

The current `groups` claim in the Grafana client is populated from that client's
own roles, not the realm's arbitrary groups. Extending the shared Keycloak group
model must preserve this distinction and explicit native application authorization.

## Practical choices, not predetermined deployment counts

| Option | Advantage | Cost / gate |
|---|---|---|
| Shared Grafana, tenant organization, isolated backend credentials/stores | Reuses the UI service; scoped datasources hold no cross-tenant authority | Explicit organization/membership lifecycle. Prometheus needs a scoped store or real authorizer; Loki needs a read-only trusted tenant gateway. |
| Dedicated tenant Grafana and scoped stores | Straightforward process/data boundary | Extra resources and app/client lifecycle per tenant; still needs scoped ingestion and backend bypass denial. |
| Shared stores with a query authorization gateway | Avoids copying metrics into per-tenant stores | More implementation/maintenance; all query, metadata, resource, streaming and alternate API paths must enforce scope. A regex appended to PromQL/LogQL is insufficient. |
| Enterprise/Cloud datasource/LBAC features | Native product controls may reduce custom work | Edition/license and exact pinned behavior must be evaluated; no paid feature assumed. |

Recommendation for review: retain the existing Grafana service and evaluate an
explicit tenant organization with datasources backed by genuinely scoped endpoints.
Do not select a second Grafana deployment merely for a different dashboard. Decide
the metrics-store/query-authorizer tradeoff before enabling any tenant query path.
A small Portal-only metrics store is easier to reason about than a new general
query-rewriting service, but its resource cost is a decision, not hidden scope.

## Required data and query trust flow

1. Platform-owned context resolves tenant → permitted runtime namespaces/apps.
2. Collector reads only approved namespaces. It assigns tenant routing from that
   context, not from application-provided `tenant`, `namespace` or header values.
   App metrics/log labels cannot spoof another tenant's destination. Cluster-wide
   metrics such as kube-state-metrics must be scoped before entering a tenant
   dataset; a namespaced scrape target alone does not make its payload scoped.
3. Keycloak authentication plus application authorization selects a native Grafana
   organization/datasource context. Browser-controlled organization/datasource IDs
   must not expand entitlement.
4. The datasource's protected read-only backend identity is limited independently
   of user query text. Loki gateway derives one fixed tenant, overwrites any client
   `X-Scope-OrgID`, rejects cross-tenant federation and denies push/delete/admin
   endpoints. Separate ingest credentials remain separate. Prometheus cannot be
   considered scoped until its store or complete query boundary enforces scope.
5. Backend ports are not directly reachable by tenant workloads/users. Only the
   trusted gateway/collector paths are allowed; TLS hostname/CA checks stay on.
6. Grafana Explore, `/api/ds/query`, datasource proxy/resource calls, streaming,
   metadata/labels/series endpoints and saved links all encounter the same boundary.
   Any unsupported path is denied rather than forwarded with a shared credential.

Platform-owned provisioning controls backend credentials, query enforcement and
notification routes. Folder visibility is presentation, not the data boundary.
Corey approved native organization Admin/Editor/Viewer tenant roles, so enforcement
must hold even when a tenant Admin creates a datasource or an Editor changes a
query/dashboard. Native Admin is not a restricted custom role: do not promise its
UI/API cannot create a datasource. Backends and network boundaries must make those
actions unable to reach another context or acquire a broader credential. Public
snapshots, anonymous/public sharing and external rendering/export remain unavailable
until disclosure behavior is reviewed. Native role rights and the required provider
restrictions must be tested together, not claimed from immutable provisioning alone.

## Activation acceptance and rollback

Use synthetic Portal and second-tenant sentinels in a separately approved test
scope. Do not inspect household data to prove a denial. Record exact deployed
versions/configuration, identities, tested URLs and sanitized results.

| Test surface | Required result |
|---|---|
| Portal dashboard and arbitrary Explore/query | Portal sentinel visible; second tenant and platform/control sentinels absent/denied |
| Foreign organization/datasource IDs and direct API/proxy/resource calls | Denied, including copied links and saved queries |
| Spoofed/multiple/empty tenant header, alternate encodings and query selectors | Cannot widen the backend tenant or bypass authorization |
| Backend direct address and alternate query/metadata/streaming endpoints | Denied unless explicitly supported under the same boundary |
| Query identity used for ingestion/delete/admin | Denied |
| Collector for unapproved namespace; application-spoofed ownership labels | Not ingested into another context |
| Unmapped identity; removed member with existing session | Denied within documented revocation bound; no fallback organization |
| Multi-tenant user | Only explicitly assigned contexts, no union credential |
| Dashboard sharing/snapshot/datasource creation attempts | Denied unless separately approved and equivalently constrained |
| Platform administration and existing recovery access | Preserved |
| Native app restart/configuration reconcile | Boundary and scoped datasource/membership persist |

These are acceptance requirements, not completed tests. Offline configuration tests
cannot prove native API, network/CNI or storage enforcement. #39 may publish only
sanitized context-specific notifications before these gates pass, and must omit
Grafana detail links the recipient is not authorized to open.

Rollback removes only the newly introduced tenant entry/membership and its query
route, then verifies existing sessions and backend credentials cannot keep querying.
Preserve existing platform administration, recovery access and stored telemetry.
Disabling a Keycloak client alone does not revoke all native sessions or machine
credentials. Storage cleanup/deletion is not part of this rollback.

## References

- [Grafana datasource security and edition limits](https://grafana.com/docs/grafana/latest/administration/data-source-management/)
- [Grafana organization management](https://grafana.com/docs/grafana/latest/administration/organization-management/)
- [Loki tenant isolation](https://grafana.com/docs/loki/latest/operations/multi-tenancy/)
- [Loki authentication](https://grafana.com/docs/loki/latest/operations/authentication/)
- [Prometheus security model](https://prometheus.io/docs/operating/security/)
- Existing [logging boundary](logging.md), [metrics](metrics.md), and [authorization matrix](../authorization/MATRIX.md).

## Inactive native query gateway slice

[The candidate renderer and native component tests](tenant-query/README.md) use
per-context TLS authentication and pinned prom-label-proxy with fixed namespace
scopes. No live tenant access, ingestion authenticity, Grafana custom-datasource
bypass protection or returned-series isolation is claimed. Deployment and those
acceptance gates remain open; this is not a completed #218 implementation.
