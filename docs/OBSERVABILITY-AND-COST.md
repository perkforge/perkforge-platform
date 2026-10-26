# Tenant observability and cost attribution

## Local profile

The optional Fleet profile uses the Prometheus Community `kube-prometheus-stack`
chart for Prometheus, Grafana, kube-state-metrics, and node-exporter. OpenCost is
a separate optional bundle and depends on the monitoring bundle. Both paths are
commented out in `local-lab/fleet/gitrepos/platform-apps.yaml`; enable them only
after reviewing node capacity. The charts are pinned to kube-prometheus-stack
`92.11.0` and OpenCost `2.5.33`.

The Prometheus stack exports only the platform tenant, environment, and
isolation-tier namespace labels from kube-state-metrics. Prometheus retention is
seven days on ephemeral storage in the disposable VM profile. Its data is lost
when the Prometheus Pod or VM is replaced. Alertmanager is disabled in this
low-footprint profile. For the two-node VM lab, the configured main-container
requests total about 675 millicores and 1,184 MiB for Prometheus, Grafana,
kube-state-metrics, the operator, two node exporters, and OpenCost. Their
configured limits total about 3.15 CPU and 3,584 MiB. These are sums of chart
resource settings, not measured use, and exclude sidecars, init containers,
RKE2, Rancher, Keycloak, databases, and other workloads. Measure actual use
before enabling this profile beside GitLab or other large applications.

Grafana and Prometheus have no Ingress. Grafana uses a randomly generated admin
password stored in `.secrets/grafana-admin-password` and a Kubernetes Secret
created by `local-lab/scripts/prepare-observability-secrets.sh`. Use a local
port-forward for platform-administrator access. OpenCost UI and API also have
no Ingress. Tenant namespaces default-deny egress to these services, so a
tenant workload cannot query shared cluster metrics through their ClusterIP.

## Tenant access boundary

This profile is platform-operator observability, not tenant-scoped Grafana
access. A Grafana dashboard variable or a filtered dashboard is not an
authorization boundary. Do not issue tenant users Grafana credentials or expose
the Grafana, Prometheus, or OpenCost services until a tenant-safe data plane or
query proxy is implemented and tested. The tenant RoleTemplates grant
namespace-scoped Pod metrics access through Kubernetes' Metrics API; Rancher
remains the tenant-facing view for workload status and supported namespace
metrics. Direct tenant dashboards and tenant query isolation remain open work.

## Cost attribution

OpenCost reads the existing Prometheus service; it does not install a second
Prometheus. The platform tenant/environment labels provide allocation keys, and
the OpenCost API supports aggregation by Kubernetes label. Cloud billing
integration and custom pricing are disabled. On-premises CPU, memory, and
storage numbers are model-based estimates, not bills or actual expenditures.
Before presenting cost results, configure and document the hardware, storage,
power, and shared-service assumptions. Keep requested capacity, measured use,
estimated allocation, and actual expense as separate report fields.

OpenCost is the initial open-source cost attribution implementation for this
profile, not an assertion that it is interchangeable with Kubecost enterprise
features. Reassess the Kubecost product and licensing requirements before
selecting a production or tenant-facing capability.

## Validation status

Fleet values and label allowlists are statically checked. Live metric ingestion,
OpenCost allocation, retention behavior, and dashboard authorization have not
been verified because this profile is not deployed. The opt-in
`local-lab/scripts/verify-tenant-observability.py --apply` verifier checks
namespace attribution labels, Prometheus scrape policy, shared-service exposure,
and tenant denial to Prometheus/Grafana. It does not establish Grafana query
isolation or tenant dashboard authorization. Do not run live mode until the
optional observability profile is deployed and ready. Passing manifest checks
must not be recorded as runtime evidence.

## References

- [kube-prometheus-stack chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [kube-state-metrics label allowlist](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/developer/cli-arguments.md)
- [OpenCost Helm chart](https://github.com/opencost/opencost-helm-chart/tree/main/charts/opencost)
- [OpenCost Prometheus integration](https://opencost.io/docs/installation/prometheus/)
- [OpenCost allocation API](https://opencost.io/docs/integrations/api/)
