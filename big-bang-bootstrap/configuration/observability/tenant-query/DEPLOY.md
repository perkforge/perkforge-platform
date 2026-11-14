# Portable query deployment

Build once, deploy anywhere: use the same digest-pinned gateway/backend images
and authored values. Supply environment-specific DNS, public trust, API/identity
endpoint CIDRs, namespace scopes and OpenBao record paths as protected deployment
inputs. Do not rebuild images or hardcode physical addresses to select a cluster.

## Existing-stack migration

1. Inspect current Flux ownership, capacity, Prometheus PVC, Grafana datasource
   UID and SSO settings. Preserve the currently selected application composition.
2. Activate the native ESO foundation if absent. Its cluster-wide Secret
   list/watch authority requires explicit approval. Keep OpenBao runtime records
   separate from offline recovery custody. Verify delivery before consumers roll.
3. Render backend and gateway with `render-backend.yaml` and `render.yaml`;
   select `backend_transport: loopback-sidecar`. Backend service port remains
   9090, targeting pod TLS port 9443. Never change native loopback reload/probes
   to HTTPS. Apply the backend ConfigMap and provisioned credentials first.
4. Merge `backend-values.yaml` into the existing monitoring values. Preserve
   storage, retention and selectors. Deploy the gateway and authenticated
   `backend-self-monitor.yaml`. Watch Operator readiness and self-scrape targets.
5. Render `render-consumer.yaml` with `consumer_render_enabled: true`, an output
   directory, gateway namespace/Service hostname, and exact identity/API endpoint
   CIDRs. `grafana_required_endpoints` entries contain `purpose` (identity or
   kubernetes-api), `cidr` (/32) and `port` (443 or 6443). Include both Service and
   endpoint addresses when the CNI evaluates translated traffic.
6. Merge the generated native child-chart values with existing Grafana values.
   Preserve `envFromSecret` for OIDC, existing mounts and SSO settings; append the
   query `envFromSecrets` entry if other entries exist. Preserve datasource UID
   `prometheus`. The new `grafana-query-auth` ESO secret supplies only
   `GRAFANA_QUERY_USER`, `GRAFANA_QUERY_PASSWORD`, `GRAFANA_QUERY_CA_PEM`.
   Do not copy credentials into ConfigMaps, Helm values or Git.
7. Apply Grafana egress only after the datasource works. Verify SSO and dashboard
   sidecar API access as well as query traffic. Existing NetworkPolicies are
   additive: inspect all selected egress policies before claiming bypass denial.

## Acceptance and fixing forward

Check Ready workloads, Prometheus and reloader self-scrapes, existing datasource
health and dashboards, Keycloak login, and denied unauthenticated backend access.
Verify namespace-filtered queries and rejected foreign-scope credentials through
the tenant route. Preserve the operator's platform route in this single-user lab;
no new human-account gate is required. If something fails, diagnose and fix forward
in the same source/values, retaining metrics storage and existing SSO. Source
rendering or a merged PR is not proof of live acceptance. Close tickets only when
their actual runtime criteria pass.
