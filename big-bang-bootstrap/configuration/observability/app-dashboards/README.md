# Per-application resource dashboards (#37)

Default-off Ansible renderer emits native Grafana file-provider values. No API,
credentials, grants, scrape configuration or selected-root changes. Explicit
profile maps 19 platform/managed apps to exact namespaces; each includes supporting
workloads and jobs in that namespace, not an inferred business-service boundary.
This inventory is source-owned, not dynamic discovery. Review additions and shared
namespace ownership; controllers and ephemeral test namespaces are not silently
advertised as managed applications.

Run `render.yaml` with `-e @platform-profile.yaml`, explicit
`app_dashboards_render=true` and absolute `app_dashboards_output`. Rendered
`helm-values.yaml` adds only unique dashboardProviders/dashboards map entries.
Recursively merge with existing complete values; do not replace maps or provision
through a competing API owner. Nothing selects the output automatically.

## Access gate before any rollout

The intended audience is platform administrators only. Org1 is necessary but NOT
sufficient: existing platform engineers are Viewers in org1. Before activation,
verify native folder permissions for `pf-platform-apps` exclude non-admin access,
including inherited defaults, and confirm actual Viewer direct UID/search denial.
This renderer does not create that ACL or claim it exists. Folder visibility does
not restrict existing datasource query authority: the existing shared Prometheus
access must be documented separately, not presented as new data isolation. No new
tenant datasource or access is created. Do not activate until reviewed access and
source-owner preservation evidence is complete.

## Panel source contract

| Panels | Source / label contract |
|---|---|
| CPU / working-set memory | kubelet `/metrics/cadvisor`, exact namespace, nonempty/non-POD container; max per namespace/pod/container deduplicates duplicate scrapes |
| Requests / limits | kube-state-metrics resource/unit and namespace/pod/container; unset limits are absent, sums can be partial |
| Ready containers / restarts | kube-state-metrics per-container ready gauge and reset-safe15m increase |
| Desired / available replicas | separate Deployment/StatefulSet native gauges; CNPG/custom controllers may not expose these and remain unavailable |
| Pod count | kube-state-metrics unique namespace/pod; includes support/jobs, not desired replica count |
| PVC used / capacity | kubelet volume stats deduplicated by namespace/claim, not multiplied by pods sharing a claim |
| Network receive / transmit | cAdvisor sandbox series `container=""`, max per namespace/pod/interface; loopback and hostNetwork pods excluded via verified kube_pod_info label |
| Sample age | kube-state-metrics timestamp age, separate from application health |

Network bytes are not HTTP requests, latency or users. The actual cluster had no
`traefik_service_requests_total` series at verification; app-attributed HTTP panels
are deliberately not invented. Native ingress/app exporter integration needs its
own approved source and attribution tests. HostNetwork app traffic is explicitly
unavailable here; collecting it twice as app traffic would be misleading.

No `or vector(0)`, value substitution or connected-null graph disguises missing
series as healthy zero. Grafana no-value text is Unavailable. Historical windows
remain historical; sample age and scrape health must be inspected before treating
a displayed point as current. This is not a complete per-source freshness/coverage
alarm. Unset resource limits are not zero limits or a finite aggregate cap.

## Evidence and remaining acceptance

2026-11-14 read-only native Prometheus query checks:45 panel queries across
Nextcloud, Portal and Loki returned HTTP200. CPU/memory/readiness/network series
were present; no-PVC Portal and no-StatefulSet Nextcloud panels correctly returned
no series. These are current data availability checks, not controlled traffic or
app-down testing. Native PromQL regression proves duplicate sandbox scrapes are
not double-counted, hostNetwork excluded, and absent app produces no synthetic zero.
Local checksum-pinned Grafana13.2.1 file import verifies native provisioning shape.

Before rollout: review exact native chart mounts/preserved dashboards, administrator
folder ACL, bounded query cardinality/latency and actual rendered source refs.
After separately approved rollout, verify native panels/no-data and safe controlled
representative changes; do not stop household apps to manufacture evidence.
Six starter dashboard expansion, wider scrape gaps, HTTP attribution, representative
ingestion/cardinality/growth and #40 recovery remain separate #37 acceptance work.

## Reviewed activation candidate (not selected by source publication)

`local-app-resource-dashboards` inherits `local-private-observability`, preserving
sharing disabled, durable Alloy, Portal Viewer mapping, all existing receivers
and datasources. The generated runtime values add one ConfigMap/reference only;
regeneration is tested byte-for-byte from the same explicit profile/templates.
Native pinned chart renders preserve existing objects, mounts and container fields.

Before selection, run the separately approved `prepare-folder.yaml` with protected
existing admin credentials, trusted CA and verified org name. It defaults off and
check-mode inert, refuses populated folders or unexpected user/team permissions,
and requires an explicitly verified existing folder ID on retry. It creates only
the missing fixed empty folder and narrows its permissions to native Admin. Never
provision dashboards first and restrict later: native tests reproduced cached
previous Viewer access after an ACL change. The safe sequence fixture proves an
already-authenticated Viewer and a fresh Viewer both denied after Admin-only ACL
is installed BEFORE file provisioning; Admin succeeds. This does not prove general
permission-cache revocation or restrict preexisting shared datasource rights.

All19 inventory apps were checked with285 live read-only queries across the first
15 panels: every query HTTP200, with9–15 nonempty panels per app. Missing custom
controller/hostNetwork/PVC sources are not fabricated. The final57 desired-replica/pod-count companion queries also returned HTTP200
(44 nonempty); thus342 final-profile queries were checked across19 apps.
No real app-down/traffic disturbance was induced for these checks. See the dated
production activation checkpoint below.

## Verified deployment checkpoint: 2026-11-14 20:14 UTC

Reviewed #468/#471/#472/#474 are deployed at immutable source
`9d00708108d3fdff3f883a10e4e2f3436a347ea4`, selected root
`clusters/local-app-resource-dashboards`. The empty fixed folder was created and
verified with exactly native Admin permission4 before root selection. The native
API-created folder includes a creator-user grant; the guard accepts only the
verified current global administrator's permission4 and then replaces it with the
Admin role. Missing native `role` fields are normalized without accepting another
user/team or inherited grant. No dashboards were exposed during failed preflights.

Grafana Helm release14 became Ready at20:14:24. Actual readback verified all19 new
provisioned dashboards under the restricted folder, each accessible to the admin;
all42 previous org1 dashboard UIDs were preserved (61 total). Existing org1
Prometheus and both Loki datasource health checks passed,12 managed rules remained,
and snapshot/external-snapshot/public-dashboard flags stayed disabled. Durable
Alloy remained on the same pod with zero restarts; Nextcloud was Ready.

No additional live Viewer account was created by owner direction. Live effective
ACL readback plus checksum-pinned native preauthenticated/fresh Viewer UID/search
denial tests support the scoped UI acceptance; an actual production Viewer browser
probe is not claimed. Existing datasource query rights are unchanged, not newly
isolated by this folder. Owner visual acceptance is separate from API proof.

#37 remains broader than this delivered tranche: representative capacity/cardinality,
wider scrape gaps, controlled traffic/app-down validation and missing HTTP attribution
are not completed merely by these dashboards. No new load, app outage, retention
change or grant was introduced to manufacture acceptance.
