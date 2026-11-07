# Opt-in logging implementation candidate — inactive

Implements the pinned #38 candidate alongside [metrics](metrics.md); the default root still
selects neither monitoring nor logging. This is not live log or auth acceptance.

## Optional source stage

`clusters/local-logging-pilot` composes the merged Nextcloud stage and metrics
pilot, then enables only the prepared Alloy/Loki packages and a native Grafana
`loki-pilot` datasource in organization 1. It is not selected live. Preservation
tests compare the exact Nextcloud enrollment objects and all existing GitLab,
runner, Headlamp and Keycloak child objects against the metrics pilot.

The datasource replaces the umbrella's automatic editable/plaintext Loki entry
with the authenticated HTTPS gateway, immutable configuration and verified CA/
hostname checks. Grafana references monitoring `loki-query-auth` keys `username`
and `password`, plus monitoring `loki-ca` key `ca.crt`, through environment-backed
native provisioning. No secret value, client-supplied tenant header or automatic
credential copy is added. The single-dollar password expansion avoids Grafana's
documented double-expansion issue. See [native provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/).

Deliver those protected inputs separately, along with the existing collector and
gateway/backend TLS/auth inputs, before selection. Foundation-owned logging/alloy
Namespaces are omitted only from the umbrella render. Failed install/upgrade
cleanup remains disabled. No public route or human OIDC mapping is enabled.

## Optional backend-first stage

`clusters/local-logging-backend` composes the same Nextcloud enrollment and
metrics CRD-only foundation, then enables Loki/Alloy without Prometheus or Grafana.
It preserves every existing rendered package unchanged and the exact reviewed
Loki/Alloy runtime configurations. It omits only two monitoring-namespace Loki
dashboard ConfigMaps and two Alloy ServiceMonitors; these are separate monitoring
integration, not log ingestion/query dependencies. Alloy depends on Loki; no dependency requires the
held monitoring runtime or its kube-system Service grant. No new RBAC or host/
network change is introduced by this source option. Existing reviewed logging
installer/operator/log-reader authority is still required and must be verified.

This can separate backend acceptance from a later monitoring access decision;
it does not bypass approval or select a live root. Merge/publish a verified release,
revalidate owned immutable inputs with `gitops_path` set to this exact root, confirm
live headroom, identities, delegation and current root/source, then obtain any
required action-time approval before guarded promotion. Keep the already approved
10Gi/72-hour logging bounds and collect only the opt-in pilot namespace. No human
access, production namespace collection or Grafana log browsing is enabled here.

For backend acceptance, use only controlled synthetic pilot logs and an owner-local
authenticated TLS query. Verify ingestion/query, wrong CA/hostname/password and
spoofed-tenant/direct-backend denials, unopted-namespace isolation and preserved
existing workloads/claims. Do not place auth values on command lines or print logs
that could contain credentials. Failure stops progression without cleanup or
relaxation. A later separately approved Grafana stage must retain this data and
pass its own datasource, admin-login and isolation checks; this stage is not full
#38/#39 acceptance.

## Initial pilot access

The initial pilot is **platform-admin-only**. Keep anonymous access, tenant
accounts, platform-engineer/viewer access and public Loki/Alloy endpoints off.
The optional Grafana SSO review overlay is not permission to enable its proposed
Viewer mappings during this pilot. No tenant-safe log datasource is implemented.

The gateway's authenticated username supplies the Loki tenant identity; labels
and dashboard filters do not authorize data access. Its current machine identity
permits both reads and writes within that tenant. A Grafana Viewer role does not
turn that credential into a read-only backend identity or isolate separate users.
Do not share this pilot datasource with tenant organizations/users. Separate
datasource/backend authorization and live cross-tenant denials remain gates.

Planned acceptance must exercise correct and incorrect credentials, spoofed
`X-Scope-OrgID`, direct-backend bypass, unopted namespaces and cross-tenant queries.
Inspect actual operator-created workloads and collector configuration before
collecting production logs. Preserve stored logs and existing services on failure;
do not relax authentication, collection scope or network boundaries to pass tests.

The metrics pilot composes the merged Nextcloud enrollment and its
preservation tests compare the exact enrollment objects. A later logging root
must retain that composition. Live service preservation, published-source checks
and verified protected PKI inputs remain independent gates; a successful offline render
does not select either pilot. No concurrent platform-root promotion is performed.

## Who does what and why

The separately approved Ansible actor runs the default-off
[`logging-prerequisites.yaml`](../ansible/logging-prerequisites.yaml). It prepares
logging/alloy namespaces, installer identities, an opt-in pilot namespace, scoped
runtime log reader and ingress policies. Helm-controller impersonates separate
`bigbang:loki-installer` and `bigbang:alloy-installer` accounts. Helm history stays in
each namespace. Installers can manage namespace Secrets; treat them as trusted
infrastructure, not ordinary human users. Alloy installer has named CRD rights
(create cannot be name-limited) and named Role bind/escalate, not cluster-admin.

The supported Alloy operator **ownNamespaceOnly** mode creates Roles instead of
ClusterRoles. Its Role still has broad Secret/workload/RBAC authority inside alloy;
cluster-scoped resource names in a Role do not grant cluster authority. The API
collector uses precreated `alloy-log-reader`, no host mounts, no added capabilities,
and only pods/log in `logging-pilot`. Pod discovery filters the opt-in label
`observability.perkforge.io/logs=true`; RBAC covers the namespace, so that label is
not an authorization boundary. No production namespace or auth/bootstrap logs are
selected. Operator-created workload behavior still needs live verification; a
rendered Alloy custom resource alone does not prove its generated PodSpec.

## Data and trust path

Alloy 1.18.0 reads the Kubernetes log API, applies a narrow password/token/secret
value replacement, and sends through authenticated HTTPS to the native Loki
gateway. This defense is not a guarantee of secret removal: producers must not log
secrets; arbitrary encodings/multiline data are outside the expression. Experimental
`loki.secretfilter` is deliberately off. No blind truncation of oversized entries.

Gateway Basic auth is backed by protected `.htpasswd` Secret `loki-gateway-auth`.
Every proxied location overwrites `X-Scope-OrgID` with the authenticated username
and strips upstream Authorization. Client-supplied tenant headers are not trusted.
Gateway verifies backend TLS against the current physical CA; backend and gateway
require their own correct service-DNS SANs. Loki itself is not an authentication
server. Namespace ingress policies prevent other namespaces bypassing the gateway;
all workloads in logging remain trusted. Verify real enforcement and negative
requests before expanding collection. No external Ingress/controller route exists.

Required future protected inputs (none created here): logging `loki-backend-tls`,
`loki-gateway-tls` (includes public ca.crt), `loki-gateway-auth`; alloy
`loki-client-auth` with chart-required username/password/tenantId/cert/key fields
(empty optional values only where supported), and public `loki-ca` ConfigMap.
An initial platform machine identity would have broad read/write access to its
Loki tenant, **not read-only Grafana or tenant-user isolation**. Choose/review that
identity before activation. Grafana Loki datasource credential delivery and
per-tenant query authorization remain blocked; no password or htpasswd is embedded
in these sources and no tenant UI is enabled. Do not reuse CA signing keys or app
bootstrap tokens for this purpose.

SingleBinary Loki 3.7.8 uses filesystem TSDB on one 10Gi Longhorn PVC with 72h
retention/compactor enabled; one Loki replica is not HA. Longhorn two-copy storage
is distinct from Loki replication_factor=1. Limits start at 1MB/s, 2MB burst,
5,000 streams and 256KB rejected maximum line size. At sustained 1MB/s the disk
would fill long before 72h: retention is not a quota. Measure real ingest,
compression, WAL/index/compaction and snapshots; stop or reduce ingest well before
reserve exhaustion. Operational retention does not define security/audit retention.
No MinIO, caches, canary, duplicated metrics collector or object-store backup.

## Evidence and remaining gates

Offline tests render the exact checksummed Big Bang 3.35.1 child pins, enumerate all
30 chart objects and roleRefs, check installer CRUD/bind/escalate, scoped CR fields,
TLS/tenant overwrite/retention, and run the default-off playbook with changed=0.
Source lookup review found Alloy's legacy upgrade migration lookup and Loki's
StatefulSet recreation lookup; both supported automatic migration/recreation
switches are explicitly off. This is not a proof of every future upgrade branch.

The official Alloy v1.18.0 CLI (revision `a435563`) accepted the exact rendered
7,011-byte collector configuration with `validate` at generally-available stability.
The official `alloy-linux-amd64.zip` archive was checked against GitHub's release
asset digest `92f4c950aec4ec16a7fdbf6f805be4334d4d5fbbe458eecf514319c1c491bef4`.
This checks syntax/components/required properties; it starts no collector and
does not verify the separately packaged Iron Bank runtime image. It uses no
Kubernetes credential or live API. Reproduce the optional check with:

```sh
ALLOY_VALIDATE_BIN=/absolute/path/to/verified/alloy-linux-amd64 \
PYTHONPATH=big-bang-bootstrap/tests PREFLIGHT_SOURCES_DIR=/path/to/pinned-fixtures \
KUBECONFIG=/dev/null python3 -m unittest \
  security.test_logging_installer.LoggingInstaller.test_optional_exact_alloy_binary_validates_rendered_configuration -v
```

See the [official release](https://github.com/grafana/alloy/releases/tag/v1.18.0)
and [validator scope](https://grafana.com/docs/alloy/latest/reference/cli/validate/).

No Loki binary validation, controller execution, network/auth allow/deny,
actual log ingestion/query/redaction/cardinality, disk retention/load, admin login,
upgrade/redeploy or independent restore has run. Preserve the Alloy CRD and data;
chart uninstall includes finalizer/removal hooks and needs separate approval.
No source selection or permissions are deployed by merging this inactive draft.
A later release/promotion requires reviewed capacity, PKI/credential delivery,
operator CRD compatibility and successful scoped pilot evidence. Never repair
an auth failure by allowing anonymous ingress or widening tenant headers/RBAC.

References: [pinned package sources](sources.yaml),
[Loki authentication](https://grafana.com/docs/loki/latest/operations/authentication/),
[Loki multi-tenancy](https://grafana.com/docs/loki/latest/operations/multi-tenancy/),
[Alloy processing](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.process/).

## SSO versus log API authorization

`logging-sso-review.yaml` keeps human entry through the separate Grafana OIDC client.
Loki and Alloy do not acquire fake browser clients; protected machine credentials
and approved Kubernetes identities remain separate. Namespace/label opt-in is not
query isolation. A tenant must not supply a trusted X-Scope-OrgID header directly;
backend-scoped datasource/proxy enforcement and cross-tenant denial tests are still
activation gates. No new proxy, public ingress or unreviewed group mapping is
implemented here. Existing log-storage, retention and capacity gates remain.
