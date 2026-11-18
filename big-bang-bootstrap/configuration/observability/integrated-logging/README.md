# Integrated logging: deployed platform pilot

## Current evidence reconciliation (2026-11-18)

This checkpoint supersedes the collection-scope, manual-custody and retention-wait
statements in the dated initial pilot below; it does not authorize a rollout or
claim that every original #38 acceptance item is complete. Later deployed evidence
includes cluster-wide API discovery, separate writer/readers with exact-record
OpenBao/ESO custody, guarded Portal ownership epochs and native org-Viewer
own/foreign-query and revoked-token checks. See the [current handoff](../../../../HANDOFF.md#current-scoped-observability-checkpoint-2026-11-14)
and [architecture evidence](../architecture-current.md).

### Scheduled natural retention verification

The read-only check on November 18 at 15:39–15:44 UTC used the saved fresh
control's exact original historical range, not a sliding last-hour query. Its
November 14 06:51:37 UTC timestamp had a positive query baseline after the prior
controlled backend restart. The selector returned HTTP 200/success with zero
entries after 72 hours plus the asynchronous deletion delay. The aged control
never had a positive baseline and is not deletion evidence.

Corroboration, rather than absence alone:
- The ordinary platform-scoped query returned five current entries; Loki readiness
  returned 200/ready and Loki/gateway/Alloy Pods were Ready. The old canary-only
  reader has no ordinary application streams; its empty result is not an outage.
- Active runtime configuration retained enabled 3-day retention, 2-hour deletion
  delay, 10-minute compaction and `max_query_lookback: 0s` (no lookback cutoff).
- The running compactor reported 388 successful retention operations, latest at
  15:30:58 UTC, and a deleted-table counter for the canary tenant/day. The sweeper
  reported 397 marker files deleted and zero currently pending/processing files.
- One cumulative retention-operation failure remains in the counters. Subsequent
  successes continue; available logs did not establish a current matching failure.

Together these support natural pruning of the positively baselined control. They
are not forensic proof identifying its exact physical chunk deletion, nor proof
of lossless ingestion or disaster recovery. No log was manually created/deleted,
and no retention policy, workload or credentials were changed for this check.

### Acceptance disposition, not scope expansion

| Item | Evidence / remaining owner |
|---|---|
| Native ingestion, TLS/auth query, narrow synthetic redaction and backend restart persistence | Dated pilot below; retain its explicit proof limits |
| Scoped custody, real collection and native tenant-machine denials | Current handoff; [boundary stages](../log-boundary/phase-a/README.md), [Portal query acceptance](../log-boundary/phase-b/README.md) and closed design [#218](https://github.com/perkforge/perkforge-platform/issues/218) |
| Cursor migration and fresh delivery | [Retained cursor evidence](../alloy-cursors/README.md); not a delivery WAL or full restore |
| Natural retention pruning | November 18 corroborated check above; scheduled waiting gate satisfied |
| Representative growth, aggregate capacity and noisy-source decisions | Owner-directed Planning [#466](https://github.com/perkforge/perkforge-platform/issues/466); existing short observations are not representative daily sizing or an enforced aggregate cap |
| Tenant-human and session/offboarding matrix | Owner-directed Planning [#475](https://github.com/perkforge/perkforge-platform/issues/475), following accepted pilot scope of #43; do not repeat proved machine tests as missing |
| Full restore/load/rollback and integrated evidence consolidation | Owner-directed Planning [#478](https://github.com/perkforge/perkforge-platform/issues/478), following accepted baseline of #40 |
| Ordered identity/collection/query C4 | [Architecture flows](../architecture-current.md#six-dashboard-plan-and-ordered-flows) and [final Portal rollout evidence](../../../clusters/local-portal-pilot/README.md#verified-final-current-state-rollout-2026-11-14); broader consolidation remains #478 |
| Comprehensive redaction review | Still unresolved in #38: no explicit transfer or completed comprehensive review found |

The current processing pattern targets `password`, `token` and `secret` key/value
shapes; its synthetic pass does not detect arbitrary credentials, structured
variants or all sensitive data. Do not silently mark comprehensive redaction
complete or invent a policy to discard security/debug records. Resolve that exact
requirement's disposition before closing #38. This documentation does not close
#38, reopen accepted #36/#40/#43 scope or start any Planning follow-up.

### Offline native redaction matrix (2026-11-18)

Alloy v1.18.0, revision `a435563`, ran a bounded local fixture at 17:36 UTC:
synthetic file source → the existing `stage.replace` expression → `loki.echo`.
Configuration validation passed, all ten input lines appeared in native output,
and the fixture exited cleanly. It used temporary local state, an empty Kubernetes
configuration and loopback-only HTTP, disabled usage reporting, and no Loki write
endpoint or real credentials. Temporary state was removed after the process exited.
This is a native processing-stage test, not a new live Kubernetes pipeline test.

| Synthetic input shape | Native result |
|---|---|
| `password=synthetic-one` | `password=REDACTED` |
| `TOKEN: synthetic-two` | `TOKEN: REDACTED` |
| `secret = synthetic-three` | `secret = REDACTED` |
| `password=first,token=second;secret=third` | All three values replaced |
| `benign_message=hello` | Preserved unchanged |
| `{"password":"synthetic-four"}` | Unchanged: quoted JSON key not covered |
| `Authorization: Bearer synthetic-five` | Unchanged: bearer header not covered |
| `api_key=synthetic-six` | Unchanged: different key not covered |
| `password=two words` | `password=REDACTED words`: whitespace suffix remains |
| `password="two words"` | `password=REDACTED words"`: quoted whitespace suffix remains |

The fixture confirms the narrow behavior and concrete gaps, not that real secrets
were observed in stored logs. No processing rule was changed. A decision remains:
accept this documented bounded policy for the current baseline with an explicit
broader-coverage follow-up, or require selected common formats to be addressed and
tested before #38 closure. Earlier practical-redaction intent is not silently
substituted for the later comprehensive-review criterion.

### Proposed bounded redaction extension (not deployed)

The local source candidate extends the existing explicit-key policy to quoted
JSON/text values (including escaped quotes and spaces), `api_key`/`api-key`, and
Authorization Bearer/Basic credentials. Separate quoted stages precede unquoted
values; explicit key boundaries avoid matching `token_count`, `secretary` or
`some_api_key`. Valid JSON string values keep their surrounding quotes. No chart
secret-discovery feature, collector access, tenant scope, retention or runtime
resource setting is changed. The November 18 baseline matrix above describes the
old running rule, not this unadopted candidate.

`tests/integration/test_logging_redaction_native.py` loads the source-owned stages,
checks both generated boundary profiles preserve them, and runs 24 exact synthetic
input/output cases using pinned Alloy v1.18.0/a435563. Set `ALLOY_VALIDATE_BIN` to
the verified binary; the native test explicitly skips without it. The two tests
passed locally, including JSON validity checks. This is not full CI, pinned
umbrella rendering or production-pipeline acceptance.

URL/query and bracket-delimited sensitive keys retain the prior broad value-tail
redaction; this can remove trailing nonsensitive query fields or a closing bracket.
Unquoted multiword values remain ambiguous, unterminated quoted values are not
covered, and arbitrary unknown keys/formats are not detected. Sensitive-key
nonstring JSON values are left unchanged. A benign field deliberately named
`token` is still redacted: key semantics, not entropy, determine coverage. New
coverage requires review; no retrospective stored-log cleanup is proposed.
Publication, live GitOps adoption and any synthetic end-to-end verification remain
separate actions. No closure or comprehensive secret-detection claim follows from
these offline cases.

## Initial integrated pilot (historical)

The optional `local-integrated-logging` root extends `local-mattermost-pilot`,
retaining Portal, Nextcloud, query authentication and both notification mounts.
It enables the existing Big Bang 3.35.1 native Loki/Alloy pinned candidate without
replacing Grafana datasource values. Existing `query-runtime-values` supplies the
Prometheus override; do not import the older `logging-pilot` datasource list.
Grafana Loki browsing uses the separately approved additive datasource/whitelist/egress configuration below.

Collection remains the existing opt-in `logging-pilot` namespace only, using API
logs, no host mounts or added capabilities, and the own-namespace Alloy operator.
Keep the existing TLS/authentication, 10Gi Longhorn claim and 72-hour retention.
No production namespace access or tenant grants are added by this source stage.

Before promotion compare the existing installer/runtime RBAC, TLS/auth delivery
and exact pinned images with the reviewed candidate. Verify request-based scheduler
headroom on CSI-capable workers, not CPU utilization. The reviewed optional
Flux placement overlay moved only stateless kustomize-controller to the existing
control-plane role, freeing 300m on a worker without changing its resources.
Loki remains on a CSI-capable storage worker; Alloy/operator are on the control
node. Do not substitute unreviewed host CSI changes, resource reductions, or the
older logging root. Actual requests including the generated config-reloader are
235m CPU / 882Mi memory across logging components, plus a 10Gi Loki PVC.

Promote only in the coordinator's window after preservation review. Verify native
readiness and controlled pilot ingestion/query before enabling Grafana log access.
Keep the same images and chart source across environments (BODA). Source publication
is not deployment, recovery proof, or completed #38 acceptance.

## Verified physical acceptance, 2026-11-14 07:11 UTC

This is a platform-admin pilot, not completed ticket #38 or tenant-wide logging.
Big Bang 3.35.1 supplies Loki 6.55.0-bb.9 and Alloy 4.3.2-bb.2 with their pinned
Registry1 images. The selected integrated root preserves current Portal,
Nextcloud, Mattermost, enrollment and notification routing.

Verified on the actual cluster:
- Loki backend/gateway, Alloy operator and generated two-container collector Ready.
  Collector and reloader are nonroot, drop ALL, forbid privilege escalation and
  use read-only roots with RuntimeDefault seccomp. No host PID/network/path access.
- Operator watches only `alloy`; collector service account can read pod logs only
  in `logging-pilot`, not Nextcloud's namespace, and cannot list pilot Secrets.
- A bounded opt-in synthetic pod's lines traversed Alloy → authenticated TLS
  gateway → Loki → Grafana's native datasource proxy. Proxy returned HTTP 200;
  synthetic password values were replaced with REDACTED while ordinary fields
  remained. An otherwise identical unopted pod yielded no collected lines.
  Both disposable pods were removed. This narrow pattern test is not proof that
  arbitrary secrets are automatically detected or that opt-in labels are ACLs.
- Trusted-CA native query succeeds; wrong credentials return 401. A caller-supplied
  tenant header cannot override the gateway's authenticated identity. No tenant
  datasource/access grant was added.
- A known direct-push sentinel's exact timestamp and line survived one controlled
  native Loki restart with the same PVC UID and bound volume. This is restart
  persistence, not replicated disaster recovery or durable Alloy offset proof.
- Grafana Loki and Prometheus native health both pass; all 41 dashboards remain.
  Existing application readiness is retained. PVC observed 264KiB used of 9.8Gi
  usable during synthetic validation, not a production growth forecast.

Still open: representative ingestion/growth and noisy-debug policy, comprehensive
redaction review, actual retention deletion evidence, tenant access integration,
and final ordered identity/collection/query C4 acceptance. Retention is configured
72h with working compactor/delete-store configuration and a 2h deletion delay;
configuration and an absent old query are **not** proof of storage pruning. A
benign aged/fresh control was accepted, but the aged record did not establish a
positive query baseline, so no deletion success is claimed. Runtime credentials
remain manually staged, not ESO-managed. Optional logging-specific metrics/rules
are disabled; existing Prometheus monitoring is unchanged.

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
Prometheus/Grafana). No monitoring-object installer grant is widened. The separate metadata-only
lookup grant is documented below. Existing dashboards are kept;
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

Grafana's datasource URL uses explicit `:443` to match its exact
`data_source_proxy_whitelist` entry. Datasource health alone did not exercise the
proxy allowlist; acceptance must also query a benign collected line through the
native Grafana datasource proxy. This changes no destination, TLS trust,
credential, network policy, or existing Prometheus path.
