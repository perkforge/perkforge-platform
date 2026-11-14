# Integrated logging candidate, not deployed

The optional `local-integrated-logging` root extends `local-mattermost-pilot`,
retaining Portal, Nextcloud, query authentication and both notification mounts.
It enables the existing Big Bang 3.35.1 native Loki/Alloy pinned candidate without
replacing Grafana datasource values. Existing `query-runtime-values` supplies the
Prometheus override; do not import the older `logging-pilot` datasource list.
Grafana Loki browsing remains a separate additive datasource/whitelist/egress step.

Collection remains the existing opt-in `logging-pilot` namespace only, using API
logs, no host mounts or added capabilities, and the own-namespace Alloy operator.
Keep the existing TLS/authentication, 10Gi Longhorn claim and 72-hour retention.
No production namespace access or tenant grants are added by this source stage.

Before promotion compare the existing installer/runtime RBAC, TLS/auth delivery
and exact pinned images with the reviewed candidate. Verify request-based scheduler
headroom on CSI-capable workers, not CPU utilization: at the planning check neither
worker could accommodate Loki's 100m request. Do not bypass this with unreviewed
host CSI changes, arbitrary resource reductions, or the older logging root.

Promote only in the coordinator's window after preservation review. Verify native
readiness and controlled pilot ingestion/query before enabling Grafana log access.
Keep the same images and chart source across environments (BODA). Source publication
is not deployment, recovery proof, or completed #38 acceptance.

## Separately approved Grafana pilot consumer

`tenant-query/render-consumer.yaml` accepts explicit `grafana_loki_enabled: true`
and `grafana_loki_gateway_host: logging-loki-gateway.logging.svc.cluster.local`.
It preserves the authenticated Prometheus document and existing Secret references,
adds a separate immutable Loki provisioning document, and references existing
monitoring `loki-query-auth` and `loki-ca`. It appends only this gateway on port443
to the proxy whitelist and one Grafana-pod egress rule to the exact logging gateway
pods on target port8080. Default false leaves existing behavior unchanged.

Corey approved this exact additive pilot access batch. Runtime rendering/apply must
still be serialized with Mattermost's Grafana restart and retain both notification
mounts. Verify actual existing input compatibility before apply, then native
Prometheus health plus Loki ingestion/query and denied direct-backend access.
Credentials are existing manually staged inputs, not claimed ESO-managed. The
machine Loki identity has read/write tenant scope; this is platform-admin pilot
access, not authorization to expose a datasource to customer tenants or broaden
collection. No password/token value is rendered by this template or stored in Git.


## Immutable staged authentication input correction

The old immutable `logging/loki-gateway-auth` contains a literal backslash+n
suffix instead of a newline after its SHA512-crypt entry. It cannot authenticate
as-is. Existing source `logging-inputs.yaml` already rejects that malformed hash;
this is target data repair, not a password rotation or generator relaxation.

Preserve the old immutable Secret. Before selecting this root, stage corrected
`logging/loki-gateway-auth-v2`, retaining the exact username/hash and replacing
only the final two literal delimiter bytes with one newline. Require a single
entry, exact old UID/resourceVersion/data, and in-memory verification against the
existing protected query password before creation. Refuse an existing v2 object
unless exact payload/immutability already match. Keep all outputs secret-suppressed,
verify readback, and use the native chart's explicit v2 reference. No additional
users, password regeneration, role changes or Secret deletion is authorized by
this repair. The corrected input remains manual custody, not ESO management.
