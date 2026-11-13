# Tenant metrics gateway: inactive component slice (#218)

This tests the smallest candidate for the [tenant boundary](../tenant-access.md):
shared Grafana organizations and existing telemetry stores, with authenticated
context-bound query enforcement. It is **not deployed or selected by any cluster
root**. It grants nobody access. No runtime package/image/install path is selected
by this slice; `sources.yaml` pins the native test binary only.

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
method/endpoint denials and empty-scope rejection. The backend does not execute
PromQL: these tests do **not** prove returned-series isolation or data authenticity.
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

## Mandatory before activation

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
  close those paths. Neither network rules nor these Grafana tests exist here yet.
- Enforce authentic namespace/resource ownership at ingestion, including tenant
  scrape configuration and `honor_labels` controls. A namespaced scrape endpoint
  can expose other resources: do not stamp its namespace over cluster-exporter
  results. Audit recording rules and shared exporters for mixed-tenant content.
  Test unlabelled, spoofed, unknown and moved-ownership data with a real metrics
  backend before enabling access. Missing namespace has no tenant fallback.
- Integrate the existing authenticated Loki tenant gateway separately. This slice
  adds no Loki routes and proves no log isolation.
- Prove dashboard/Explore/API allow/deny behavior using tenant Admin/Editor/Viewer
  and PE roles; preserve PE access and remove grants on failed isolation evidence.

These gates keep #218 open. No tenant grant is justified by these component tests.

References: [prom-label-proxy](https://github.com/prometheus-community/prom-label-proxy),
[Grafana security](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/),
[Prometheus security model](https://prometheus.io/docs/operating/security/).
