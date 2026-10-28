# v0.2.0 baseline preflight — hold live installation

**Recommendation: do not co-install this stack on the current VMs, and do not
rebuild them merely to try the unchanged resource profile.** Prefer the separate
physical `dev` cluster when ready. A local trial first needs a reviewed smaller
Flux/resource profile and a preservation/discard decision for existing data.
Nothing here deploys, resizes or rebuilds anything.

This report preserves the published v0.2.0 baseline. The proposed local-only
[smaller profile and staged protocol](LOCAL-TINY.md) is a separate comparison;
dev stays on this baseline. Request-fit still is not runtime validation.

## Measured now vs rendered candidate

Read-only snapshot: 2026-10-28 16:29–16:34 UTC. Both nodes Ready, no pressure
conditions; metrics are a point in time, not a startup/load test.

| Current VM | vCPU | allocatable MiB | requests CPU / MiB | working set MiB | root free GiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| cks-control | 2 | 3,653 | 1.575 / 2,520 | 3,127 | 16.3 |
| cks-worker | 2 | 3,653 | 1.260 / 2,304 | 2,367 | 69.0 |

Each VM has 4 GiB configured RAM (30/100 GiB disks). The host has 14.96 GiB RAM,
2.76 GiB available and 10.4 GiB swap used; 16 logical CPUs. Do not increase guest
RAM to force a fit. Node allocatable equals reported capacity, so it is not an
application-only memory budget. Eighteen live Pods have at least one container
without a memory request; Rancher, Fleet and several base services therefore consume more than request sums show.

The **local render-only candidate**, not Big Bang defaults, contains nine steady
Pods plus one disabled/unsized manual Helm test Pod:

| Component | Pods | requests CPU / MiB | limits CPU / MiB | PVC GiB |
| --- | ---: | ---: | ---: | ---: |
| Pinned Flux bootstrap | 4 | 1.600 / 2,208 | 3.200 / 4,448 | 0 |
| Headlamp | 1 | 0.100 / 128 | 0.500 / 256 | 0 |
| Keycloak + PostgreSQL | 2 | 1.250 / 1,280 | 2.500 / 2,560 | 4 |
| OpenBao | 1 | 0.100 / 256 | 0.500 / 512 | 10 |
| Portal | 1 | 0.025 / 64 | 0.250 / 192 | 0 |
| **New stack only** | **9** | **3.075 / 3,936** | **6.950 / 7,968** | **14** |

These are rendered declarations, not measured use. Current scheduling space is
only 1.165 CPU; Flux alone needs 1.6 CPU. Its 900m helm-controller cannot fit on
either node's remaining CPU requests. Coexistence fails before adding the apps.

The clean estimate does **not** retain Fleet or the current apps:

| Observed group | requests CPU / MiB | Pod working set MiB | Clean estimate |
| --- | ---: | ---: | --- |
| RKE2 `kube-system` only | 2.175 / 2,776 | 2,730 | Retained |
| Rancher/Fleet (`cattle-*`) | 0.010 / 128 | 1,193 | Removed |
| Other apps/operators/storage | 0.650 / 1,920 | 1,072 | Removed/replaced |

A like-for-like clean estimate retains that RKE2 system profile (including DNS,
metrics and Traefik), then adds the new stack: **5.25 CPU / 6,712 MiB combined**,
before unrequested OS/CNI, storage and other overhead. It is an estimate for this
unchanged base profile, not a universal Kubernetes minimum or a measured rebuild. That exceeds the existing four vCPU. Memory limits
of the new stack alone exceed the two nodes' combined allocatable RAM. Limits
are ceilings, not reservation or a prediction, but there is no defensible peak
budget here. The actual templates also permit a simultaneous maximum Deployment
surge of another 1.4 CPU / 1,952 MiB; this is a rollout scenario, not a measured
startup peak. The dev assembly also renders for regression, preserving its explicit
two-Headlamp override; this table is local only. Keycloak image build/startup and
database initialization still need live measurements on an approved target. Stateful upgrades here have no HA reserve.

## Why a small subset may still be viable after tuning

Your app-count intuition is reasonable: excluding Flux, the new five app/DB Pods
request **1.475 CPU / 1,728 MiB**, versus **0.660 CPU / 2,048 MiB** requested by
all current non-kube-system workloads. Their observed working set is about
2,265 MiB; that is usage, not a comparable guarantee for the new stack. The
candidate Keycloak alone requests 1 CPU / 1 GiB versus the live app's 250m /
768 MiB. It may be conservative for this trial, but startup must be measured
before changing that request or its 2 GiB limit.

The larger difference is Flux. The **same pinned** generated `gotk-components.yaml`
starts with upstream requests of **350m CPU / 256 MiB** across four controllers;
Big Bang's `base/flux` then patches them to **1,600m / 2,208 MiB**. These are
production-oriented declarations, not evidence that four tiny repositories
consume that much at idle. Merely substituting the upstream request figures
would reduce the clean arithmetic to **4.000 CPU / 4,760 MiB**: exactly all four
vCPU, with no scheduling/CPU startup margin. This is an illustration, **not an
implemented profile or a safe runtime claim**. Upstream limits are still 1 GiB
per controller, so low requests alone do not establish a memory budget.

The core source/kustomize/helm controllers are required by this design. Notification
is optional only if Alerts/Providers/Receivers are not used; dropping it would
save just 100m / 200 MiB at Big Bang's current requests and requires an explicit
bootstrap/readiness change. Keeping four controllers and measuring smaller,
reviewed requests is clearer than silently removing one. All unrelated Big Bang
packages are already disabled; there is no large hidden observability stack to cut.

A tuned clean trial is **plausible, not established**. The next bounded experiment
should be separately authorized: a clean target with preserved/discarded data
settled, same pinned controllers/images, reviewed tiny controller resources, then
measure cold source fetch plus Helm reconciliation before adding DB/Keycloak and
finally UI/OpenBao/portal. Record per-node placement, guest/host working set,
startup/reconciliation peaks and rollout reserve. Reserve explicit system and
largest-Pod/upgrade headroom; neither aggregate requests just below capacity nor
a low idle sample proves fit. No smaller profile is implemented in this PR.

## Exact selection and remaining gaps

- Big Bang **3.35.1** supplies Flux **2.9.5**, four Iron Bank controllers and
  **11 CRDs**. Controller resources come from its unchanged `base/flux` patches.
  Existing cluster has Fleet/Rancher and no Flux CRDs; choose one lifecycle owner.
  The base still grants cluster-admin to reconciler controllers; hardening and
  scoped platform/tenant identities remain review gates before unpause.
- Headlamp **0.45.0-bb.1**, upstream **0.45.0**, gluon **1.1.9**, bb-common **1.6.0**.
  Wait/Cypress jobs are disabled; no Headlamp ClusterRoleBinding renders. A pinned
  Flux plugin, OIDC/API trust and per-user denial tests remain unfinished.
- Keycloak **7.3.2-bb.1**, app **26.8.0**; vendored keycloakx **7.3.2**, PostgreSQL
  chart **18.12.4**, Iron Bank PostgreSQL **18.6**, gluon **1.1.9**, bb-common **1.6.1**.
  Supported existing-Secret inputs remove packaged example credential Secrets.
  The default probe checks Bitnami initialization marker files; the candidate
  uses supported `customReadinessProbe` with `pg_isready` to avoid assuming that
  filesystem contract for the selected native image.
  Render checks prove wiring, not image startup or authenticated DB connectivity.
- Official OpenBao chart **0.30.6**, image **2.7.2**; injector off. Its default
  single-server file backend/TLS-disabled configuration is **not approved for use**.
  TLS, backend/recovery/unseal custody and backup design remain separate gates.
  A `system:auth-delegator` binding renders and needs review. The chart's test Pod
  has no resources; Flux Helm tests are disabled, so it is excluded from steady
  totals, not counted as zero-cost if later enabled.
- Portal config **v0.1.0**, chart **0.1.0**, previously approved image digest from
  its bundle; runtime image/source are unchanged. App chart stays tenant-owned.
  Only its offline render uses `enabled=true`; authored app defaults remain off.
- No ESO, CNPG, mesh, observability or cert-manager is installed by this candidate.
  The embedded DB avoids adding another DB operator. DNS/CNI, ingress, storage,
  API trust, source/registry credentials and security foundations are prerequisites,
  not free services. Current Traefik/CNI/DNS costs are in the measured RKE2 baseline.

Repo1 archives were anonymously readable and all chart dependencies are vendored;
no chart registry login or dependency install was needed for rendering. Runtime
Flux/Headlamp/Keycloak/PostgreSQL images use `registry1.dso.mil` and require reviewed
Iron Bank access/pull setup. OpenBao uses Quay; portal uses GHCR plus the existing
pull-secret contract. No image pull or registry authentication was tested; no
registry credentials were inspected.
The committed `sources.yaml` pins public test archives by SHA256; charts and
rendered workload YAML are not vendored into this repository.

The two candidate PVC classes remain unset: choose an approved per-provider
storage class. Current `local-path` is node-bound, WaitForFirstConsumer, Delete;
14 GiB requested is neither resilience nor a backup. Headlamp/Keycloak mesh routes
produce no usable Traefik ingress while mesh is off. Platform-owned ingress/TLS,
DNS for the agreed hosts, Keycloak realm/clients, Kubernetes API OIDC groups/RBAC,
namespace/deployer/runtime grants, network/admission/quota and source identities
remain missing. `keycloak-bootstrap-existing` must supply reviewed bootstrap admin
environment keys; `keycloak-database-existing` needs `password` and
`postgres-password`. This PR references those Secrets; it creates no credentials.

## Existing ownership and preservation gate

Fleet currently owns release `keycloak` in namespace keycloak and release
`openbao` in namespace openbao, matching this candidate's names. It also owns the
active household portal; do not point a new Flux owner at those resources.
Live Keycloak is **26.8.1** on PostgreSQL **17.6**: this package is not an in-place
upgrade, and PG18 must not mount the old database PVC. Nextcloud is currently
scaled to zero/paused but its 6 GiB PVCs remain; paused is not disposable data.
Current PVCs total 23 GiB, including Keycloak 4 GiB, GitLab/Valkey 10 GiB and OpenBao
3 GiB. OpenBao recovery material and the stable portal/identity configuration also
need a preservation decision; no backup/restore is proven by this preflight.

If local experimentation is required now, the next proposal should be a bounded
smaller resource profile, then staged Flux → DB/Keycloak → OpenBao → UI/portal
measurement on a separately approved clean target. Do not weaken limits/policies
or add RAM merely to make this arithmetic pass. Otherwise use the future three-node
physical target and budget it from fresh evidence; its capacity is not validated here.

Before **any** live action, obtain separate explicit approval for the target and
controller owners; a preservation/backup or discard decision for every affected
PVC/service; any destruction of **cks-control and cks-worker disks**; registry/source
credential provisioning; DNS/TLS/API identity/security setup; and later activation.
The user's disposable-VM preference is not execution authorization for this rebuild.

## Reproduce the offline result

To reproduce this historical table, use the v0.2.0 checkout; the current local
profile produces the smaller numbers in LOCAL-TINY.md. From repository root,
with existing Helm/kubectl/Python/PyYAML and app checkout at
its selected published release:

```sh
python3 local-lab-big-bang/tests/fetch_preflight_sources.py /tmp/minimal-sources
PREFLIGHT_SOURCES_DIR=/tmp/minimal-sources \
ENROLLMENT_CHECKOUT=/path/to/enrollment-v0.1.1 \
TENANT_APP_CHECKOUT=/path/to/portal-v0.1.0 \
CAPACITY_REPORT_DIR=/tmp/minimal-inventory \
  python3 -m unittest discover -s local-lab-big-bang/tests -v
```

Only the fetch step reads public artifact URLs; renders use vendored dependencies
and `KUBECONFIG=/dev/null`. Numeric inventory JSON stays temporary. Test code reads
the actual ordered valuesFrom keys and the render-only `preflight/values.yaml`.
Neither cluster root includes that opt-in file; Keycloak remains disabled in both.
Helm emits a known table-coalescing warning when null removes this package's default
credential table; tests require no generated credential Secret and real external
references. Tests are not a live auth/network/storage/load proof.

Primary pinned sources: [Big Bang Flux](https://repo1.dso.mil/big-bang/bigbang/-/tree/3.35.1/base/flux),
[Keycloak package/dependencies](https://repo1.dso.mil/big-bang/product/packages/keycloak/-/blob/7.3.2-bb.1/chart/Chart.yaml),
[package values](https://repo1.dso.mil/big-bang/product/packages/keycloak/-/blob/7.3.2-bb.1/chart/values.yaml),
[Keycloak 26.8.0 container sizing/startup](https://github.com/keycloak/keycloak/blob/26.8.0/docs/guides/server/containers.adoc).
