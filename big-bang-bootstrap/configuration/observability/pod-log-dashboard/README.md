# Pod-log browsing dashboard — source only

Tracks [logging #38](https://github.com/perkforge/perkforge-platform/issues/38) and
[tenant query boundaries #218](https://github.com/perkforge/perkforge-platform/issues/218).
This adds an actual Loki logs panel, log-volume graph, selected-range count and
chained namespace/pod/container filters. It does not replace the existing
`pf-logging` metrics dashboard or automatically provision anything.

## Authorization comes first

The renderer requires an **explicit reviewed datasource UID and Grafana org ID**.
It has no shared/pilot datasource fallback or browser datasource chooser. The
same dashboard definition is rendered for each org; identity and backend scope
are configuration, never a rebuilt application image. No credential, datasource,
user, org, role, namespace mapping or gateway permission is created here.

Namespace/pod/container controls are navigation filters, **not authorization**.
The server-side query boundary must constrain direct Explore/API requests even
if every dashboard selector is removed or changed. A platform engineer's future
cluster-wide datasource must be explicitly authorized and have measured collection
coverage; a tenant's datasource must enforce only its registered namespaces.
The currently deployed admin pilot is not tenant isolation. Do not give tenants
`loki-pilot`, or activate this dashboard as evidence that isolation exists.

## Render locally, then review before provisioning

`render.yaml` defaults off and performs no network/API/deployment action. Example
operator-owned **synthetic** inputs:

```yaml
pod_logs_render: true
pod_logs_org_id: 2
pod_logs_datasource_uid: reviewed-org-logs
pod_logs_coverage: Registered workload namespaces; collection coverage verified separately
pod_logs_output: /absolute/operator-local/render-directory
```

Run `ansible-playbook -i localhost, render.yaml -e @approved-inputs.yaml`.
The output contains `dashboard.json`, native `provider.yaml`, and additive child-chart `helm-values.yaml`. Missing
inputs fail closed. No default data source or identity is inferred.

After query authorization and negative tenant-boundary tests pass under separately
approved execution scope, mount the JSON at the provider's exact org-specific
path and install that provider in Grafana's dashboards provisioning directory.
The renderer itself does neither. Do not mix files for different orgs in one
provider directory. Preserve existing provisioning, datasource credentials,
Prometheus, dashboard counts and alerting. The stable UID `pf-pod-logs` is local
to each organization; the provider is read-only to UI updates. Removal is a
separate reviewed operation (`disableDeletion: true`).

Default view is the last 15 minutes with 30-second refresh. The logs panel requests
at most 1,000 records, newest first; narrow filters/time to inspect older records.
This display/query limit does not discard ingestion, alter retention or deduplicate
repeated diagnostic events. Empty results can mean excluded/uncollected data or a
wrong time window, not proof that a pod emitted no logs.

## Compatibility and acceptance

Uses native Grafana 13.2.1 classic dashboard schema and bundled Loki label-value
query objects (`type: 1`, `label`, `stream`). Confirmed label names are `namespace`,
`pod`, `container`. Variable regex formatting is explicit; selections stay within
whatever the independently authorized datasource actually permits.

- [Loki template variables](https://grafana.com/docs/grafana/latest/datasources/loki/template-variables/)
- [Variable formatting](https://grafana.com/docs/grafana/latest/visualizations/dashboards/variables/variable-syntax/)
- [Native file provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards)

Offline render tests and optional checksum-pinned native Grafana import are not
live log-query or isolation proof. Before live acceptance, verify actual authorized
pod logs and volume queries, chained filters, multi-select/All, time changes,
empty/no-data behavior and direct unauthorized query denial for each intended org.
Do not close #38/#218 on the basis of this dashboard.

Reproduce source checks from repository root:

```sh
PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest configuration.test_pod_log_dashboard -v
# Optional: existing binary must match tenant-query/sources.yaml; never downloaded by test.
GRAFANA_VALIDATE_BIN=/path/to/grafana PYTHONPATH=big-bang-bootstrap/tests \
  python3 -m unittest integration.test_pod_log_dashboard_native -v
```

The native fixture runs only on loopback with temporary synthetic credentials and
checks file provisioning, panel types and datasource/variable bindings. It does
not create a live datasource or validate LogQL against production streams.

## Platform-only activation handoff (not selected)

`platform-profile.yaml` explicitly binds org **1** to the proposed read-only
`loki-platform` datasource. It remains disabled and is not referenced by any
cluster selection. Do not substitute `loki-pilot`: its existing pilot credential
is not the new read-only federation identity. Tenant dashboard activation is
outside this profile.

After the datasource and server-side boundary pass their separately reviewed
acceptance, render this profile with an operator-local output directory and an
explicit `pod_logs_render=true`. Merge the resulting `helm-values.yaml` into the
**existing** complete Grafana values using recursive map merge. Do not replace
existing values or install a second Grafana. Unique provider filename and
`pf-pod-logs-org-1` dashboard key avoid overwriting existing providers/dashboards.
Native chart provisioning mounts the generated ConfigMap at its matching provider
path; no extra manual ConfigMap or broad sidecar label is required.

Compatibility test uses Big Bang Grafana chart `13.2.4-bb.0` / upstream chart
`13.2.4`, whose **application** version is `13.2.1`. It proves generated ConfigMap,
mount and provider wiring while preserving pre-existing rendered ConfigMap data,
container settings/mounts and unrelated objects. It does not prove the live count
of 41 existing dashboards: activation must record their UIDs before/after and
verify all remain, with exactly one intended new platform dashboard. Also verify
actual LogQL volume/log queries, chained label choices, All/multi-select, empty
results and native browser behavior against the new datasource before acceptance.

Optional exact-chart source test (no download):

```sh
GRAFANA_CHART_DIR=/existing/grafana/chart HELM_BIN=/existing/helm \
  PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest configuration.test_pod_log_dashboard -v
```
