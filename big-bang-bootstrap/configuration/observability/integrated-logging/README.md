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


Native umbrella monitoring defaults would add Loki PrometheusRules/ServiceMonitors
and Alloy ServiceMonitors outside the existing installer authority. This pilot
explicitly disables only those optional logging monitoring objects (not existing
Prometheus/Grafana). No installer grant is widened. Existing dashboards are kept;
new logging exporter scraping/rules remain a separately reviewed follow-up.


The integrated override explicitly retains existing `private-registry` references
for Loki and Alloy/operator/collector. The umbrella has no embedded registry
credentials and otherwise emits empty references over child defaults. This uses
existing namespace-local immutable pull Secrets; it does not rotate credentials,
change pinned Registry1 images or grant access to another namespace. Native umbrella
regression tests cover both Pod templates and the Alloy custom resource.


The local integrated profile selects the existing RKE2 DNS service name
`rke2-coredns-rke2-coredns` through the native Loki `global.dnsService` value.
The chart default `kube-dns` Service does not exist in this cluster. This is
environment configuration, not an image rebuild, IP pin or DNS/network change.
Other environments select their existing DNS service through their own values.

### Pinned Alloy platform-detection metadata

The pinned Alloy 4.3.2-bb.2 dependency calls `validations.platform.detect`
unconditionally from `_platform_validations.tpl` during server-side Helm
rendering. Its `lookup "v1" "Node" "" ""` requires cluster Node **list** even
on RKE2; setting `global.platform` only affects a separate resolver and does not
skip this validation. Offline Helm rendering cannot establish that permission.
The logging prerequisite adds the separate `alloy-installer-platform-detection`
ClusterRole and binding: core `nodes`, **list only**, bound exclusively to
`bigbang:alloy-installer`. The Node rule grants no get/watch/write, Secret access, or authority
to the operator/collector. It exposes node metadata to the installer, not pod logs.
Apply this source-owned prerequisite before retrying the native release; retain
all existing scopes. Reassess when Big Bang updates its pinned dependency to
support detection without this lookup. Do not falsify platform capabilities or
patch the upstream chart to bypass its validation.

The same pinned chart also performs a cluster-wide Deployment lookup for its
optional operator conflict check. The scoped local overlay disables that native
`upstream.alloy-operator.conflictCheck` check, **not** the operator's namespace
boundary. Before first activation or adding another operator, the platform
operator must inspect existing Alloy operator deployments and their
`WATCH_NAMESPACE` settings and verify no overlap; the installer is deliberately
not granted cluster Deployment visibility. The physical target was checked with
no existing Alloy operator before this activation. `ownNamespaceOnly: true`
remains mandatory. Upstream Helm NOTES additionally reads the release Namespace
for Istio metadata; the metadata role permits **get only** on the single
`alloy` Namespace, not list/watch or any Namespace mutation. This grant is only
for `bigbang:alloy-installer`, never the operator/collector.

### Restricted synthetic acceptance images

The `logging-pilot` namespace needs its own pull credential even when the pinned
Registry1 test image appears cached. Do not bypass kubelet credential checks.
After approval, `configuration/ansible/logging-canary-registry.yaml` copies only
the existing immutable Registry1 payload from `logging/private-registry` into
`logging-pilot/private-registry`, with hidden stdin, exact namespace/cluster
checks, immutable owned-repeat equality and readback. Default/check mode does
nothing. Set `logging_canary_registry_apply=true` and the independently verified
`logging_expected_cluster_uid`. No password rotation, new registry authority,
operator/collector permission, or automatic ServiceAccount modification occurs.
Bounded restricted synthetic pods explicitly reference this Secret; clean up only
the temporary test pods after acceptance. The pull Secret remains for repeatable
acceptance and must never be committed or printed.

The enabled `alloy-logs` collector explicitly receives the pinned Big Bang
chart's restricted singleton config-reloader posture (UID/GID 65534,
no privilege escalation, drop ALL, RuntimeDefault seccomp, read-only root).
The same native image/version is retained; namespace Pod Security is not relaxed.
Alloy itself retains UID/GID 473 and its restricted context. A bounded 64Mi
`emptyDir` at `/tmp/alloy` permits its runtime state while preserving the
read-only root and existing read-only Loki CA mount. This state is ephemeral,
not a claim of durable collector offsets. Native Helm Ready alone does not prove
that the operator-generated collector passed admission or collected logs.
