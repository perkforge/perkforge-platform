# Observability architecture: current plan and acceptance map

Dated 2026-11-14. This reconciles planning issue #36, not implementation closure of
#37–40 or parent #35. Source artifacts and measured evidence are distinguished
from assumptions. No new deployment, permission or retention decision is made here.

## Selected architecture and ownership

Three physical RKE2 nodes have 16GB each, shared with household workloads. Native
Big Bang 3.35.1/Flux owns deployments. Pinned packages are Monitoring
91.4.1-bb.1, Grafana 13.2.4-bb.0 (app13.2.1), Loki6.55.0-bb.9 (app3.7.8),
Alloy4.3.2-bb.2 (collector1.18.0/operator1.11.0), and Prometheus Operator CRDs
31.0.1-bb.0. Exact fetched-source checksums are in [sources.yaml](sources.yaml).
There is one Prometheus store and one Grafana; bundled duplicate Grafana and
separate Prometheus Alertmanager are disabled by the reviewed design. Metrics-server
remains for Kubernetes resource metrics. No additional HA/object-storage stack is
introduced. Existing upstream recording/alert rules are preserved; this is not
proof every upstream alert has an equivalent Grafana notification rule.

- Deployment: reviewed native YAML roots and pinned Helm releases; prerequisite
  RBAC/ServiceMonitor delivery is foundation-owned where the root lacks authority.
- Configuration: Ansible renderers and guarded native API operations. Python
  validation/tests and safety verifiers are not a second deployment controller.
- Query: authenticated TLS gateway, server-derived scopes, dedicated read/write
  identities and exact-record OpenBao/ESO delivery. See [boundary](log-boundary/README.md)
  and [namespace lifecycle](log-namespace-guard/README.md). A dashboard filter is
  never authorization. Platform federation includes fallback/registered/legacy
  scopes; Portal queries only its guarded ownership epoch.
- Human authorization: [Grafana org mapping](../authorization/sso/grafana/orgs/README.md).
  Platform engineers have platform Viewer access; Portal's approved initial log
  phase maps canonical tenant roles to its org Viewer, not native org Admin.
  Machine-org denial tests do not substitute for every human browser/session test.
- Notifications: Grafana-managed rules and built-in Alertmanager own evaluation
  and routing; [ntfy](ntfy-routing/README.md) and [Mattermost projection](mattermost-projection/README.md)
  are bounded delivery destinations. [Flux deployment notifications](deployment-notifications/README.md)
  have separate purpose/topics. Each provisioned rule has one source owner.

## Measured scheduling budget, not usage or full-platform sizing

Read-only running-container resource inventory on 2026-11-14 covers monitoring,
logging and alloy namespaces. Values include sidecars and all three node exporters.
Requests reserve scheduling capacity; a low observed working set does not free it.

| Component group | CPU request | Memory request | Memory limits / caveat |
|---|---:|---:|---|
| Grafana + dashboard sidecar | 200m | 356Mi | Grafana1Gi; sidecar unbounded |
| Prometheus + TLS proxy + reloader | 270m | 1088Mi | 2Gi +128Mi; reloader has no request/limit |
| Monitoring operator | 200m | 512Mi | 512Mi |
| kube-state-metrics | 100m | 256Mi | 256Mi |
| Three node exporters | 600m | 750Mi | 750Mi total |
| Alloy collector + reloader | 60m | 306Mi | 512Mi collector; reloader unbounded |
| Alloy operator | 50m | 128Mi | 256Mi |
| Loki backend + gateway | 125m | 576Mi | 1Gi +128Mi |
| **Inventoried subtotal** | **1605m** | **3972Mi** | Not a finite aggregate memory cap |

This excludes separate query gateway, ntfy/Mattermost, identity/ESO/Flux/Longhorn,
control-plane/OS overhead and household apps. It is not the cluster total or a
claim that all remaining capacity is available. Review these shared dependencies
and real node scheduling requests in #442 before changing budgets. Storage-bound
workloads remain on eligible CSI workers; no unrelated workload relocation is
implied. Reviewed sources include [candidate values](candidate-values.yaml),
[integrated logging values](integrated-logging/values.yaml) and
[durable cursor stages](alloy-cursors/README.md). Later additive values override
old candidate defaults; inspect the fully rendered composition before rollout.

## Storage, retention and observed envelope

| Store | Logical claim | Policy / consequence |
|---|---:|---|
| Prometheus | 10Gi | 7d /8GB block cap, whichever applies first; WAL/compaction need extra room |
| Grafana | 1Gi | Persistent native state; Git remains configuration authority |
| Loki | 10Gi | 72h retention, asynchronous compactor/deletion; not free-space-triggered |
| Alloy positions | 1Gi | Retained singleton cursor state; not a delivery WAL |

These four claims total22Gi logical, approximately44Gi replica scheduling at two
Longhorn replicas, excluding snapshots, filesystem/replica metadata, other claims
and transient operations. That is allocation arithmetic, not measured consumed
bytes or a complete platform storage budget. Low current occupancy does not prove
peak ingestion fits retention. Index/WAL/chunk/compaction overhead and two-hour
Loki deletion delay require free-space margin. Existing PVC-space alert warns
below15% available for15m; it does not authorize automatic deletion.

Observed examples: the earlier15-minute full-scope window delivered16,846 entries /
3,304,241 bytes with zero new transport drops and one retry; collector peak was
64.67% of its512Mi limit. After durable migration, at17:10:34 the new process had
sent11,294 entries /1,802,242 bytes with zero drops/retries. These brief windows
are recovery/load observations, not representative daily sizing or a growth forecast.
Loki used36,515,840 bytes of10,464,022,528 bytes at that latter check. Prior historical
mixed-age rejection losses remain recorded; they are not erased by a clean window.

The source uses bounded ingestion settings, but a per-partition1MiB/s cap is NOT
a global disk bound. Required capacity follow-up: measure representative busy and
quiet periods, stream cardinality, daily net growth and compaction/snapshot peaks;
include shared services and household headroom before approving expansion/resize.
No new cap or shorter retention is silently chosen in this documentation.
Actual72h deletion proof remains scheduled separately; backend restart persistence
and cursor migration do not prove retention pruning or disaster recovery.
Security/audit evidence is governed separately by #22 and must not inherit short
operational retention by accident.

## Six-dashboard plan and ordered flows

[Metrics plan](metrics.md) and `metrics-prerequisites/dashboards.yaml` define six
source-owned starters, not complete per-app resource/traffic coverage:

| Dashboard | Intended evidence / remaining acceptance |
|---|---|
| Cluster | Node pressure/capacity; collector gaps displayed unavailable, not healthy |
| Workloads | Requests/limits, readiness/restarts and PV usage with verified labels |
| Tenants | Authoritative ownership mapping, bounded aggregation, never filters as auth |
| Nextcloud | Household resource/PV health; app traffic only from approved real exporters |
| Logging | Ingestion/drops/retries/storage and scoped pod logs; source completeness separate |
| Alerting | Evaluation health, pending/firing/resolved and delivery status, no-data explicit |

#37 owns finishing these and per-app dashboards/controlled traffic validation.
The newer [pod-log dashboard](pod-log-dashboard/README.md) has actual chained
namespace/pod/container and panel-query proof, but does not complete every starter.

Ordered flow: approved pod API logs → Alloy trusted namespace/epoch labeling →
write-only TLS gateway → Loki partition/storage → read-only server-scoped gateway
→ org-bound Grafana datasource/dashboard. Separately, exporters → Prometheus →
Grafana rule evaluation → built-in routing → bounded ntfy/Mattermost projection.
Collection errors, intentional168h history exclusions and writer transport loss
are distinct. [Delivery alerts](log-delivery-alerts/README.md) detect sustained
writer drops/retries/missing telemetry, not discovery completeness.

The maintained interactive identity/C4 model is in the Portal repository under
`architecture/` with `docs/identity-maintenance.md`; the final current-state release
is coordinated separately. It records owners, stages and ordered edges. Do not
call a pending image/root promotion live from a documentation commit. Existing
platform architecture views remain in `docs/architecture/` in this repository.

## #36 criterion disposition and handoff

| Planning criterion | Artifact / disposition |
|---|---|
| Inventory/pins/upstream rule ownership | Above, sources.yaml, metrics.md, alert runbooks; inventory documented, full alert migration remains child acceptance |
| Small-cluster topology/dependencies/resources/persistence | Above budget and native source; shared-service total and representative sizing explicitly unresolved |
| Ingestion/caps/replication/retention/security evidence | Above measured-versus-assumed envelope; #22 separate, pruning/long-term growth unproven |
| Diagram/trust/ordered flows/owners/stages | Boundary/lifecycle/C4 sources and flow above; final release status independently verified |
| #13/#14/#20 and folder conventions | #13/#14 closed; #20 repository separation remains open. Native deployment/Ansible configuration retained; no new runtime path from this review |
| Six dashboards/notifications/security/rollout/recovery plan | #37 plan above; #38/#39/#40 retain their own unfinished acceptance. #449 completed independently |

Rollout proceeds reviewed source → scoped prerequisites/custody → staged collection
→ real positive/negative queries → measured pressure/delivery → human exposure only
after authorization checks. [Recovery ownership](recovery.md) and the
[verified cursor migration](alloy-cursors/README.md) describe guarded fix-forward,
retained state and stop conditions. Replication is not a backup, and no destructive
restore or additional restart is authorized by this plan. Parent #35 remains open
while its children do; planning completion must not be represented as implementation
acceptance. The remaining budget assumptions require explicit review, not invented
precision or a blanket “architecture complete” claim.
