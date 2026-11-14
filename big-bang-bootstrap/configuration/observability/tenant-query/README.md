# Tenant metrics gateway: inactive component slice (#218)

This tests the smallest candidate for the [tenant boundary](../tenant-access.md):
shared Grafana organizations and existing telemetry stores, with authenticated
context-bound query enforcement. It is **not deployed or selected by any cluster
root**. It grants nobody access. An unselected Flux-compatible package is included
below; its images are digest-pinned, but no runtime installation is selected.
`sources.yaml` pins the additional native test binaries.

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

- Select the unselected package through existing Big Bang/Flux ownership; provide
  authenticated TLS upstream configuration and reviewed secret delivery. Native
  fixture rendering defaults to loopback; package rendering is an explicit opt-in.
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

## Unselected Flux-compatible package

Set `tenant_query_package_enabled: true` only to **render** the package, supplying
`tenant_query_output_dir` separately from the container's fixed `/tmp/gateway`.
The renderer emits `deployment.yaml` and `kustomization.yaml`; `kubectl kustomize`
composes them offline. No Flux root, HelmRelease or running service is changed.
The generated nonsecret manifests can enter a separately reviewed Flux path; do
not commit protected htpasswd, certificate keys or generated secret contents.

The candidate uses a dedicated platform-owned namespace, not `monitoring`,
`kube-system` or `default`. Tenant workload/editor rights must not extend there.
Required package inputs are `gateway_namespace`, `gateway_tls_secret`,
`upstream_client_secret`, each context's `auth_secret_name` and integer
`health_port`, plus `platform_query.auth_secret_name`. All protected paths are
fixed under `/etc/gateway` and validated by `render.yaml`. Secret keys are:

- gateway TLS: `tls.crt`, `tls.key`;
- upstream identity: `ca.crt`, `tls.crt`, `tls.key`;
- every distinct context and PE auth Secret: `htpasswd`.

Distinct Secret names/files must contain distinct scoped credentials; filenames
alone do not prove that. No ESO grant/delivery or Secret creation occurs here.

One replica, nonroot UID/GID 1000, read-only filesystems, dropped capabilities and
no Kubernetes token. Official Nginx 1.31.6-alpine reuses the existing repository
TLS-proxy digest; prom-label-proxy v0.16.2 uses its inspected linux/amd64 manifest
digest. Nodes are constrained to amd64. There is one Nginx container plus one
namespace proxy per context, not another metrics store. For the single Portal
fixture, proposed requests total 40m CPU and 128Mi RAM, limits 1 CPU and 384Mi RAM;
these are starting budgets, not measured capacity or HA guarantees. No PVC.

Only TLS 8443 is exposed by the ClusterIP Service. Query proxy ports stay on Pod
loopback. Per-proxy internal metrics ports are only for kubelet readiness; the
NetworkPolicy does not allow peers to those ports. Readiness proves processes are
listening, not successful upstream queries or tenant isolation. Effective policies
must be audited because Kubernetes NetworkPolicies are additive.

The gateway policy allows ingress only from the selected monitoring Grafana Pods,
and egress only to selected monitoring Prometheus Pods on 9090 and kube-system DNS
on UDP/TCP 53. A second policy allows those gateway Pods into Prometheus. Neither
policy removes the existing monitoring-namespace ingress allowance. Existing
Grafana raw-backend bypass remains open until its separately reviewed backend/
egress migration; therefore **no tenant grants accompany package deployment**.

The package smoke runs actual pinned containers with no external network, as
nonroot/read-only, and verifies internal metrics readiness. It is not Kubernetes
Secret/fsGroup/CNI/Flux acceptance. Run all source/package checks with:

```sh
RUN_QUERY_PACKAGE_NATIVE=1 \
QUERY_MONITORING_CHART=/path/to/verified/monitoring/chart \
HELM_VALIDATE_BIN=/path/to/verified/helm \
  PYTHONPATH=big-bang-bootstrap/tests \
  python3 -m unittest configuration.test_tenant_query_package -v
```

Native containers must already be pulled by their exact digests. Chart input is
verified monitoring 91.4.1-bb.1; Helm is the repository's 3.19.0 pin. The real Helm
comparison proves `discovery-values.yaml` changes only five definition namespace
selectors and preserves every other rendered object, including exporter labels.

## Read-only live audit and bounded activation scope

The 2026-11-13 read-only audit found 8 ServiceMonitors, 1 PodMonitor and 36
PrometheusRules (94 recording rules), all defined in `monitoring`; no Probe or
ScrapeConfig objects. Prometheus currently selects definitions from all namespaces,
with no namespace enforcement or web TLS config. Kubelet and kube-state-metrics
use `honorLabels: true` to preserve actual resource namespaces. Portal's inspected
`portal-workloads` Role has no monitor/rule permissions; this is not a full
cluster-wide effective-RBAC audit. No credentials or raw private topology are
recorded here.

The observed monitoring-namespace ingress allowance and absence of Grafana egress
restrictions leave a raw Prometheus bypass today. Synthetic test success does not
change that live fact. `discovery-values.yaml` is the smallest ownership fix:
limit definition discovery to platform-owned `monitoring`, preserving trusted
exporter resource labels. It does not authorize tenant-supplied rules/monitors and
does not replace the remaining label/rule ownership audit.

Before requesting deployment approval, finish the following bounded gates:

1. Verify namespace protection, image pull/provenance, secret custody, backend TLS
   identity, effective network policies and current datasource consumers. Render
   against the selected released source. No broad new PE/OpenBao permissions.
2. Validate the **Operator-generated** Prometheus configuration, startup/readiness
   probes, config-reloader, self-scrape and existing consumers with authenticated
   backend access. Native standalone mTLS is not drop-in Operator evidence:
   [upstream tracks client-cert probe compatibility](https://github.com/prometheus-operator/prometheus-operator/issues/5419).
   Do not flip `RequireAndVerifyClientCert` live until that path is proven.
3. Ask for action-time approval of the exact namespace/Secret delivery and network
   changes: gateway ingress from Grafana on 8443; gateway egress to the selected
   backend on 9090 and DNS on 53; backend ingress from that gateway. Apply the
   five discovery selectors only after verifying no selected definitions moved.
   Keep tenant access closed and current PE datasource working during staging.
4. Once equivalent authenticated PE metrics/log paths are ready, separately approve
   the concrete Grafana datasource/egress migration closing raw backends while
   preserving Keycloak and existing platform functionality. This package does not
   yet supply that migration or a Loki route. Test custom URLs, query API, direct
   backend, wrong credentials/context, and unchanged PE views on the actual target.
5. Only after those denials pass request scoped tenant org/role activation. On a
   failed denial, leave/revoke tenant access first; do not regain availability by
   reopening raw backends while tenants still have access. Staging rollback removes
   only the new candidate objects and restores the reviewed values selection,
   preserving telemetry, existing credentials and the working platform app.

### Operator-compatible backend integration proof (not deployment-ready)

The pinned Operator v0.94.0 implementation is material here, not just the
Prometheus web configuration schema:

- [`buildProbeHandler`](https://github.com/prometheus-operator/prometheus-operator/blob/v0.94.0/pkg/prometheus/promcfg.go#L1426)
  uses kubelet HTTP(S) probes without client certificates normally. With
  `listenLocal: true` it instead uses an exec HTTP probe to `localhost:9090`.
- [`BuildConfigReloader`](https://github.com/prometheus-operator/prometheus-operator/blob/v0.94.0/pkg/prometheus/common.go#L362)
  targets the local Prometheus endpoint for reload; `MakeContainerPorts` omits
  the public container port with `listenLocal`.

`backend-nginx.conf.j2` is an **unselected native integration proof**, not part
of `render.yaml` or a deployable overlay. Its candidate arrangement is HTTP
Prometheus bound to loopback, with a separately bound authenticated TLS frontend
in the same pod. The frontend requires a trusted client certificate, exposes
only query/query_range and authenticated `/metrics`, and rejects lifecycle and
admin endpoints even for an authenticated client. Loopback probe/reload paths
remain available inside the Prometheus pod. Do not co-locate Grafana or tenant
workloads in that pod. A dedicated client CA must authorize only the gateway and
explicit trusted monitoring consumers, not every cluster client certificate.

The native fixture runs **the same ten Grafana data/isolation tests** through
this frontend, plus local readiness/liveness/reload and authenticated self-scrape
checks. It does not run the Operator, prove generated pod reconciliation, validate
Iron Bank image exec tooling, enforce Kubernetes network policy, or establish
credential separation for production. The synthetic fixture certificate is not a
runtime trust design.

Before making a deployment overlay selectable:

1. Render and reconcile the exact Operator/chart configuration in an isolated
   test cluster. Prometheus must bind loopback only; a sidecar must bind a
   **different** public port (for example 9443, not 9090 on wildcard which would
   collide). Update Service target ports, gateway upstream and policy ports
   together. Verify probes, config reload, rolling restart and self-scrape.
2. Inventory every existing Prometheus consumer. Migrate the self ServiceMonitor
   to the frontend with a dedicated TLS client and correct service port; do not
   expose unauthenticated raw query as a compatibility fallback. Preserve the
   reloader metrics endpoint independently. Validate current alerts/PE dashboards.
3. Preserve PE functionality before enabling tenants: the present gateway permits
   only query/query_range. Dashboard variable labels/series/metadata and existing
   log datasources require their own authenticated, tested routes. Do not claim
   that pointing all current Grafana datasources at this gateway is compatible.
4. Obtain action approval for the exact backend port/auth/ServiceMonitor changes
   and Grafana egress changes. Existing monitoring-wide ingress is additive; it
   does not supply query authorization. An egress allowlist must retain necessary
   DNS/identity/PE data paths without allowing Grafana to reach loopback backend
   or alternative unauthenticated services. Validate effective CNI policy and
   direct/custom-datasource denial on the target cluster before granting tenants.

This proof avoids the unsafe native `RequireAndVerifyClientCert` flip that would
break ordinary kubelet probes. It is not permission to make that flip or a claim
that the remaining PE consumer and egress migration is complete.

### Authenticated platform variable and health reads

The PE route now also permits `/api/v1/labels`, `/series`, `/metadata`,
`/status/buildinfo`, and `/label/<conventional-label-name>/values` through the
same distinct platform credential and verified upstream TLS client. The inactive
backend frontend permits these matching read paths. There is no general-purpose
proxy, runtime configuration endpoint, lifecycle endpoint or admin API. Label-value
requests allow GET only; other listed read APIs accept GET/POST (unsupported
Prometheus methods still fail upstream); DELETE remains denied. Names outside
`[a-zA-Z_][a-zA-Z0-9_]*` are intentionally unsupported by this slice.

Real Grafana datasource requests validate the basic variable/health paths against
both direct-mTLS Prometheus and the loopback frontend. Platform series queries
include all synthetic namespaces plus unmapped series. Tenant credentials cannot
access these platform routes, and tenant routes still reject unimplemented
metadata/variable paths. This updates the query-only PE limitation noted above,
**not** the tenant API coverage or full existing dashboard compatibility claim.
Loki/log datasource routes, exemplars and other read APIs are not implemented;
keep existing PE datasources and live network settings unchanged until their
compatibility and isolation are tested. The inactive package is still not selected.

### Inactive chart integration candidate

`backend-values.yaml` is a separate **unselected** Big Bang overlay. It sets
`listenLocal: true`, adds the pinned nonroot Nginx sidecar on pod port **9443**,
and directs the existing Prometheus Service's target to `backend-tls`. The Service
port remains 9090; any destination-pod NetworkPolicy must allow **9443**, not
assume the Service port is the pod port. The gateway upstream must use HTTPS and
the authenticated backend Service DNS name, never loopback on the gateway pod.
There is no automatic change to the earlier gateway package's policy or upstream.

The pinned chart applies `serviceMonitor.scheme/tlsConfig` to BOTH native
Prometheus and reloader endpoints. Therefore this candidate disables that stock
self-monitor and pairs it with `backend-self-monitor.yaml`: Prometheus `/metrics`
and `/reloader/metrics` use the dedicated client Secret and HTTPS. The frontend
forwards reloader metrics to HTTP localhost8080. Operator `ListenLocal` also binds
reloader metrics locally and removes its named container port, so the obsolete
public reloader Service port is disabled. The reloader itself remains HTTP. Each endpoint sets a distinct static `component`
target label (`prometheus` or `config-reloader`) so shared `go_*`/`process_*`
metric names cannot collide behind the same TLS Service/port.
The monitor selector matches the actual chart-rendered Service labels. It does
not change other kubelet/KSM/resource labels or discovery settings.

`render-backend.yaml` only renders a local `backend-config.yaml` ConfigMap when
explicitly opted in with an existing canonical `backend_output_dir`; it never
applies it. The ConfigMap and overlay agree on 9443 frontend, 9090 loopback,
protected TLS mount and writable scratch mount. Required `query-backend-tls`
(server cert/key and narrowly trusted client CA) and `query-backend-self-client`
(client cert/key/server CA) Secrets are **not created or stored in Git**. The
server certificate must match
`monitoring-monitoring-kube-prometheus.monitoring.svc`. Source names are proposed
runtime inputs, not existing issued credentials.

The real pinned Helm render test proves the overlay's CR/Service and per-endpoint monitor
shape. It does **not** prove Operator reconciliation, pod secret/fsGroup access,
exec-probe tooling, reloader health, nor actual scrape success under Kubernetes.
No isolated Kubernetes environment is currently available in this workstation's
PATH; native process and offline Helm tests do not replace that validation. Do
not activate this candidate alone: current PE consumers would need coordinated
migration to authenticated HTTPS, and CNI/egress and log compatibility remain
open. A future activation approval must enumerate the paired ConfigMap/Secrets,
Prometheus rollout, Service target, split monitor, gateway destination port9443,
and preserved PE/identity/log routes. Keep tenant grants closed until that tested
migration is ready. Do not use the live cluster as an unapproved reconciliation
experiment.

### Pairing the inactive gateway with the backend sidecar

For local package rendering, explicitly select `backend_transport: loopback-sidecar`
together with `metrics_upstream: https://monitoring-monitoring-kube-prometheus.monitoring.svc:9090`
and `upstream_tls_name: monitoring-monitoring-kube-prometheus.monitoring.svc`.
This selects pod destination **9443** in both gateway egress and paired backend
ingress policies while keeping the upstream Service port **9090**. Incorrect
Service address, TLS identity or transport mode fails before output is written.
The omitted/default `direct-mtls` mode preserves the earlier 9090 pod policy for
its separate authenticated-native-backend candidate; it is not a raw HTTP fallback.

This pairs inactive source contracts only. The backend overlay, ConfigMap, dedicated
Secrets and split self-monitor still require coordinated deployment. Existing
additive policies, Grafana egress and PE consumer migration remain unresolved;
no live network enforcement or Operator reconciliation is claimed.

## Existing-stack deployment

See [portable deployment and fix-forward operations](DEPLOY.md) and
[dedicated OpenBao/ESO delivery](eso/README.md). Renderers remain opt-in;
source publication is not a claim of live acceptance.

### RKE2 ingress translation and OIDC

An allowed external ingress `/32:443` may not match a CNI post-DNAT destination.
RKE2 Traefik hostPort/Service443 targets selected pods at TCP8443. The explicit
flag `grafana_rke2_ingress_backend_enabled` adds only namespace `kube-system`
plus BOTH `app.kubernetes.io/name=rke2-traefik` and
`app.kubernetes.io/instance=rke2-traefik-kube-system` on8443. Default remains off;
other providers select their reviewed equivalent without rebuilding images.
Preserve existing egress and TLS/client settings. This is a separately approved
network change, not a credential reset. Verify trusted-CA discovery and actual
login from the Grafana workload after applying.

#### Required Grafana network-change regression check

After any Grafana egress/ingress-routing change, run checks **inside the actual
Grafana workload**, preserving its configured CA and canonical OIDC hostname.
Desktop HTTP200 and browser authorization redirects do not exercise server-side
token exchange and must not count as SSO acceptance.

1. GET the configured realm discovery endpoint with trusted CA and bounded timeout,
   without redirects/TLS bypass. Require HTTP200 from the Grafana pod.
2. POST a deliberately unauthenticated authorization-code grant request without a
   code to the configured token endpoint. Require prompt expected 400/401, not TCP
   or TLS timeout. Never capture/replay a human code or disclose client credentials.
   This establishes reachability, NOT successful authenticated token exchange.
3. Verify unchanged Grafana readiness, recovery availability, existing query
   datasources and exact prior policy rules. NetworkPolicy needs no pod restart.
4. Record fresh real-user OAuth callback/dashboard acceptance separately or leave
   it explicitly pending. An existing session, login page or redirect is not proof.

The 2026-11-14 incident exposed this gap: an overnight restriction permitted original
ingress port 443 but omitted translated Traefik port 8443. The narrow fix restored workload
reachability without restart or identity changes, then the owner confirmed login.
The renderer and protected target inputs retain the correction; this operator-
applied policy is not claimed to have continuous Flux ownership.
