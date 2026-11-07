# Harbor isolated data candidate

Unselected public source; data and app activation are not wired yet. No cluster root
includes these manifests or the watch patch; Valkey is suspended. Do not apply
this directory directly or rerun the shared operator's original foundation.
Harbor, its OIDC client, scanner and CI remain off.

## Proposed scope

- One dedicated CNPG PostgreSQL 17.11 instance and one TLS/authenticated Valkey
  7.2.15 instance, reusing the existing reviewed pins. Existing GitLab/Nextcloud
  stores, cache, credentials and PVCs are untouched.
- PostgreSQL: 8Gi dedicated Longhorn, 250m/512Mi requests, 1 CPU/1Gi limits,
  100 connections, no superuser login, plaintext rejected. Harbor's one core pool
  remains capped at 50 open/10 idle; scanner/exporter remain off.
- Valkey: 2Gi dedicated Longhorn, 100m/256Mi requests, 500m/512Mi limits,
  128Mi no-eviction cache, persistent AOF, one Recreate writer. Init resources
  are also bounded. These small budgets require workload acceptance, not just Ready.
- Both data Pods require storage-capable workers. The app connection overlay
  also gives registry/jobservice worker placement and Recreate for their RWO claims.
- Data ingress defaults to deny. Only Harbor core reaches PostgreSQL; only core,
  jobservice and registry reach Valkey. The existing CNPG operator may reach its
  database health/control ports. This does not implement full application ingress,
  internal TLS or egress policy, and host-local paths need independent testing.

## Authority and protected inputs

The separate owner-admin prerequisite bundle grants no new cluster authority.
It proposes the existing CNPG namespace Role unchanged in `harbor`, bound only
to the existing `cnpg-system/platform-cnpg` account. That role includes management
of Harbor Secrets/workloads and Pod exec. Adding the namespace is a material
access expansion and needs explicit action-time approval.

`operator-watch-review.yaml` adds `harbor` while retaining `gitlab` and
`tenant-home-nextcloud` in both the chart values and native Deployment patch.
It is not included in any build. Changing the shared operator requires a fresh
read-only comparison against the current watches, followed by the approved narrow
GitOps rollout and preservation checks. Never replace a newer watch list with this
snapshot or create another operator.

The separate `bigbang/harbor-data-installer` gets Valkey workload/Helm-history
CRUD only in Harbor, with no bind/escalate/cluster grants. It has no shared
`bigbang` Secret-history access. Test hooks are disabled. `platform-reconciler`
gets only Harbor Cluster/NetworkPolicy reconciliation and Pod health reads;
namespace/Role creation remains an owner-admin task.

No Secret values or credential generator are included. Future protected Ansible
preparation must create/reuse exact owned immutable inputs without rotating them:

- `harbor-database`: basic-auth `username=harbor` and `password`, used by CNPG
  bootstrap and Harbor's existing password reference. Never reuse another app's
  database or credential.
- `harbor-valkey-acl`: key `default`; `harbor-redis`: the identical dedicated
  password under `REDIS_PASSWORD`. Password-only default-user auth is deliberate.
- `harbor-valkey-tls`: `tls.crt`, `tls.key`, `ca.crt`, with the service FQDN in
  its SAN. Server-only TLS is required; Harbor does not support cache mTLS here.
- `harbor-public-ca`: public CNPG server CA plus the approved Valkey/service CA
  trust roots under `ca.crt`. Do not export any CA signing key. Preserve the
  explicit core `PGSSLROOTCERT` path and verify native hostname/CA enforcement.

The pinned Harbor chart resolves Redis credentials through Secret lookups into
its private runtime configuration. Real credential-bearing rendered output must
never be committed, printed or placed in a public fixture cache. Offline renders
use absent/synthetic Secrets only. PostgreSQL/Valkey certificates, password
agreement and container trust loading remain unverified.

## Guarded prerequisite procedure

`configuration/ansible/harbor-prerequisites.yaml` defaults to no contact, including
check mode. After explicit approval it creates only the thirteen authored namespace,
installer and namespaced Role/binding objects. It never changes the operator,
watch list, credentials, workloads, source selection or existing objects.

- Requires a clean exact published-release checkout and matching release evidence.
- Pins the API, cluster UID, protected kubeconfig and existing operator UID,
  chart/image, service account, readiness and both retained namespace watches.
- Validates every existing target before writing anything. Foreign ownership,
  rule/subject drift, token mounting and terminating objects are refused.
- Creates and reads back one missing object at a time. A failure or uncertain
  response stops further writes; keep completed objects and inspect before retry.
- A repeated approved invocation reuses exact owned objects, preserves their UIDs
  and makes no changes. There is no patch, adoption, rotation or automatic cleanup.

Use the existing `configuration/ansible/inventory.yaml` with an owner-only extra
vars file containing the published release evidence/target inputs,
`harbor_expected_api`, `harbor_expected_operator_uid`,
`harbor_foundation_scope=harbor-foundation-v1` and
`harbor_foundation_apply=true`. The scope string is a guard, not authorization.
Keep the current accepted root selection; the procedure does not promote a root.
Real authority acceptance and operator/data readiness are separate from fixtures.

## Cumulative capacity gate

Read-only sample on 2026-11-07 at about 14:40 UTC: all three nodes and 15 releases
were Ready, with no unready active Pods. Live source was v0.26.0; v0.28.0 publication
had not deployed Harbor.

- Worker CPU requests were 5.270/6 and 5.045/6 cores, leaving 1.685 cores total.
  Actual utilization was low, but requests determine scheduling.
- Worker finite memory limits were approximately 99% and 90% of allocatable.
  Several existing containers are unbounded; finite totals are not real ceilings.
- This data candidate requests 350m/768Mi, with 1.5 CPU/1.5Gi limits. CNPG's
  generated init work and migration peaks still need exact runtime validation.
- Current scanner-off Harbor native chart requests 600m/1536Mi across six
  containers, before any tuning needed for reliable startup or push/pull load.
  Data plus app requests therefore begin at 950m/2304Mi. No fit/performance claim
  follows, and this does not budget later Grafana/backup/other queued changes.
- Proposed data adds 20Gi of two-replica scheduled storage; registry10Gi plus
  job logs1Gi add another22Gi, total42Gi. Of that, 40Gi is dedicated-disk replicas
  and 2Gi remains on root-disk Longhorn. Retained smoke claims stay untouched.
  Snapshots, growth, migration, restore and backup headroom are additional.

Recalculate per-node scheduling, limit overlap and storage budgets immediately
before activation. Do not shrink existing apps or reserve space intended for
backup work without a separate reviewed decision.

## Remaining sequence and approvals

1. Review/release this inactive source and its guarded prerequisite procedure.
   Complete private input/CA delivery before any data-stage activation.
2. Approve the isolated data sizes/resources, Harbor-only CNPG access expansion,
   protected credentials/certificates and exact foundation objects. Then add a
   data-only root based on the latest accepted app stack, preserving all existing
   selections and watches; publish/review the new immutable release.
3. Separately approve source/root selection and data-service activation. Verify
   TLS, correct credentials, wrong password/CA/hostname/plaintext/cross-namespace
   denials, one bounded persistence test and unchanged existing apps/PVCs.
4. Complete app protected inputs, internal transport, egress, trusted external
   routing and native release behavior. Deploy an empty scanner-deferred pilot,
   verify built-in local admin, authenticated push/pull and denied access.
5. Implement the dedicated Keycloak client plus guarded Harbor OIDC API adapter;
   approve credential delivery and the explicit platform-admin mapping before
   activation. Configure OIDC before creating local non-admin accounts. Preserve
   built-in local recovery and all projects/images/robots. Verify named MFA login,
   local recovery and unmatched/non-admin access separately.

SSO is not implemented by these data manifests. Tenant project sync/offboarding,
robots, CI publishing, Trivy/scanning and isolated restore remain separate gates.
No successful offline render counts as a live TLS, CNI, data or login test.
