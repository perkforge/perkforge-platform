# Observability architecture review — partial implementation, inactive

First draft for #35/#36, after #103 → #104 → #106 → #107. This is **not an
installation-ready stack** or completion of #37–40. No root/valuesFrom consumes
this folder; every candidate package is disabled and child reconciliation paused.
Architecture review precedes any activation. No credentials, collectors or
notification delivery are created. Myles' provisioner is excluded as requested.

## Inventory and source decisions

The selected Big Bang 3.35.1 supplies these exact package pins. `sources.yaml`
records downloaded official archive content SHA256s, not signature verification.

| Package | Chart / application |
|---|---|
| Prometheus Operator CRDs | 31.0.1-bb.0 / operator CRD app v0.93.1 |
| Monitoring | 91.4.1-bb.1 / operator app v0.94.0; kube-prometheus-stack 91.4.1 |
| Grafana | 13.2.4-bb.0 / Grafana 13.2.1 |
| Alloy | 4.3.2-bb.2 / k8s-monitoring 4.3.2 |
| Loki | 6.55.0-bb.9 / Loki 3.7.8 |

No competing tracked monitoring installer/configuration was found. The saved
03:33 UTC physical snapshot had RKE2 metrics-server, not Prometheus/Grafana/Loki/
Alloy. Keep metrics-server: its resource-metrics API is not a second Prometheus.
No new live inventory was taken. Existing household apps/Nextcloud are not proven
present by this review; do not manufacture healthy application metrics.

The historical render included a separate Alertmanager. The revised inactive
candidate disables it and Monitoring's bundled Grafana. Upstream PrometheusRules
remain for recording rules and reviewed migration of useful alerts. Grafana's
built-in Alertmanager owns the eventual single notification route. Exact revised
renders and installer/CRD compatibility checks are required before selection.

## Conservative starting budget — proposals, not measured ingestion

| Component | Initial request / memory limit | Persistent capacity / retention |
|---|---|---|
| Prometheus, one replica | 250m / 1Gi; limit 2Gi | 10Gi Longhorn; 7d and 8GB block cap |
| Grafana, one replica | 100m / 256Mi; limit 512Mi | 1Gi Longhorn; Git owns configuration |
| Loki, proposed single-binary | review ~100m / 512Mi; limit ~1Gi | propose 10Gi, 3d initially; **not configured/validated yet** |
| Alloy, node log collection | review ~50m / 128Mi per worker/node as scoped | bounded durable positions; **not configured/validated yet** |

The actual node snapshot showed low load: control 4.44Gi, workers ~1.6Gi RAM,
15.2Gi allocatable each. Requests are not usage; numerous existing containers have
no requests/limits. Measure peak ingest/cardinality before accepting this budget.
The 21Gi proposed monitoring/logging claims cost roughly 42Gi scheduled with two Longhorn
replicas, before snapshots and actual store overhead. Including queued OpenBao/
Keycloak and retained test claim gives ~36Gi logical, ~72Gi replicated scheduling.
Shared worker OS disks reported ~222Gi available each, ~70.7Gi reserved; these
figures are not additive logical capacity or a dedicated storage pool.

Prometheus time/size limits remove old blocks at the first applicable limit; WAL
and compaction need additional headroom. The 8GB cap is below the 10Gi filesystem,
not a guarantee against full disk. Loki sizing must include chunks/indexes/WAL,
compaction and deletion delay. Alert on free capacity, growth and failed ingest/
retention before exhaustion; no alert authorizes deletion. Prefer narrow scrape
scope/low-cardinality labels and opt-in log filtering over blind truncation.
Security/audit evidence retention belongs to #22 and cannot silently inherit the
short operational metrics/log policy. No Mimir, object-store cluster or HA stack
is added by this draft.

## Who does what and why

Big Bang/Flux owns deployment; reviewed Ansible prerequisites own delegated
installer identities and separately approved app API configuration. Do not give
the ordinary root RBAC self-grant. Native Grafana provisioning is the initial
review candidate, with one owner for each datasource/dashboard/rule. No external
provisioner or competing manual API owner. Six dashboards remain to implement:
cluster, workloads, tenants, Nextcloud, logging and alerting.

Alloy → Loki and exporters → Prometheus → Grafana are separate data paths.
Alloy's pinned package wraps k8s-monitoring and includes an Alloy operator path;
review required CRDs/RBAC and disable duplicate metrics collectors before use,
rather than assuming it is only a simple log DaemonSet. Loki's storage/auth/proxy
configuration also needs a full child render and security tests; no speculative
filesystem/retention settings are presented as tested here.

Initial Grafana is platform-admin only with an external `grafana-admin` Secret
reference; anonymous and OIDC access remain off. Keep UI/ingestion routes closed.
No token/password is generated. Later tenant access needs real datastore/query
boundaries: dashboard variables/folders alone are not isolation. Loki
`auth_enabled` checks tenant headers, not user authentication; a trusted auth
proxy must derive/overwrite tenant identity, deny bypass and cross-tenant queries.
Network policies and actual deny tests are required, not assumed from labels.

Collect only explicitly approved workloads initially. Exclude credential-bearing
bootstrap/auth logs until producer logging and security/audit handling are
reviewed. Redaction is defense in depth, not proof that arbitrary secrets cannot
leak; collectors are trusted host/API readers. Never collect private key/config
files as logs. Tenant/app labels must be bounded; don't label per-request IDs or
secret/user content. Ingest failures and dropped/noisy records need visible counts.

## Alert/notification decision — one path, not duplicate delivery

Owner decision: Grafana-managed rules → Grafana built-in Alertmanager → one
authenticated TLS ntfy contact point. No separate Prometheus Alertmanager or
external Alertmanager datasource/forwarder is selected. Preserve useful upstream
rules: keep recording rules in Prometheus, inventory alert expressions and import
reviewed alerts into Grafana against datasource UID `prometheus`. Prometheus does
not push arbitrary external alerts into Grafana's built-in manager. Source rules
must not acquire a parallel notification route. Compare labels, pending periods,
recording-rule dependencies, no-data/error handling and resolved behavior before
claiming alert coverage. Imported rules need a single Git/API owner and stable IDs.

Native Grafana webhook custom payloads and ntfy templating are candidates; a
separate adapter is not assumed necessary. Pinned-version payload compatibility,
exact endpoint/topic and protected publisher credentials remain unverified.
Delivery stays unarmed until firing/resolved, grouping/repeat, silence expiry,
credential/TLS denial and bounded failure tests pass. Whole-cluster/network failure
needs independent detection. No credentials or contact point are created here.

See [Grafana rule import](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/alerting-migration/),
[Grafana webhooks](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/webhook-notifier/)
and [ntfy publishing](https://docs.ntfy.sh/publish/). These describe available
mechanisms, not successful acceptance of this pinned inactive deployment.

## Remaining staged work and acceptance

1. Review architecture/budgets/ownership (#36), exact CRD/operator compatibility,
   chart lookups and rendered roles/bindings. No activation from these examples.
2. Implement scoped installer/metrics/Grafana provisioning and six dashboards
   (#37). Validate control-plane scrape endpoints/TLS and prevent duplicate stores.
3. Implement constrained Alloy/Loki storage, retention and ingestion/query auth
   (#38), with representative ingest/cardinality and positive/negative tests.
4. Implement one notification path, pinned compatible integration and protected
   inputs (#39); test firing/resolved, deduplication, silence and failed delivery.
5. Separately approve a pilot; verify all-node metrics/log query, tenant denial,
   resource/retention behavior, redeploy persistence and actual isolated restore
   (#40/#101/#105). Replication/redeployment is not backup/restore evidence.

The inactive YAML is actual native Big Bang input for review, not new automation.
The original architecture draft validated outer selection/local child renders.
The [metrics implementation](metrics.md) now adds checksummed Monitoring/Grafana/
CRD fetch/render and installer audits to CI. Alloy/Loki and full-stack deployment,
tenant auth or alerts are not proven.
Those missing pieces are why this is an honest architecture/partial-config draft,
not five claimed completed implementation MRs.

Sources: [Big Bang](https://docs-bigbang.dso.mil/),
[Prometheus storage](https://prometheus.io/docs/prometheus/latest/storage/),
[Grafana external Alertmanager](https://grafana.com/docs/grafana/latest/alerting/set-up/configure-alertmanager/),
[Alertmanager UI limitations](https://grafana.com/docs/grafana/latest/datasources/alertmanager/),
[Loki authentication](https://grafana.com/docs/loki/latest/operations/authentication/),
[Loki tenancy](https://grafana.com/docs/loki/latest/operations/multi-tenancy/).

## Queued SSO and machine access

[sso-review.yaml](sso-review.yaml) records disabled Grafana OIDC and explicit
per-app/tenant authorization gates. Big Bang/Flux deploy apps; Ansible owns future
reviewed clients/native settings. The merged three-app adapter does not yet accept
these new clients: no hidden generic apply or realm import is provided here.
Each implementation draft carries its own values/proposal and tests; none creates
credentials, users, groups, grants or live ingress.

Grafana is the human entrypoint. Prometheus/Loki/Alloy/Alertmanager/ntfy machine
interfaces remain internal with separately scoped credentials; do not invent a
browser login or assume Grafana login protects a directly exposed backend. Tenant
roles require org/datasource and query/write isolation, not dashboard hiding or
Loki namespace labels. Existing recovery and stale-session denial need live tests.
Velero has no independent web login/client: operators use Kubernetes API/RBAC;
its controller identity and backup-store credentials are separate privileged
boundaries. It remains evaluation-only, with no install or new service account.

Sources: [Grafana OAuth](https://grafana.com/docs/grafana/latest/setup-grafana/configure-access/configure-authentication/generic-oauth/),
[Velero restrictive RBAC](https://velero.io/docs/v1.18/rbac/).
