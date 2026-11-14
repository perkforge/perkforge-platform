# Grafana tenant access design and acceptance map (#218)

2026-11-14. This is a design decision record and pinned native test evidence, not
another deployment, human membership grant or claim of full #40 acceptance.
The current approved Portal profile is **log viewing only**. Its canonical
admins/developers/viewers all receive native org Viewer. The earlier generic
Admin/Editor/Viewer renderer remains available for review but is not the approved
Portal access contract. Platform-admin and platform-engineer authority remain
independent. Do not silently promote tenant admins to Grafana org Admin.

## Authoritative mapping, trust and lifecycle

Platform enrollment owns the context and exact runtime namespaces; namespace UID
and immutable ownership epoch are guarded by admission. An owner-selected context
maps to an explicitly discovered native Grafana org, a fixed read-only query
identity and its org-bound datasource. No browser header, label, dashboard variable
or caller-supplied org ID selects additional authority. Runtime namespaces are not
control namespaces. Multiple namespaces may map to one context's reviewed epoch
set, but additional assignment requires source review; unknown/shared/system
namespaces fall into platform-only storage, never a tenant catch-all.

Alloy uses trusted Kubernetes metadata → write-only gateway → Loki partitions.
Tenant query credentials fix the permitted partition set at the server gateway;
platform-engineer read credentials fix the reviewed federation. The org datasource
contains only its own query credential, never the collector or platform credential.
Native federation has explicit scopes, not a wildcard; multi-tenant tail is not
supported. Tail, push, admin and alternate backend paths stay denied for query
identities. See [query boundary](../../../../observability/log-boundary/README.md),
[ownership guard](../../../../observability/log-namespace-guard/README.md), and
[controlled live probe](../../../../observability/log-boundary/phase-b/README.md).

Keycloak canonical groups project to **owned-client** entitlements. Exact client
mapper and effective scope guards refuse competing groups-claim authorities.
Grafana strict OAuth mapping uses global `None` for non-platform-admin identities,
then exact org mappings; unknown claims fail rather than falling into org1.
Platform admins retain GrafanaAdmin; platform engineers are org1 Viewer, not
implicit administrators. Native org IDs are discovered inputs, not portable
constants. The local profile's already verified ID is only a target selection.

Login-time synchronization is not continuous revocation. Before an ownership
transfer or recipient removal, remove the affected native org membership, revoke
Grafana sessions and separately review service-account tokens, revoke the relevant
Keycloak session/claims and prove fresh/old access denied. Preserve unrelated orgs.
Do not relabel old Loki history into a new owner: allocate a new epoch, remove old
read scope and retain old history under its authorized owner/platform policy.
An unavailable identity source is not permission to adopt unknown memberships.
The current operator-run procedure is explicit; no unimplemented controller is
claimed. Detailed native removal/logout/relogin evidence and credential custody
are in [the org runbook](README.md).

## Rights and disclosure matrix

| Surface | Approved tenant Viewer / engineer Viewer | Platform administration / future richer roles |
|---|---|---|
| Own datasource, Explore and arbitrary LogQL | Read only the gateway's fixed scope; query filters are convenience, not enforcement | Platform federation is separately authorized; no writer credential in any query datasource |
| Foreign org/datasource, forged org header, direct backend | Denied in native/live scoped probes; no shared platform datasource | Platform admins intentionally possess cross-org authority |
| Dashboard JSON, saved queries and ordinary URLs | Own-org read when explicit provisioning/ACL permits; ordinary links still require recipient authentication and membership | Platform Git/native provisioning owns dashboards and ACLs; review imported queries/annotations for platform metadata |
| Dashboard edit, datasource creation, invitations, local user add, service-account creation | Native Viewer denied | Native org Admin can add an unmapped existing user; **not compatible** with canonical-membership-only tenant administration. Admin/Editor are not granted for this release |
| Local/external snapshot creation | Native Viewer denied, including direct API calls | Authorized publisher can create a copy with an anonymous bearer key; org checks cannot protect an already published copy |
| Public dashboard creation/update | Native Viewer cannot create; public write permission is separate from dashboard read | Authorized publisher can expose public dashboard data. This is a deliberate disclosure boundary, not an authenticated tenant endpoint |
| Public artifact consumption | A published snapshot/public-dashboard token is intentionally anonymous | Do not publish sensitive platform/tenant logs or assume org membership protects a published artifact |
| Export/copy/screenshots | Authorized viewers can copy what they can read | Data authorization cannot prevent recipient exfiltration; do not claim DRM |

No tenant-created folder ACLs or inherited Editor rights are part of the initial
profile. Source provisioning determines the own-org dashboard/folder ACL. Merely
hiding Share/Edit controls is insufficient. A dashboard read link does not grant
access, while an already published anonymous artifact does: the distinction must
remain visible in operator guidance. Alert links use only authorized destinations.

### Owner-selected private sharing profile

Where the owner requires **no anonymous Grafana artifacts**, use the pinned native
server controls below as a separately reviewed configuration change:

```ini
[snapshots]
enabled = false
external_enabled = false
[public_dashboards]
enabled = false
```

The owner explicitly selected global sharing-off on 2026-11-14, including platform
admins, while preserving ordinary authenticated viewing. The opt-in
`private-sharing/values.yaml` implements only these three native fields; the
`local-private-observability` root inherits every existing durable-logging object
and appends one ConfigMap reference. Defaults and other selections are unchanged.

The native fixture proves these deny snapshot creation/read even for the recovery
admin and remove the public-dashboard create route. This is global, not per-org.
It does not delete old stored artifacts or copies already exported to another
server. Before activation, inventory existing publications read-only and retain
that evidence privately. Do not print bearer keys or delete publications. Verify
existing publication URLs, if any, and direct APIs after rollout, plus ordinary
authenticated dashboards, datasource health and OAuth configuration preservation.
An existing externally copied artifact requires a separate handling decision;
disabling this Grafana cannot retract copies. Source selection is not live proof.

## Pinned supported mechanisms and actual tests

Grafana OSS 13.2.1, Loki 3.7.8 and Alloy 1.18.0 are the native versions reviewed
here, selected through pinned Big Bang packages. No Enterprise datasource RBAC,
paid identity sync or custom image is assumed. Edition/version verification and
source hashes live in [sources](../../../../observability/tenant-query/sources.yaml).

The checksum-pinned `tests/integration/test_grafana_org_oauth.py` runs a disposable
loopback Grafana and synthetic OAuth issuer, with analytics/plugin updates off.
Only synthetic empty dashboards are used. External snapshot URL points to the
loopback fixture, never a public service. It demonstrates:

- Real own dashboard read/search positive (ACL set before login), foreign dashboard
  read/permissions and platform datasource denial, plus exact org memberships.
- Viewer dashboard writes, local/external snapshot creation, public dashboard
  creation and native membership/invitation/datasource/service-account writes denied.
- With sharing enabled, admin-created snapshot and public dashboard are anonymously
  readable. This preserves the risk as a regression, not a false-denial test.
- With the owner-selected sharing-off controls, admin creation/anonymous snapshot reads
  are denied and public-dashboard creation is unavailable, while org mapping,
  own dashboard reads and the previous revocation regressions still work.
- Existing native mixed AdminA/ViewerB, PE Viewer, platform admin, unmapped-user,
  first-login org1 isolation and membership-removal/logout/relogin tests remain.

The current **live** temporary org-local Viewer probe separately proved actual
Loki marker reads, foreign UID/proxy/query/header/switch denial and token cleanup.
It did not impersonate a tenant or prove fresh tenant-human OIDC/session behavior.
Native fixture results do not establish the live sharing configuration or enumerate
existing publications. No complete backend restore, all-app coverage or retained
history deletion is claimed; those belong to #38/#40, not a design test.

Primary pinned source:
- [Native route authorization and anonymous snapshot read](https://github.com/grafana/grafana/blob/v13.2.1/pkg/api/api.go)
- [Snapshot settings/read guard](https://github.com/grafana/grafana/blob/v13.2.1/pkg/api/dashboard_snapshot.go)
- [Public dashboard routes and write permissions](https://github.com/grafana/grafana/blob/v13.2.1/pkg/services/publicdashboards/internal/api/api.go)
- [Native sharing defaults](https://github.com/grafana/grafana/blob/v13.2.1/conf/defaults.ini)

## All #218 design criteria, without implementation scope inflation

| Criterion | Resolution / remaining decision |
|---|---|
| Authoritative namespace/workload map, shared/multi-namespace/ownership changes | Enrollment + immutable epoch guard + exact reader mappings; source reviewed assignments only, fallback platform-only; transfer procedure above |
| Roles, membership lifecycle and default deny | Explicit Viewer-only Portal matrix, independent PA/PE, canonical owned-client entitlements; native removal/session/token procedure, not automatic sync |
| Supported versions/editions/options | Native OSS orgs + gateway partitions chosen over filters/folders/paid datasource RBAC; exact versions and rejected org Admin bypass documented |
| Explore/API/header/alternate backend access | Server-fixed query scopes and live/native positive-negative probes; tail/write/admin paths excluded, not falsely claimed supported |
| Folder/share/provisioning/snapshot paths | Source-owned read ACLs; Viewer write denials; native anonymous publication behavior and supported global-disable alternative proved. Owner selected global sharing-off; live activation/readback remains separate |
| Positive/negative test plan | Existing fixtures/probe plus new enabled/disabled sharing regression; real human login/session and future broader-role rollout remain explicit controlled acceptance |
| Reviewed matrix, flow, remaining decisions and staged rollout | This document + linked source/runbooks; current release preserves PA/PE/Viewer, future changes source-review→exact approval→native tests→bounded rollout→deny proof; fix forward without silently weakening boundaries |

The owner has selected the supported global sharing-off control. Independent review
and verified activation complete that selected boundary; do not mark broader live
tenant lifecycle or fresh human login completed with this design evidence.
