# Metrics/Grafana implementation candidate — inactive

Implements the native values, reviewed foundation, six starting dashboards and
regressions for #37. This does not select the profile or complete live acceptance.
The architecture #108 remains the basis; old README “remaining” items are historical
architecture gaps superseded here only where explicitly implemented below.

## Implemented

- Exact checksummed Monitoring/Grafana/Prometheus-CRD child sources now participate
  in normal fixture downloads and CI rendering. All selected objects, native
  CRDs, roleRefs and named escalation/bind delegation are checked. YAML enum `=`
  in upstream CRD schemas is parsed as a string with a narrow safe-loader adapter;
  unknown tags are not broadly accepted.
- Ten CRDs explicitly marked Helm resource-policy keep (not deletion-proof), all35 native PrometheusRules, Prometheus and bundled Alertmanager
  preserved. One separate Grafana; no second Prometheus, Grafana or Alertmanager.
- Operator admission webhooks remain enabled. The **supported upstream patch Job**
  supplies their serving certificate/CABundle instead of requiring a second
  cert-manager installation. Its exact upstream helper image is
  `ghcr.io/jkroepke/kube-webhook-certgen:1.8.8`; this changes the package's Big Bang
  cert-manager default and needs review before deployment. It does not issue public
  service certificates or disable the admission webhook.
- `metrics-prerequisites/` includes explicit installer identities/policies and six
  immutable starting dashboards: cluster, workloads, tenants, Nextcloud, logging,
  alerting. Native datasource/dashboard files own configuration; no API provisioner
  competes. Prometheus and Alertmanager datasource definitions are not UI-editable.
  Absent Nextcloud/Loki metrics yield NoData, not fabricated successful acceptance.
- Grafana's runtime sidecar reader gets **ConfigMaps only, in monitoring**. Its
  chart's broad cross-namespace Secret/config reader is off. Helm release storage
  for these new installers stays in monitoring, with no new bigbang Secret grants.
  No existing app storage namespace changes.
- Default-off `configuration/ansible/metrics-prerequisites.yaml` verifies the clean
  published release/target then applies foundation/dashboards and ingress policies.
  It requires reviewed API-server IPv4 `/32` inputs from protected inventory before
  writes. Namespace-only trusted traffic and exact operator webhook sources are
  permitted; policies do not claim to constrain host-network node exporters.

## Who gets authority

The reviewed Ansible actor applies grants; helm-controller impersonates three
separate installer accounts. Named cluster-role bind/escalate and webhook/CRD
management are trusted infrastructure delegation, **not least privilege** or a
human role. No installer cluster-admin binding is added. Kubernetes create cannot
be object-name restricted. Native operator runtime can manage Secrets/workloads
across namespaces; kube-state-metrics also receives upstream Secret list/watch.
Those are real sensitive permissions even if exported metrics use metadata.
They require explicit live approval; do not market them as harmless read-only UI.
Grafana human admin, runtime sidecar and installer identities remain separate.

## Remaining activation gates

No release/root selects these disabled candidates; no permissions, credentials or
network policies were applied. Before a later selection/promotion: approve the
architecture and exact source, verify CRD/operator compatibility and actual lookup
and runtime API behavior, current capacity, protected `grafana-admin` plus Registry1
inputs, API-source CIDRs and network-policy behavior. Do not overwrite/adopt
conflicting resources or loosen webhook/network rules on failure.

Initial Grafana remains local platform administration; anonymous/OIDC/ingress off.
Current routing is Traefik, but this candidate creates no controller-specific
route. Istio/Gateway API is a future reviewed direction, not a network migration
performed here. No Keycloak group mapping is enabled. Verify actual all-node/RKE2
scrapes, trusted admin access, representative dashboards, cardinality/ingestion,
7d/8GB retention/WAL headroom and controlled alerts before claiming #37 complete.

Logging/tenant query auth (#38), one notification route (#39), actual isolation,
resource/redeploy/restore validation (#40) remain subsequent work. No staging
namespace or datastore contents may be deleted without scoped cleanup approval.

CRD removal, release uninstall and data cleanup need separate review: deleting a
CRD also deletes its custom resources. Keep annotations reduce normal Helm removal
risk but are not backup or authorization to delete/recreate.
