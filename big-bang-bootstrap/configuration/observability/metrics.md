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
- Ten CRDs explicitly marked Helm resource-policy keep (not deletion-proof), all35 native PrometheusRules and Prometheus preserved. Separate Alertmanager is disabled; Grafana built-in Alertmanager owns the eventual notification route.
- Operator admission webhooks remain enabled. The **supported upstream patch Job**
  supplies their serving certificate/CABundle instead of requiring a second
  cert-manager installation. Its exact upstream helper image is
  `ghcr.io/jkroepke/kube-webhook-certgen:1.8.8`; this changes the package's Big Bang
  cert-manager default and needs review before deployment. It does not issue public
  service certificates or disable the admission webhook.
- `metrics-prerequisites/` includes explicit installer identities/policies and six
  immutable starting dashboards: cluster, workloads, tenants, Nextcloud, logging,
  alerting. Native datasource/dashboard files own configuration; no API provisioner
  competes. Prometheus datasource is not UI-editable; no external Alertmanager datasource is provisioned.
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

### Reconciled staged wiring

`clusters/local-metrics-review` composes the merged Nextcloud database-only stage with
inactive observability values. `clusters/local-metrics-crds` activates only the
CRD release after protected foundation approval and immutable release selection.
Neither stage enables monitoring, Grafana, Loki or Alloy. The default root and
live source are unchanged. Both preserve existing rendered app resources; the
already-emitted disabled CRD values Secret gains only the keep annotation input.
All three metrics roots preserve the exact Nextcloud enrollment source/parent and
existing direct platform resources; they do not enable Nextcloud web/cron or
change its source pin. Live Nextcloud acceptance remains independently gated.

`clusters/local-metrics-pilot` adds cluster metrics and Grafana after CRD readiness.
Its explicit overlay defers existing app exporters: the unguarded umbrella switch
would add a GitLab exporter, change the runner Deployment/Service, and create a
Keycloak ServiceMonitor. Current source and live installer Roles do not permit
the runner Service or Keycloak ServiceMonitor. The pilot adds no authority to
those installers. Existing app dependency lists are preserved, so their health
does not acquire a new dependency on monitoring readiness.

Pinned child renders compare all existing GitLab, runner, Headlamp and Keycloak
objects unchanged, except GitLab's two shared-secret hook Job name suffixes. The
upstream hashes every coalesced value: removing the umbrella's unwanted Redis
monitor setting leaves an inert `redis:null` key that changes only those suffixes.
The complete Job PodSpecs, commands, credential references and hook policies are
identical. Normal Helm upgrades still execute the existing pre-upgrade hooks;
this is not proof of zero API activity or a live credential-preservation check.
The generated GitLab ServiceMonitor post-renderer has no matching object in this
pilot. Existing app scrapes remain deferred; cluster metrics alone do not complete
their dashboard acceptance. Default roots remain unchanged.

The CRD/pilot stages omit only the umbrella's monitoring Namespace template;
the approved Ansible foundation owns that Namespace. No namespace-management
authority is added to the umbrella installer.

These roots are source candidates, not live selections. No permissions,
credentials or network policies were applied. Before promotion: approve the
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

## Grafana SSO payload — review only

`grafana-sso-values.yaml` is an optional native Generic OAuth overlay, not selected
by any root. It keeps the app disabled/paused, references a protected environment
Secret and public CA ConfigMap, enables PKCE/verified TLS and strict role matching,
and retains independent local recovery. Only exact platform-admin claims propose
Grafana server administration; platform-engineer/viewer initially propose Viewer,
with direct engineer edits still a review decision. Unmatched/tenant groups have no
fallback grant. No users/clients/Secret values or mappings are created here.

Pinned Grafana 13.2.1 supports this native configuration. OSS org-role mapping is
not Enterprise Team Sync. Tenant organizations and backend-scoped datasources stay
disabled until separately tested; Viewer can query all permitted org datasources,
and dashboard/folder hiding is not data isolation. Avoid a global expression that
turns any tenant admin into server/org admin in every membership. Per-tenant native
mapping/apply and lifecycle/revocation wiring are not implemented by this overlay.
Test fresh MFA and native roles/denials, independent recovery, stale sessions,
rollback and per-app resources before activation. No new public endpoint is exposed.
