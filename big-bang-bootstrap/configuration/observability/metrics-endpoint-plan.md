# Metrics endpoint decision — source proposal, not live approval

The live root remains `local-metrics-crds`. No monitoring/Grafana workload, new
system Service grant, host listener or restart has been applied by this proposal.
The reviewed chart needs the Service Role in #208 even if some scrapes are deferred.
Services and ServiceMonitors are different objects; neither makes a loopback-only
host listener reachable from a Prometheus Pod.

## Recommended initial scope

Use the optional [limited values profile](limited-pilot/values.yaml)
for the initial node/workload pilot, after explicit scope/access approval and source
wiring/publication. It defers controller-manager, scheduler, etcd and kube-proxy
ServiceMonitors and the umbrella-injected Headlamp blackbox probe, removes the
unnecessary CoreDNS HTTP bearer reference, and enables
kubelet certificate verification. Exact pinned renders retain all 35 native rule
objects and seven ServiceMonitors, with no HTTP bearer references or TLS bypasses.
The optional `local-metrics-limited-pilot` and `local-logging-limited-pilot` roots
consume this profile. Existing roots remain unchanged. Neither optional root is
selected live: choosing one requires merged/published source, explicit access/scope
approval and guarded root selection, not a live Helm override. Deliver/revalidate
protected inputs using that exact root path; existing default-off delivery, clean
released checkout, cluster identity and immutable-input checks still apply.

Credential-free preflight verified all three existing kubelet serving certificates
against the cluster CA and their node-IP identities. This supports strict kubelet
TLS; authenticated metrics requests, every expected scrape, Grafana datasource
health and dashboard data still require live acceptance. Operator metrics already
reference the admission serving CA Secret and a matching generated DNS identity.

This limited scope is not complete control-plane monitoring or #37 acceptance.
Preserved rules may show missing-control-metric alerts/NoData. Keep notification
routing unarmed and document those gaps; do not turn missing data into success or
silently remove useful recording rules. Full control-plane scrapes remain deferred.
Grafana remains local platform-admin-only: anonymous, OIDC and public ingress off.

## Exact access to review before live apply

| Actor | Authority / consequence |
|---|---|
| `bigbang:monitoring-installer` | New Role/RoleBinding `kube-system:monitoring-system-services`: Service creation in kube-system; Kubernetes cannot name-limit create. Other read/watch/update/patch/delete rights cover only the five generated names below. No existing DNS/control Service, Secret, Pod or ConfigMap mutation rights are added. |
| `monitoring:monitoring-monitoring-kube-prometheus` | Existing candidate runtime ClusterRole: get/list/watch nodes, nodes/metrics, Services, Endpoints, Pods, EndpointSlices and Ingresses; GET `/metrics` and `/metrics/cadvisor`. No new permission is needed merely to reach a listener. Pod discovery can read Pod specifications, not just labels. |
| Prometheus credential | The pinned chart creates `monitoring-monitoring-kube-prometheus-token`, a Kubernetes service-account-token Secret, referenced by API/kubelet authorization. Treat it as a long-lived API credential; do not send it to anonymous HTTP targets or reuse an administrator/etcd key. This proposal does not replace its lifecycle with a projected-token design. |
| `monitoring:monitoring-monitoring-kube-operator` | The existing reviewed candidate manages Secrets/workloads across namespaces. This is trusted infrastructure authority, not a tenant/human role. |
| `monitoring:monitoring-monitoring-kube-state-metrics` | The existing reviewed candidate includes global Secret list/watch. Exporting metadata does not remove that API data-access consequence. |
| `monitoring:monitoring-grafana` | Namespaced ConfigMap get/list/watch for provisioning; no broad Secret reader. Bootstrap credentials are separately delivered immutable inputs. No tenant/engineer/viewer grants are enabled. |

The five exact Service names are:

- `monitoring-monitoring-kube-coredns`
- `monitoring-monitoring-kube-kube-controller-manager`
- `monitoring-monitoring-kube-kube-etcd`
- `monitoring-monitoring-kube-kube-proxy`
- `monitoring-monitoring-kube-kube-scheduler`

The pinned node-exporter DaemonSet has **hostNetwork=false and hostPID=false**;
it mounts `/proc`, `/sys` and `/` read-only and serves port 9100 on the Pod network.
It still reads host information. Do not describe it as having no host access or
claim all hardware/network collectors are accurate before comparing live results.
The namespace ingress policy is not a substitute for actual denial tests. The
proposal adds no NodePort, LoadBalancer, public ingress or host-network exporter.

## Full endpoint plan — separate maintenance, not part of #208 apply

| Endpoint | Evidence / required work before enabling |
|---|---|
| Controller manager, HTTPS 10257 | Live arguments bind loopback; delegated authentication and authorization kubeconfigs are present. Approve a specific reachable bind, verified serving CA/SAN and TLS-verified ServiceMonitor using the Prometheus identity. Preserve `/metrics` authorization; never add it to anonymous allow paths. |
| Scheduler, HTTPS 10259 | Same loopback/delegated-auth finding and requirements. Keep certificate verification enabled; current native defaults skip verification and are not accepted as the final plan. |
| etcd metrics, HTTP 2381 | Current listener was not established by the Pod-argument inspection. RKE2's `etcd-expose-metrics` changes exposure and defaults false. Verify actual listener/config first. Do not export the etcd client private key or scrape its datastore API as a shortcut. Require an approved authentication/TLS and network design before making metrics remotely reachable. |
| kube-proxy metrics, 10249 | No override/config-file argument was observed; upstream defaults to loopback. Verify actual sockets before a change. A bearer header does not itself prove this server authenticates requests. Approve protected transport/access before remote exposure. |

Host configuration must use a separate, owner-local, default-off maintenance
transaction with an inspect-only phase, exact installation/cluster/config hashes,
protected backups and independent recovery. Do not run the broad install-RKE2
playbook or modify generated static-Pod manifests to repair these endpoints.

Changing RKE2 component arguments requires a reviewed service-restart plan. The
single control-plane restart temporarily removes API/Flux control access; app
continuity is not guaranteed. If worker kube-proxy changes require agent restarts,
process one worker at a time and verify node/storage/app recovery before the next.
Do not change unrelated OIDC arguments, cluster joins, datastore, DNS, storage,
versions, firewall or CNI. Existing host preparation intentionally disables
firewalld for Canal compatibility; do not enable it as a quick metrics restriction.
No host-network exposure should be assumed protected by namespace NetworkPolicy.
The full option cannot be approved as a mere namespaced Service fix.

After any separately approved maintenance, require correct CA/hostname and
Prometheus authorization success, wrong CA/hostname/token and unprivileged-client
denial, no broader reachability, expected targets UP and preserved Nextcloud,
GitLab, claims and replica health. Stop on failure; no automatic second restart,
control relaxation, uninstall, rollback or data cleanup is authorized here.

Sources: [RKE2 server flags](https://docs.rke2.io/reference/server_config),
[controller authentication/bind options](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager/),
[scheduler options](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-scheduler/),
[kube-proxy metrics defaults](https://kubernetes.io/docs/reference/config-api/kube-proxy-config.v1alpha1/),
[etcd metrics listeners](https://etcd.io/docs/v3.6/op-guide/monitoring/), and the
[existing guarded maintenance pattern](../../../infrastructure/ansible/API-OIDC.md).
