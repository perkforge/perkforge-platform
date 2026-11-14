# Capacity decision proposal for #36

Status: proposed planning decision for independent review, 2026-11-14. This does
not install an aggregate rate limiter, change requests/limits/retention, or certify
sustained production capacity. #38/#40 own runtime validation. Closure of #36
requires acceptance of this explicit provisional plan, not relabeling assumptions
as enforced controls.

## Accounting boundary

The measured dedicated monitoring/logging/Alloy subtotal is1605m/3972Mi requests.
The read-only namespace inventory also identifies these dependencies. Charge each
listed shared service at **100%** for conservative dependency-envelope accounting,
not a fabricated proportional observability allocation; do not double-count this
envelope when computing the whole cluster budget.

| Dependency | CPU request | Memory request | Accounting / limitations |
|---|---:|---:|---|
| tenant-observability query services | 40m | 128Mi | Dedicated query boundary |
| ntfy and projection | 60m | 96Mi | Full namespace, includes deployment notifications |
| Mattermost and operator | 250m | 1792Mi | Full shared collaboration delivery dependency |
| Keycloak and its database | 500m | 1024Mi | Full shared identity dependency |
| OpenBao | 100m | 256Mi | Full shared secret custody dependency |
| External Secrets | 100m | 256Mi | Full shared delivery controller |
| Flux controllers | 1600m | 2208Mi | Full shared deployment dependency |
| Longhorn namespace | 1440m | 0Mi declared | **Memory unreserved, not zero usage**;24 containers have no requests |
| kube-system | 2675m | 2904Mi | Full shared network/DNS/control components;7 containers have no requests |

Dedicated plus these conservatively charged namespaces total8370m/12636Mi of
**declared** requests. Missing requests and some missing limits mean there is no
finite enforced aggregate runtime bound. OS/kernel overhead and unrelated apps
remain outside this envelope, not available spare capacity. At the same snapshot
Nextcloud requests280m/840Mi, GitLab5850m/~15697Mi, Harbor850m/2048Mi and other
management/backup workloads also consume capacity. Thus48GB installed RAM is not
an observability entitlement. Per-node allocatable, init-container maxima,
overhead, affinity and rollout surge require fresh scheduler preflight; this
running-container sum is not scheduler admission proof. #442 owns resource
right-sizing; this ADR neither changes nor legitimizes unbounded containers.

## Provisional retention envelope and explicit assumptions

Existing observed window:3,304,241 sent bytes/914s ≈3.53KiB/s, with one retry.
This is a short observed sample, not a peak/day estimate. Adopt for planning review
an **8KiB/s aggregate sustained raw-ingress envelope**, with an assumed **2× total
retained-storage amplification**, across all partitions combined. Neither factor
is measured representative demand or guaranteed compression. At74h (72h retention
plus2h deletion delay) the model consumes about4.07GiB. If compaction/deletion
falls behind, the horizon grows and this model is invalid.

The measured Loki filesystem is about9.75GiB. Plan at most45% for modeled retained
working data, reserve25% for transient WAL/index/compaction uncertainty, and keep
at least30% operational free-space margin. These are review allocations, not
filesystem quotas; avoid double-counting persistent index overhead inside both
the2× estimate and transient reserve. The existing15%-free/15m alert remains an
emergency backstop, not the planning threshold. The deployed1MB/s per-partition
limit is burst protection and does not enforce this aggregate envelope.

Four observability claims total22Gi logical (~44Gi at two Longhorn replicas).
Backing-store snapshots/metadata and other claims need additional physical space;
snapshots are not reserved inside the Loki filesystem. No automatic resize,
retention reduction, deletion or arbitrary log filtering is authorized.
Prometheus retains its reviewed7d/8GB block policy on10Gi, but WAL/compaction and
series churn can exceed the block allowance. Grafana1Gi and Alloy positions1Gi
are retained state, not proof of backup/recovery or sizing longevity. Security
and audit evidence remains separately governed by #22.

## Ownership, triggers and validation handoff

Platform engineering owns this envelope and the decision to change scope/budget;
the on-call platform operator investigates alerts. Before collection expansion,
review existing source-owned scope plus current per-node scheduler and replicated
backing-store headroom. Freeze **further expansion**, not existing collection, if:

- a representative hour exceeds8KiB/s aggregate writer sent-byte average;
- modeled retained footprint exceeds45% of actual Loki capacity;
- free space drops below30%, compaction/deletion falls behind, or amplification
  exceeds the assumed2× budget;
- sustained writer drops/retries or memory pressure breach existing alert limits.

These are manual review triggers, not newly deployed alerts or an enforced ingress
cap. Existing #449 signals provide sustained writer-loss/retry/telemetry alerts;
source discovery completeness remains separate. Do not silently stop production
collection or discard fresh logs to meet this plan. Escalate the exact choice:
reduce approved scope, change supported aggregate controls, or resize after review.

#38/#40 acceptance must measure at least a representative busy and quiet cycle,
aggregate bytes/stream cardinality, retained growth and compaction/backing-store
peaks, then replace assumptions or revise the budget. Time-gated retention deletion
and actual restore remain distinct. A future enforced aggregate bound needs its
own reviewed native configuration and denial/load tests; none exists by inference
from this ADR. Whether #36's words “set capacity caps” mean an accepted planning
budget or a deployed aggregate limiter is an explicit acceptance decision. If the
latter is required, #36 remains open; this document cannot manufacture that proof.

## Exact #36 planning checklist

- Inventory, package pins, upstream-rule preservation and notification ownership:
  [architecture-current.md](architecture-current.md), sources.yaml, metrics.md and
  current alert runbooks. Preserved rules are not all migrated notifications.
- Three-node design, dependencies, resource/persistence budget: current architecture
  table plus full dependency accounting above, without HA/heavy new services.
- Observed ingestion, caps/replication/headroom/retention: bounded measurement and
  explicit proposed envelope above; enforced-cap ambiguity remains for review.
- Diagram, tenant trust, ordered flows and ownership/stages: architecture-current
  flow and Portal maintained identity/C4 model, with final release evidence separate.
- #13/#14/layout review: closed prerequisites reviewed; #20 repository migration
  remains open. Native deployment YAML and Ansible configuration remain owners.
- Six-dashboard plan, Grafana/ntfy design, evidence/rollout/recovery: current
  architecture matrix, metrics.md, scoped query/notification runbooks and recovery.md.
  Planning decisions do not close implementation children #37–40 or parent #35.
