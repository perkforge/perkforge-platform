# Tenant metrics gateway: inactive component slice (#218)

This tests the smallest candidate for the [tenant boundary](../tenant-access.md):
shared Grafana organizations and existing telemetry stores, with authenticated
context-bound query enforcement. It is **not deployed or selected by any cluster
root**. It grants nobody access. No runtime package/image/install path is selected
by this slice; `sources.yaml` pins the native test binaries only.

## Implemented path

`render.yaml` is a default-off, local Ansible renderer. It requires
`tenant_query_render_enabled: true`, `runtime_dir`, `certificate_path`,
`private_key_path`, `server_name`, a loopback `listen_address`, `metrics_upstream`,
and a nonempty `query_contexts` list. Every context supplies `id`, `namespaces`,
`proxy_port`, and its own `htpasswd_path`. Empty scopes, duplicate routes/ports/auth
files and unsafe scalar syntax fail before writing files. Render only to a fresh
private directory; the renderer neither creates credentials nor launches services.
Namespace input must come from the platform-owned context inventory, not requests.

The native fixture consumes Portal's approved `runtime_namespaces` from
[its context](../../authorization/contexts/portal.yaml). Control namespaces are
not silently added. A second synthetic context proves credential separation.

1. Nginx terminates TLS and authenticates each fixed context route against a
   separate protected htpasswd file. These are backend datasource identities, not
   Keycloak user passwords. Future runtime custody is OpenBao/ESO under the existing
   credential procedure; no credentials or delivery are added here.
2. Each authenticated route goes to its **own** loopback-only
   `prom-label-proxy v0.16.2` process with static namespace values. The proxy never
   accepts the authorization scope from an HTTP header/query/form parameter.
3. Only exact GET/POST `query` and `query_range` routes are allowed. Request auth and
   tenant headers are stripped before upstream forwarding. Every PromQL selector
   receives the fixed scope; conflicting selectors fail, broad selectors narrow.

The optional `platform_query.htpasswd_path` adds separate `/platform` query/range
routes. Its auth file must differ from every tenant's, and it requires authenticated
TLS upstream configuration. HTTPS upstreams require `upstream_ca_path`,
`upstream_client_cert_path` and `upstream_client_key_path`; platform Nginx routing
also requires `upstream_tls_name`. Only isolated loopback fixtures may use HTTP.
The renderer additionally emits an inactive `grafana-security.ini` origin
restriction. Merge it into selected Grafana configuration only after review; it
is not automatically applied and does not replace backend mTLS or egress policy.

No generic passthrough exists. Labels, series, metadata, rules, alerts, exemplars,
remote-read, admin, debug and federation endpoints remain denied. Consequently
label-discovery dashboard variables are not supported by this initial slice.
Their upstream filtering must be verified before opening them. This is not yet a
complete Grafana datasource integration. Multiple namespaces use explicit static
values, never namespace-name wildcard policies.

## What passing tests do and do not prove

Tests run actual Nginx (observed 1.26.3), real pinned prom-label-proxy, actual
Ansible rendering, synthetic TLS/auth and a recording loopback backend. They prove
credential/route isolation, header/form override resistance, selector rewriting,
method/endpoint denials and empty-scope rejection. The first suite uses a recording
backend, not PromQL evaluation. The separate data-plane suite below exercises real Prometheus and Grafana.
No downloads occur during tests. Provide the independently checksummed official
Linux amd64 v0.16.2 binary and Nginx; the binary hash is checked again at startup.

```sh
PROM_LABEL_PROXY_BIN=/path/to/verified/prom-label-proxy \
  PYTHONPATH=big-bang-bootstrap/tests \
  python3 -m unittest integration.test_tenant_query_gateway -v
```

`NGINX_VALIDATE_BIN` optionally selects the existing Nginx executable. Temporary
keys, htpasswd files and child processes are removed when the test finishes.
No production configuration, kubeconfig, user credentials or services are used.

### Real synthetic data-plane evidence

`integration/test_tenant_query_data_plane.py` runs checksum-pinned Grafana 13.2.1
and Prometheus 3.14.0, matching reviewed app versions, with temporary organizations,
users and metrics. It exercises both the datasource proxy and `/api/ds/query`
used for arbitrary query requests. It proves in that fixture:

- All three tenant roles receive Portal data only; the separately authenticated
  PE datasource sees both tenants and unlabelled data.
- Native tenant org Admin can create a datasource, but Portal credentials fail
  against the PE/other-context route. Cross-org IDs and org-header switching fail.
- Direct backend access lacks the mandatory client certificate. Grafana's source
  origin restriction and backend mTLS both participate in preventing bypass.
- Trusted scrape target labels with `honor_labels: false` prevent an application
  from claiming another namespace; its conflicting label becomes `exported_namespace`.

```sh
PROM_LABEL_PROXY_BIN=/path/to/verified/prom-label-proxy \
PROMETHEUS_VALIDATE_BIN=/path/to/verified/prometheus \
GRAFANA_VALIDATE_BIN=/path/to/verified/grafana/bin/grafana \
  PYTHONPATH=big-bang-bootstrap/tests \
  python3 -m unittest integration.test_tenant_query_gateway integration.test_tenant_query_data_plane -v
```

This is synthetic data-plane evidence, not a deployed network test, frontend UI
session test, full plugin/redirect surface audit, cluster rule audit or ingestion
policy rollout. Grafana's public distribution fixture is not the Iron Bank plugin
bundle. TLS certificates are disposable test inputs; runtime custody is unchanged.

### Ingestion audit findings

The checked-in limited metrics overlay does not yet enforce the trusted
resource-to-namespace mapping needed for tenant query access. Do not infer it
from a dashboard filter or from a ServiceMonitor's placement:

- An application scrape can use its platform-owned target namespace with
  `honor_labels: false`, as the native fixture proves. Tenant-controlled scrape
  relabelling must not be able to replace this boundary.
- Cluster exporters such as kube-state-metrics and kubelet/cAdvisor describe
  resources across namespaces. Their legitimate **resource** namespace must be
  retained and audited; stamping the exporter's own namespace is incorrect.
- Rules can manufacture namespace-labelled aggregates. Review tenant-exposed
  recording rules for mixed-context input; a namespace label alone proves nothing.

The fixture does not claim the existing cluster already meets those conditions.
Current source data ownership and selected monitoring rules still need an
operator/source audit before runtime activation.

## Remaining activation work

- Select/pin packaged deployment through existing Big Bang/Flux ownership; provide
  authenticated TLS upstream configuration and reviewed secret delivery. The local
  renderer currently binds TLS to loopback only and has no deployment consumer.
- The gateway must be separate from Grafana. Internal proxy ports are not exposed
  as Services. Grafana and tenant workloads cannot reach raw Prometheus/Loki or
  bypass gateways. Apply backend auth and actual network/egress enforcement.
- Platform-engineer all-data access needs a **separately authenticated** backend
  route. Trusting the Grafana pod/source IP would let tenant org Admins use it too.
  Tenant credentials must fail there; PE credentials stay outside tenant orgs.
- Native Grafana org Admin can create datasources. Test arbitrary URLs, redirects,
  alternate DNS/IP/ports, self/metadata/internal endpoints, plugin resource APIs,
  cross-org datasource IDs and credential reuse. Folder/UI restrictions do not
  close those paths. Network rules and complete plugin/redirect coverage do not
  exist here yet; the native tests cover the concrete datasource/query API attempts listed above.
- Enforce authentic namespace/resource ownership at ingestion, including tenant
  scrape configuration and `honor_labels` controls. A namespaced scrape endpoint
  can expose other resources: do not stamp its namespace over cluster-exporter
  results. Audit recording rules and shared exporters for mixed-tenant content.
  Test unlabelled, spoofed, unknown and moved-ownership data with a real metrics
  backend before enabling access. Missing namespace has no tenant fallback.
- Integrate the existing authenticated Loki tenant gateway separately. This slice
  adds no Loki routes and proves no log isolation.
- Complete dashboard/Explore/UI/API allow/deny behavior using tenant Admin/Editor/Viewer
  and PE roles; preserve PE access and remove grants on failed isolation evidence.

These gates keep #218 open. No tenant grant is justified by these component tests.

References: [prom-label-proxy](https://github.com/prometheus-community/prom-label-proxy),
[Grafana security](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/),
[Prometheus security model](https://prometheus.io/docs/operating/security/).
