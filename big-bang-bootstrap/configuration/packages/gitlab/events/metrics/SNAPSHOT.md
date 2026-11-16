# Inactive pipeline-only snapshot consumer

Separate from the unchanged legacy exporter/rules templates. Requires the reviewed
opt-in `gcpe_pipeline_snapshot_*` collector fork, not stock v0.6.0. No image,
service, scrape, credential, project or rule has been activated by these files.
The synthetic example disables snapshot polling; every Grafana rule remains
paused regardless of that flag. No selected GitOps root imports these templates.

Validate literal inputs with `verify_snapshot_inputs.verify` before Ansible/Jinja
rendering, and again at any future setup boundary. Unknown fields, per-target
URLs/tokens, non-push sources, wildcard refs, conflicting ID/path mappings and
more than 16 targets fail closed. Each exact branch is anchored/escaped in the
upstream project's scope. Jobs, child pipelines, variables, reports, environments,
tags, merge requests, wildcard discovery, Redis, pprof, webhooks, OpenTelemetry
and legacy pull scheduling are disabled. TLS verification stays on; only one
reviewed HTTPS GitLab origin is configured. Runtime token custody/delivery,
private CA, network and platform-only scrape/query access need separate approval.
No credentials are rendered; `snapshot_enabled` is not an authorization grant.

## Stable incident and operator health

Per target, exact static `project_id/project/ref/source` selectors are reduced to
one unlabeled result, with operator-authored context/project/incident labels.
Raw pipeline IDs, usernames, messages, URLs, timestamps and error bodies are not
notification labels or annotations. Duplicate samples fail closed (single
collector/scrape required; HA is unsupported).

The incident returns **1 only for failed**, **0 only for success**, and only while
valid=1, present=1, completion timestamp>0 and observation age is nonnegative and
within the selected freshness bound. Running/canceled/unknown/empty/error/stale
states yield no data. Grafana `KeepLast` on no-data/error must preserve an existing
incident, not announce recovery. This does not prove Grafana state persistence or
notification lifecycle. The separate operator-health rule detects missing,
invalid or stale observation telemetry, including process-reachable but unhealthy
polling; it is paused too, uses a 1-minute hold and Alerting on query/no-data error.
Fresh observed pipeline absence is not an API failure.

Freshness is at most three polling intervals and is not an event-delivery SLA.
Collector monotonic age and valid-bit clock guards are required; timestamp alone
is not proof of a recent poll. Latest-state sampling can miss intervening failures.
No scan/deployment coverage is claimed by this pipeline-only tranche.

## Tests and remaining gates

`PROMTOOL=/path/to/already-installed/promtool PYTHONPATH=big-bang-bootstrap/tests
python3 -m unittest configuration.test_gitlab_snapshot_metrics
configuration.test_gitlab_metrics -v`

Offline tests cover exact inputs/default-off and unchanged legacy behavior. The
optional native Prometheus test evaluates rendered expressions against synthetic
failed/success/running/canceled/empty/error/stale/cold/missing vectors. Without
PROMTOOL it explicitly skips rather than claiming native evaluation. It does not
exercise real GitLab, Grafana lifecycle, delivery, permissions or deployment.

Before activation: freeze/review collector ABI and artifact provenance, parse this
rendered config with that exact collector, independently review consumer rules,
then test real scoped API permission and lifecycle/delivery in an explicitly
approved rollout. BODA means the same reviewed collector artifact with selected
target configuration; no environment-specific rebuild or private-only config.
