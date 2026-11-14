# Scoped native Loki boundary: inactive source preparation (#38 / #218)

No root selects this directory, no credential is created and no permission or
collection is changed by rendering. Native Big Bang 3.35.1 / Loki 3.7.8 / Alloy
1.18.0 images remain unchanged. This is configuration, not a new proxy service.

## Contract

`render.yaml` defaults off/check-mode inert. Explicit local inputs supply a fresh
private output directory; TLS certificate/key/CA and htpasswd **paths**, not values;
listener/backend TLS names; a writer and platform-reader username; `log_scopes`
(exact authoritative namespace + immutable ownership-epoch `scope_id`);
`log_readers` (unique username + nonempty authorized `scope_ids`); and
`log_legacy_scopes` (platform-readable old pilot IDs, never tenant-readable).
`log_fallback_scope` is `platform-unassigned-v1`. No caller can select query scope.
Generated native gateway config enforces separate methods/endpoints: collector
POST push only with one registered nonlegacy scope; query identities read only,
with the server overwriting any supplied tenant header. Unknown identities/scopes
and tail, delete, rules, admin, UI, encoded paths and generic passthrough are denied.
Only query/query_range/series and label discovery are candidates; actual pinned
Loki federation and Grafana endpoint behavior must pass before live exposure.

Alloy stages must follow trusted Kubernetes namespace relabelling and no payload
stage may replace that ownership label. First route to platform-only fallback,
then exact owned namespace→epoch mappings. No duplicate ingestion. Platform reads
an explicit generated federation list of fallback + registered epochs + legacy
pilot. New unknown/system namespaces remain visible to platform engineers in the
fallback, but never become tenant-readable automatically. Loki has no wildcard
federation; tail does not support multi-tenant federation and stays disabled.

Namespaces cannot be renamed in place. Namespace reuse or ownership transfer
requires a new epoch ID and removal of the former read mapping; old epochs remain
platform-only until retention. A namespace name alone is not a durable ownership
identity. Existing pilot data must never be relabeled or exposed as tenant data.
A generated immutable inventory of authoritative context mappings is required;
this renderer does not discover or infer membership from pod labels or log text.

## Pending exact live batch and capacity gates

Proposed `alloy-cluster-pod-log-reader` ClusterRole/binding grants only the existing
`alloy:alloy-log-reader` pods get/list/watch and pods/log get; no Secrets/exec/nodes.
Separate protected writer, platform-reader and Portal-reader credentials require
reviewed OpenBao/ESO custody and exact consumer delivery, not shared machine
read/write credentials in tenant datasources. Per-org Grafana membership and
isolated query credentials are a separate coordinated #218 integration.
No network expansion is necessary for existing Alloy/Grafana→gateway endpoints;
backend bypass and selector-tightening must still be tested. No tenant org gets
the platform credential or raw Loki access.

The existing 10Gi/72h pilot and idle collector do not establish capacity for the
observed 101 active pods / 154 container specifications. Stage actual collection,
measure sent/dropped/retried bytes, PVC growth and CPU/memory, and expand only after
resource review. A per-tenant 1MiB/s ingestion cap is not a global storage bound.
Do not silently drop arbitrary debug/security records, claim general secret
redaction from a pattern test, resize storage or change resources without review.

Native component allow/deny tests are necessary but not proof of deployed tenant
isolation, namespace-transfer lifecycle, all Grafana APIs or durable delivery.

## Rendering and verification

Supply `log_runtime_dir` separately from `log_output_dir`: runtime nginx writable
paths must be valid inside the pinned gateway pod, never a desktop artifact path.
The output must not already exist; rerender into a new private directory.
`log_collection_namespaces` is an explicit nonempty staged namespace list.
Only `log_collect_all_namespaces: true` together with an empty list selects all
namespaces. The source emits the exact cluster reader prerequisite separately;
rendering neither applies it nor removes the existing pilot Role/RoleBinding.
`boundary-values.yaml` is an additive final umbrella values input; it preserves
existing processing/redaction, immutable images/resources, TLS volumes and pod
security. `labelSelectors: null` intentionally removes the old pilot opt-in
selector rather than merging an empty object into it.

The local test uses real nginx, TLS and synthetic BasicAuth against a recording
HTTPS backend. It verifies server header replacement, writer/read endpoint
separation, fixed federation, unsafe input rejection and strict paths/methods.
With `PREFLIGHT_SOURCES_DIR` pointing at the exact pinned Big Bang/Loki/Alloy
charts it also checks actual umbrella/child renders and unchanged pod image,
resource and security settings. This is not a substitute for pinned-image live
Loki isolation, Grafana per-org authorization, or tenant lifecycle verification.

Before promotion: bind scope inventory to authoritative tenant context/ownership
revision; create distinct protected identities with exact-record ESO delivery;
verify no raw-backend network bypass; provision query identities only to their
approved Grafana org; prove tenant A cannot query B/fallback/legacy through header,
LogQL, labels/series, datasource proxy or direct gateway requests. Keep tenant
access disabled until all denial checks pass. Record actual collection coverage
and resource budget separately from permissions capable of wider collection.

The pinned chart maps `resource.opentelemetry.io/*` pod annotations into ordinary
labels after its initial namespace/pod/container assignment. Therefore the boundary
explicitly resets namespace, pod, container and job from reserved Kubernetes
metadata in **final** `extraDiscoveryRules`, after every annotation/label mapping.
This prevents an application annotation such as `resource.opentelemetry.io/namespace`
from selecting another ownership partition. Kubernetes annotation name syntax
forbids a leading underscore, so this map cannot manufacture reserved `__meta_*`
source names. The exact-render regression checks rule ordering and malicious input.

## Dedicated runtime custody and Phase A

`custody.yaml` renders only four fixed KV-v2 records under `platform`:
`logging/boundary/{gateway,collector,query-platform,query-portal}-v1`.
It emits separate exact-record policies, exact-SA short-lived auth roles, public CA,
empty named target Secrets and Merge/Retain ExternalSecrets. ESO receives only
named Secret get/update/patch, not namespace-wide Secret create/delete. The existing
controller-wide cache is unchanged. No consumer may read another record.

`seed.yaml` is explicit/default-off/check-mode inert. It creates a private retry
bundle once, checks every remote record before writing, creates missing records
with CAS zero, accepts only exact equal retries and verifies readback. Keep that
protected bundle for partial retry; do not regenerate or overwrite mismatches.
The optional `logging_legacy_htpasswd_file` must contain only the existing exact
`platform-pilot` hash line, copied privately from the verified existing gateway
Secret. It preserves that credential, not a new grant or password rotation.

`activate-custody.yaml` is separately explicit. Existing resources must carry the
exact source ownership label and match their expected content. It refuses foreign
adoption, creates missing resources only, never reapplies empty Secret data, checks
existing policies/roles for exact scope before writing missing identities, waits
for ESO and verifies exact decoded payload. It selects no root and restarts nothing.

Phase A uses `log_readers: []`, leaving tenant query authorization disabled even
though its protected credential is prepared. `log_legacy_reader: platform-pilot`
retains read-only access to its exact legacy pilot partition, preserving the old
datasource while new platform queries use `loki-platform`/`pf-log-platform-read`.
Legacy writes are rejected after cutover. Switch gateway/collector in a coordinated
window after verifying the old opt-in pilot has no live producers; otherwise
review buffering/collection impact before proceeding. The tenant lifecycle guard
and actual cross-scope denials remain mandatory before tenant exposure, not a
reason to block reviewed platform-only collection.

Native Alloy also needs its own namespaced `get/watch` on the exact
`alloy/loki-boundary-collector-v1` Secret for `remote.kubernetes.secret`.
The separate `alloy-scoped-client-secret-reader` Role/Binding grants only that
consumer identity, not cluster-wide Secret reads or any query credential. ESO
success alone does not prove the collector can read its destination credential.
Verify both `auth can-i` and actual component reload/ingestion before acceptance.
