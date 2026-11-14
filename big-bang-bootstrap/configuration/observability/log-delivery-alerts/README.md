# Log-delivery health alerts (#449)

Native Prometheus scrape plus Grafana rules, routed through the **existing**
`platform-resource-ntfy` contact point. Its ntfy and Mattermost receivers are
preserved byte-semantically; no new notification policy or parallel Alertmanager
route is created. Alert links open the native Grafana rule and the org1 pod-log
dashboard. Account permissions still apply.

Apply the exact `servicemonitor.yaml` through the authorized foundation owner only
after confirming the current cluster UID and no conflicting existing object.
It targets only the existing Alloy collector service/metrics port and retains
only delivery counters and the separately labeled native processing-exclusion counter. Prometheus-generated `up` is not removed by metric
relabeling. Existing Prometheus selectors and connectivity must be verified;
this manifest grants no RBAC or network access. Do not broaden the installer.

Before arming, prove the live Prometheus target is up and each required counter
exists with namespace=alloy/service=alloy-alloy-logs. Port-forwarded metric output
alone is not durable monitoring. The source's 1000-sample limit bounds unexpected
series growth; an exceeded scrape limit becomes unavailable telemetry, not
silently healthy collection.

* Drops: reset-safe five-minute dropped-entry rate positive for ten minutes.
* Retries: reset-safe five-minute retry rate positive for fifteen minutes.
* Telemetry: five-minute down/absent-target or missing-counter lookback, sustained
  another five minutes. This also detects a changed/missing metric name.

A single short catch-up event does not satisfy the sustained rate durations.
Repeated catch-up losses can still alert and require investigation. HTTP400 may
reject mixed-age batches; do not claim only old entries were lost. No retention,
ingestion age bound, collection opt-out or application filtering is changed.
Rate rules keep their previous state on absent data, with the dedicated missing
telemetry rule covering that condition; datasource evaluation errors remain
explicit Error. A brief scrape interruption does not create duplicate immediate
NoData pages for every counter rule.

`render.yaml` is default-off/check-mode inert and creates rules-only output, no
credentials. `update.yaml` is separately default-off and requires explicit update
approval, expected cluster/Bao identity, current exact record hash, existing ESO
binding and current operator authentication. It CAS-adds only the reviewed group
inside the existing `grafana-platform-alerts` record, preserving all receivers
(including the newly added Mattermost destination) and other rule groups. Verify
exact ESO payload and native Grafana provisioning after the coordinated reload.
Do not induce production drops to test an alert; use native synthetic rule tests
and clearly distinguish actual target/rule evaluation from notification delivery.

The drop/retry query returns the actual reset-safe summed rate, not a boolean;
Grafana's existing C > 0 threshold and persistence windows are unchanged. The
notification summary includes the five-minute rate in entries/s or retries/s,
formatted to six significant digits; nonfinite values display unavailable.
This is a rate, not an inferred count or proof that every rejected batch entry
was lost. The missing-telemetry rule remains a status condition.

These rules cover writer delivery and missing scrape/counter telemetry, not
source discovery completeness. Pinned Alloy v1.18 Kubernetes API source health
only indicates valid configuration and exposes no source-specific debug metrics;
per-target last-line/error metadata requires separate coverage design. Do not
interpret scrape up=1 as proof every intended pod is being collected.
