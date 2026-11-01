# Alert rules and acceptance preparation — inactive

For #39/#40 after [metrics](metrics.md) and [logging](logging.md). These sources
add reviewable native rules and a bounded readiness evidence helper, not completed
live acceptance or a working notification bridge. No root includes this overlay.

`alert-values.yaml` preserves all35 vendor PrometheusRule objects and adds one
three-rule group: NodeNotReady5m, PVC free below15%10m, available node memory below
10%10m. Thresholds/delays are starting review values; compare useful vendor rules
and deduplicate before activation. The bundled Alertmanager owns grouping,
inhibition/silences and eventual notifications. Its candidate receiver is explicitly
`null`: it sends **nothing**. It is not a placeholder URL that might receive data.

Grafana is the main human alert/dashboard interface. Its external Prometheus
Alertmanager datasource can display/silence alerts, but external routing/contact
configuration remains Git-owned and read-only in Grafana. Grafana's built-in
Alertmanager does not receive arbitrary Prometheus alerts. Future Grafana-managed
rules must forward to the same external manager, with one proven notification path;
that forwarding remains off, no second direct ntfy contact point is configured.

`notification-contract.yaml` is disabled and deliberately not a deployable receiver.
Native Alertmanager webhook JSON is not automatically the ntfy publish API. Endpoint,
TLS, credential custody and supported payload conversion/adapter require review.
No invented unauthenticated webhook, credentials, in-URL token or retry bridge.
Inspect labels/annotations for sensitive tenant information before delivery.
Myles provisioner remains excluded; Istio/Gateway API is ticket-only.

## Execution and evidence contract

`configuration/ansible/observability-verify.yaml` is default-off and in check mode
uses no credentials/API/files. A separately approved execution verifies the exact
cluster UID, refuses an existing evidence directory, waits once for five named
HelmRelease conditions, saves every result/status owner-only and stops on failure.
It never resumes/reconciles/repairs controllers or reads Secrets/PodSpecs/logs.
Use a fresh directory under the established protected runtime evidence parent;
operator must verify that parent is trusted and not a symlink. This helper proves
only release readiness, **not the full #40 acceptance below**.

After a reviewed release/selection and explicit scoped approval, acceptance must
record actual outcomes, timestamps and limits:

1. All-node/RKE2 and workload scrapes, intended dashboards and truthful NoData;
   no duplicate Prometheus/Alloy metrics pipeline.
2. Nonsecret opt-in log samples from each intended scope searchable through
   authenticated TLS; wrong credentials/header spoofing/backend bypass denied.
   Tenant query isolation is a separate required boundary before tenant access.
3. Controlled firing and resolved signal reaches only the intended client;
   grouping/repeat/silence/dedup and delivery failure are observable.
4. Measure CPU/memory, cardinality, ingest rate and Longhorn replicas/WAL/index/
   compaction/reserve headroom; verify configured retention over time, not by
   merely reading values. Whole-cluster outage remains an external monitoring gap.
5. Approved redeploy persists configuration/data. Isolated backup/restore proves
   recovery integrity and observed RPO/RTO; replication is not backup. Coordinate
   #101/#105 instead of restoring over this working cluster.

No synthetic fixture, readiness condition or committed checklist is reported as
having passed these physical checks. Do not generate load, delete data, restore,
change tenant rights or send notifications without the concrete action approval.

[Grafana external Alertmanager behavior](https://grafana.com/docs/grafana/latest/alerting/set-up/configure-alertmanager/),
[Alertmanager configuration](https://prometheus.io/docs/alerting/latest/configuration/),
[ntfy publishing](https://docs.ntfy.sh/publish/).
