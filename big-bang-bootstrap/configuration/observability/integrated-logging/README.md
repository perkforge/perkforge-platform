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
