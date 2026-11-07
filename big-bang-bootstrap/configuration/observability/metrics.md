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

## Umbrella ownership and bootstrap boundary

The pinned Big Bang Grafana template otherwise looks up the existing admin Secret
and copies it into a Flux notification credential before any post-renderer runs.
The source keeps that reference in the child's native HelmRelease `spec.values`
(via the package Flux overrides), which Flux merges after `valuesFrom`. The
umbrella-facing admin reference and fallback fields are empty. No admin Secret
read or credential copy is needed by the umbrella identity.

The umbrella post-renderer omits only `monitoring`'s `grafana` Alert/Provider,
`grafana-flux-auth` Secret and `flux-grafana-dashboards` ConfigMap. Notifications
remain unarmed. The 37 native Grafana ConfigMaps belong to its existing scoped
installer; the six foundation dashboards remain Ansible-owned. No dashboard API
provisioner or cross-namespace umbrella grant is added. The synthetic-loopback
regression runs the real pinned Helm lookup under the unchanged umbrella Role,
including installed monitoring APIs; it reproduces the old forbidden Secret GET
and proves the corrected path performs none. Default/current roots and existing
app manifests remain unchanged. This is offline evidence, not live acceptance.

## Existing registry credential references

The Monitoring and Grafana package-local `values.global.imagePullSecrets` lists
explicitly reference the existing immutable `monitoring/private-registry` Secret.
Big Bang's credential helpers emit empty reference lists when registry credentials
are deliberately absent from Git values. Those lists override package defaults;
Helm propagates the package global into its dependencies. Secret presence alone
therefore does not prove any workload can use it.

The pinned limited roots now bind that reference on operator/state-metrics/node
exporter Pods, the Prometheus CR, admission Jobs and the Grafana Pod. The operator
propagates the CR reference to its generated Prometheus/reloader StatefulSet.
No credential values, Secret creation/copy/rotation, registry substitution or new
RBAC are involved. Existing Secret identity/ownership remains an external input.
Exact legacy/fixed renders and the native operator generator enforce this contract.
Actual authenticated pulls and recovery still need separately approved live checks.

The broader non-limited roots also render a blackbox exporter with a separate
pull-secret input. It is unchanged here and still has an empty effective reference;
those roots are not accepted for activation. The limited roots explicitly defer
that exporter and its app probes.

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

The native monitoring chart also emits five metric Services in `kube-system`:
CoreDNS, controller manager, etcd, kube-proxy and scheduler. The installer needs
an explicit Service-only Role there; its monitoring-namespace Role cannot cover
these objects. Creation cannot be name-restricted by Kubernetes, so this remains
trusted installer access. Read/watch/mutate/delete rights are limited to the five
exact generated names. Existing DNS/control Services, Secrets, Pods and ConfigMaps
receive no additional permission. The namespace itself is not relabeled or owned
by this foundation. The binding targets only `bigbang:monitoring-installer`.

The offline grant audit now follows actual RoleBindings and target namespaces,
rather than incorrectly treating every namespaced object as a monitoring object.
Live preflight must still verify authorization. A permitted Service is not proof
that its target is reachable: the observed RKE2 controller-manager and scheduler
metrics bind to loopback. Their endpoint/exposure plan requires separate review;
this Role does not change host bind addresses, firewall, TLS, or running system
components. Do not proceed through a failed scrape check or relax controls to
make it pass.

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

`configuration/ansible/metrics-inputs.yaml` is a separate default-off delivery
entrypoint. It reads operator-provided `admin-username`/`admin-password` files
only after published-source, clean-checkout, cluster-UID and monitoring namespace
checks. The directory must be owner-only 0700 and the regular files owner-only
0600. It creates only immutable monitoring `grafana-admin` and a copy of the
existing flux-system `private-registry`; the source credential must contain only
Registry1. It never generates, rotates, prints or exports a credential to GitHub.

All missing inputs receive server validation before the first create. An identical
owned repeat makes no changes; any unowned or mismatched credential refuses
adoption/rotation. A partial first delivery can resume only with the same exact
approved files/source credential. Protected results and stdin stay redacted.
Actual transmission to the cluster requires action-time approval of
`metrics_inputs_apply=true`; default/check mode reads no private input or API.
This does not deliver logging/query/TLS inputs or create an SSO grant.

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
and retains independent local recovery. The narrower initial proposal permits
only explicitly granted own-client admin claims; engineer, viewer, tenant and
unmapped users are denied. No users/clients/Secret values or mappings are created
by this review overlay. The [cohesive Grafana procedure](../authorization/sso/grafana/README.md)
provides separately approved role/client operations and the optional
`local-grafana-sso` native stage, with same-release source rollback.

Pinned Grafana 13.2.1 supports this native configuration. OSS org-role mapping is
not Enterprise Team Sync. Tenant organizations and backend-scoped datasources stay
disabled until separately tested; Viewer can query all permitted org datasources,
and dashboard/folder hiding is not data isolation. Avoid a global expression that
turns any tenant admin into server/org admin in every membership. Per-tenant native
mapping/apply and lifecycle/revocation wiring are not implemented by this overlay.
Test fresh MFA and native roles/denials, independent recovery, stale sessions,
rollback and per-app resources before activation. No new public endpoint is exposed.

The [endpoint and approval plan](metrics-endpoint-plan.md) records the exact new
Service delegation, existing runtime identities, transport findings and unselected
limited-scrape alternative. No host maintenance is included or authorized by #208.

The optional [lab Grafana HTTPS UI](grafana-ui/README.md) has a separate root
and explicit DNS/TLS/network/access preparation. Existing pilot roots do not
select it; publication or healthy Pods alone does not expose a UI.

Grafana's pinned wrapper defaults to a historical automatic migration for
pre-9.3.1-bb.2 installs. This platform starts at 13.2.4-bb.0, so package-local
`autoRollingUpgrade.enabled=false` disables only that obsolete lookup/deployment-
deletion hook. It does not disable normal Helm upgrades or Flux reconciliation.
Do not grant the installer cross-namespace HelmRelease access to satisfy this
unused migration. Regression coverage exercises actual `--is-upgrade` rendering
against a loopback API with the unchanged installer bounds, plus current/old
history calibration and selected-root manifest preservation. Install-only
rendering cannot expose the upgrade-only lookup.

See [monitoring recovery and retained state](recovery.md) for the pinned webhook
trust lifecycle, guarded public-CA recovery, registry override retirement review
and active pilot-path boundaries. This adds no automatic repair or cleanup.
