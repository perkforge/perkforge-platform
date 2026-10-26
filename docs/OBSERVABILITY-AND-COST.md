# Tenant observability and cost attribution

## Local profile

The Fleet profile uses the Prometheus Community `kube-prometheus-stack` chart
for Prometheus, Grafana, kube-state-metrics, and node-exporter. OpenCost is a
separate bundle and depends on the monitoring bundle. Both paths are currently
disabled in `local-lab/fleet/gitrepos/platform-apps.yaml` after the monitoring
rollout coincided with a control-node OOM. The bundles remain configured and
pinned to kube-prometheus-stack `92.11.0` and OpenCost `2.5.33`; re-enable them
after the cluster has adequate memory headroom.

The Prometheus stack exports only the platform tenant, environment, and
isolation-tier namespace labels from kube-state-metrics. Prometheus keeps three
days of data on ephemeral storage, with a 1 GiB retention-size ceiling and a
2 GiB `emptyDir` ceiling. Data is lost when its Pod or VM is replaced.
Alertmanager is disabled. Prometheus, Grafana, kube-state-metrics, the operator,
two node exporters, and OpenCost request about 525 millicores and 688 MiB total;
configured main-container memory limits sum to about 1,792 MiB. The Prometheus,
Grafana, kube-state-metrics, operator, and OpenCost workloads are pinned to
`cks-worker`; node-exporter runs on both nodes. These are configured values, not
measured use. They exclude sidecars, init containers, RKE2, Rancher, Keycloak,
databases, and other workloads.

Before rollout, `cks-worker` used about 2,024 MiB of
memory, had 1,152 MiB in workload memory requests, and had 3,740,808 Ki
allocatable (about 3.65 GiB). Adding the configured observability requests
would bring worker requests to about 1.8 GiB, roughly 50% of allocatable memory.
The control node already had about 90% of memory and 91% of CPU reserved by
requests, which is why the main monitoring workloads are pinned to the worker.
Those request figures did not predict the control-plane's actual memory
behavior and were not a capacity guarantee.

### 2026-10-26 rollout finding

During reconciliation, the control VM's kernel OOM killer terminated
`kube-apiserver` after it reached about 2.25 GiB RSS. The VM has 4 GiB assigned
(about 3.6 GiB visible to the OS); Keycloak used about 750 MiB and etcd about
168 MiB at the subsequent inspection. Prometheus/Grafana pods were placed on
the worker and became Ready, with Grafana using about 248 MiB and its two
sidecars about 80 MiB each. OpenCost had not started. The incident establishes
that the current two-VM profile has insufficient control-plane headroom during
this rollout; the timing suggests the rollout contributed, but does not prove
that its worker-side memory alone caused the control-node OOM. The host itself
reported 14 GiB total RAM, 3.7 GiB available, and 8.5 GiB swap in use, so
increasing VM memory on this host is not a safe remedy.

The Fleet paths are paused pending the three-node ThinkCentre cluster. Do not
re-enable them on these VMs or record this rollout as a successful observability
acceptance test.

Grafana and Prometheus have no Ingress. Grafana uses a randomly generated admin
password stored in `.secrets/grafana-admin-password` and a Kubernetes Secret
created by `local-lab/scripts/prepare-observability-secrets.sh`. Use a local
port-forward for platform-administrator access. OpenCost UI and API also have
no Ingress. Tenant namespaces default-deny egress to these services, so a
tenant workload cannot query shared cluster metrics through their ClusterIP.
The Fleet bundle adds a platform-only overview dashboard with tenant namespace
count, CPU, memory, pod, and namespace quota panels. Its metrics include tenant
labels and therefore remain for platform administrators; it is not a tenant
dashboard or an authorization boundary.

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

Fleet values, resource budgets, node selectors, dashboard structure, and label
allowlists are statically checked. Prometheus/Grafana did reconcile, but the
rollout coincided with the OOM described above. Live metric ingestion, OpenCost
allocation, retention behavior, tenant denial probes, and dashboard
authorization remain unverified. The
`local-lab/scripts/verify-tenant-observability.py --apply` verifier checks
namespace attribution labels, Prometheus scrape policy, shared-service exposure,
and tenant denial to Prometheus/Grafana. It does not establish Grafana query
isolation or tenant dashboard authorization. Do not run live mode until the
observability profile is deployed and ready. The platform deployment script runs
the verifier when the bundle paths are enabled. Passing manifest checks must
not be recorded as runtime evidence. A Playwright dashboard-access test is a
follow-up for Phase 5; do not grant tenant Grafana access until a tenant-safe
data plane or query proxy has been implemented and verified.

## References

- [kube-prometheus-stack chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [kube-state-metrics label allowlist](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/developer/cli-arguments.md)
- [OpenCost Helm chart](https://github.com/opencost/opencost-helm-chart/tree/main/charts/opencost)
- [OpenCost Prometheus integration](https://opencost.io/docs/installation/prometheus/)
- [OpenCost allocation API](https://opencost.io/docs/integrations/api/)
