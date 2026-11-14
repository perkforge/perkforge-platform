# Phase A: platform-only real pod logs

This optional root is source preparation until a reviewed exact commit is selected.
It inherits the current integrated logging root, preserving existing apps, ingress,
SSO, query/notification mounts, Prometheus and the old `loki-pilot` datasource.
The new org-1 `loki-platform` datasource has a distinct read-only identity; the
native dashboard and reviewed PE-only OAuth fields are additive map keys.
No tenant org, user membership or tenant query map is enabled here.

## Ordered activation

1. Complete reviewed four-record custody delivery and verify exact synchronized
   payload, not only a Ready condition. Keep original pilot credentials/Secrets.
2. The authorized foundation operator applies only `collector-rbac.yaml` and
   verifies pod metadata/log reads, with Secrets/exec/writes still denied.
   These two cluster-scoped objects are deliberately NOT in the tenant-limited
   root: `platform-reconciler` cannot create ClusterRoles/Bindings. Do not expand
   its authority or reinstall bootstrap to apply these prerequisites.
3. Verify no active old opt-in pilot producer before the gateway/collector switch;
   otherwise review buffer/loss impact. Preserve `platform-pilot` hash with exact
   legacy read scope. New writes use only `pf-log-collector-write` and registered
   scopes. Gateway access metadata goes to stdout without request arguments or log
   content, avoiding an unbounded private filesystem log.
4. Select the reviewed current-root composition only in the serialized window.
   Wait for Loki/gateway/Alloy/Grafana readiness; verify actual pipeline labels,
   spoofed namespace annotation handling, read/write separation, arbitrary header
   denial, legacy query preservation and TLS. Test actual datasource proxy and
   dashboard queries before enabling the separately reviewed PE entitlement.
5. Verify existing dashboard inventory/Prometheus/notifications and app readiness.
   Tenant access remains gated by lifecycle admission and actual cross-scope tests.

Initial collection is explicitly `tenant-portal`, `mattermost`, `flux-system`.
This provides real workload logs and a platform read federation while measuring
bytes/retries/drops/PVC growth/CPU/memory against existing 10Gi/72h storage and
unchanged requests/limits. It is NOT yet all-cluster coverage. Expand the source
namespace list or explicit all-namespace flag only after the measured budget is
reviewed. Per-tenant ingestion limits are not a global storage cap; no arbitrary
silent debug dropping or claim of general secret redaction is made.

`profile.yaml` plus the reusable boundary renderer must reproduce checked-in
`boundary-values.yaml` and `collector-rbac.yaml`. The dashboard values derive from
the reviewed `pod-log-dashboard/platform-profile.yaml` and renderer, wrapped by
`dashboard-values.yaml.j2`; no alternate dashboard or datasource fallback.

Pinned Alloy defaults move `pod` into structured metadata. The profile explicitly
nulls only that mapping so the final Kubernetes-derived `pod` label remains
indexed and native Loki pod-label discovery/chained dashboard variables work.
Other metadata mappings remain unchanged. Historical records collected before this
fix can expose pod in query results but not indexed label discovery; verify newly
ingested streams rather than mistaking that metadata for working dropdowns.

### Measured second stage (2026-11-14)

The first 10-minute observation (14:31–14:41 UTC) sent 235,175 bytes/848 entries
with no added retries or drops; collector working-set memory was 157–164Mi and
CPU about 2–3m. PVC used bytes grew 389,120→843,776 with over 99% available.
These short-window figures are not a full-cluster or steady-state retention proof.
The separate earlier rollout credential failure had dropped batches; counters at
observation start were not zero and no no-loss claim is made.

The next explicit source stage adds `monitoring` to the existing three namespaces,
without grants, image/resource changes or tenant exposure. Observe at least another
10 minutes with the same error/drop/retry, memory and PVC-growth checks before an
all-namespace trial. Do not infer full-cluster capacity from quiet Portal workloads.

### Cluster-wide observation stage

The explicit all-namespace profile is the next controlled trial, not retrospective
proof that all workloads were collected. Promote only after the representative
10-minute monitoring window has stable fresh ingestion, no newly increasing
retry/drop counters, collector cgroup/working-set usage below 75% of its 256Mi
limit, and more than 30% PVC free with a measured 72-hour growth projection plus
30% reserve fitting capacity. Observe at least 15 minutes after expansion; short
windows cannot establish a steady-state capacity or retention guarantee. Keep
existing requests/limits, credentials, routing and tenant query denial unchanged.

The gateway suppresses only successful POST push access metadata, avoiding a
self-collection feedback loop once `logging` is included. Failed push requests,
authorization denials and query access metadata remain logged; application logs
are not silently discarded by this rule. Native pod collection opt-out annotations
still apply. The pre-expansion inventory had no opted-out active pods; future
opt-outs must not be presented as complete coverage.

Adding `monitoring` initially encountered five timestamp-too-old HTTP 400 batches
at 14:50:36–37 UTC. Compared with the earlier window, dropped counters increased
by 15,825 entries / 636,967 bytes and retry counters by 14. These are interval-wide
counter deltas, not a claim each loss was an old record: a rejected batch can
include mixed-age entries, and the exact per-entry disposition was not verified.
No age policy was weakened and no lossless backfill claim is made. Acceptance
uses a separate clean post-catch-up window beginning 14:54:46 UTC.

### Collector-only measured memory correction

The first all-namespace startup exceeded the pilot memory gate: cgroup usage
reached 256,978,944/268,435,456 bytes (95.7%) with memory-max events, although no
OOM or restart was observed. The targeted fix raises only collector memory
request 128Mi→256Mi and limit 256Mi→512Mi, preserving 50m CPU, reloader resources,
image, placement and all other workloads. Before rollout the eligible control
node had about 5.7Gi of unrequested memory and over 1 CPU free; one surge pod
requires only 306Mi/60m including the unchanged reloader. No Nextcloud workload
move or sizing change is involved. This corrects measured headroom, not old-log
HTTP400 rejection. Repeat fresh delivery and 75%-of-limit memory gates afterward.
