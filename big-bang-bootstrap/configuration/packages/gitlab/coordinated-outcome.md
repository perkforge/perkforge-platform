# One coordinated GitLab, Keycloak and runner outcome

This feature reconciles only GitLab scope from old #114 against current
main, preserving the existing application acceptance evidence. No observability
predecessor is a runtime dependency and no old PR base is retargeted. All normal
roots and the combined review profile stay disabled. Dormant activation roots
require explicit selection. The approved provider and data stages are accepted as observed on 2026-11-04.
CNPG, TLS Valkey, PostgreSQL and Garage are Ready on prepared workers. Released
v0.17.4 bootstrap initialized one Garage layout, one read/write-only key without
admin/createBucket authority and six buckets; final repeat changed zero. Live
TLS/hostname, authentication and negative cases, namespace connectivity denials,
normal Pod replacement persistence and dummy/probe cleanup passed. Public CNPG
client CA delivery passed without exporting its signing key. Original claims and
ten immutable credential identities remain preserved.

Separately approved v0.17.5 delivered only the GitLab namespace Pod health-reader
Role/binding. Exact readback, preservation of 35 prior prerequisite objects,
zero-change repeat and twelve positive/negative permission checks passed. Flux
root, three nodes and eight releases are Ready; no active Pods are unready and
attached Longhorn volumes were healthy. During that data-stage acceptance runtime
remained v0.17.3; the later app attempt below selected v0.17.6.

Read-only checks from all nodes found Garage anonymous access denied on its local
worker and unreachable from the other nodes; the admin listener was unreachable
everywhere. PostgreSQL CA/hostname verification passed on its local worker; the
other nodes timed out. This is neither blanket node-origin NetworkPolicy isolation
nor independent backup/restore or node-failover proof. GitLab workloads were still
off at data acceptance; the later app attempt is described below. SSO, runner and
drive access remain off and separately gated. Source publication and
live activation require their own approvals.

## Current app attempt and first-install recovery gate

The approved v0.17.6 app preparation delivered the GitLab pull credential and
public trust objects, each with a zero-change repeat; existing data credentials
and TLS leaves were reused. The separately approved v0.17.7 promotion resolved
umbrella Namespace rendering without adopting the foundation Namespace or adding
cluster-wide rights. Its first GitLab install then failed before its shared-
secrets hook could start because image-pull references were absent.

Observed 2026-11-05: the approved old never-started hook cleanup and v0.17.8
promotion completed. Both global pull-Secret lists now reference only existing
`private-registry`, and the new upgrade-check image pulled successfully. GitLab
still has two failed Helm revisions and no successful install. Flux selected an
upgrade after the failed install's configuration changed. The real
`gitlab-gitlab-chart-info` ConfigMap was never created by the failed first install;
the pre-upgrade guard rejects that missing metadata with a generic unsupported-
upgrade-path message. This is not evidence of an actual GitLab version jump.
Final-failure remediation then reported `MissingRollbackTarget` because there is
no successful revision to roll back to. At that earlier diagnosis no migration or Gitaly claim had started; the later
partial recovery is recorded below. Three data Pods and four bound claims retain their
observed identities. GitLab/root readiness remains unaccepted; SSO, named grants,
runner and drive access remain outside this recovery.

### Partial recovery and public CA mount correction

Approved v0.17.9 recovery staged the reviewed source/policy with root, umbrella
and child paused. Native revision 3 hit the CLI watcher's broad Role-list request.
Four bounded Helm 4.2.4/current-RBAC tests verified legacy hook/job waits, including
terminal hook/migration failures; optional namespace probes remained denied.
Approved revision 4 then passed hooks and created real chart-info and workloads.
Gitaly and Shell became Ready; the new 10Gi Gitaly claim is Bound. Migrations,
Toolbox and dependency containers cannot create a PostgreSQL CA mount under the
chart's read-only `/etc/gitlab` configuration volume. The native wait was cancelled
without cleanup. Revisions 1–4 remain failed; all three reconcilers remain paused.
Original data services, four claims and eleven credential identity/content checks
passed after failure. Generated app Secrets and the Gitaly claim are preserved.

The permission boundary is intentional: Role/RoleBinding reads are restricted to
`gitlab-shared-secrets`. Do not add namespace-wide RBAC reads to accommodate a
manual CLI waiter. If a separately approved native Helm 4 recovery is needed,
retain all hooks and use `--wait=legacy --wait-for-jobs` with the reviewed timeout;
never substitute hook-only/no-wait, take-ownership or skip validation. Flux's own
polling waiter is different, so do not change its wait strategy to copy the CLI.
The installer regression checks both allowed named reads and denied unrelated
Role/RoleBinding reads. No extra permission was granted during recovery.

The durable fix changes only PGSSLROOTCERT and mountPath to
`/etc/gitlab-postgres-ca`, retaining verify-full, public CA ConfigMap/key,
readOnly/root filesystem protections, images, resources, RBAC and storage.
Regression rendering checks eleven consumers: five app containers, four configure
init containers and two dependency init containers. It reproduces seven old
read-only parent collisions and compares the full render after normalizing only
CA paths and ordinary values-hashed Job names.

From the bootstrap directory, explicit offline fixture
`tests/fixtures/gitlab-ca-mount-runtime.py` uses the cached pinned webservice CNG
image with no network, pulls or credentials. It checks read-only parent mkdir
rejection and successful sibling mount/read-only enforcement. Podman can precreate
nested mount destinations differently from kubelet; this is not a complete kubelet
or all-image rehearsal. Native libpq tests skip if the host library is absent;
rendered verify-full and existing transport evidence do not replace live acceptance.

Review and release this source correction before retry. Recheck partial resource
ownership, all five claims, private inputs and chart-info while paused; deliver
corrected source-owned values before allowing parent-owned child resume. Real
chart-info now allows assessment of an ordinary Flux-managed upgrade, retaining
all hooks/job checks, rather than another fresh installation. No concurrent Helm
actions, writable configuration directory, TLS downgrade, data reset, credential/
certificate rotation or new RBAC is needed. Publication alone does not authorize
live repair. Preserve data/history and stop on unexpected state.

### Preserve failed state explicitly

Big Bang merges its global Flux failure settings into the child release.
`retries: 0` alone leaves `upgrade.cleanupOnFail: true` and
`upgrade.remediation.remediateLastFailure: true`. The released v0.17.9 correction sets
`cleanupOnFail: false` and `remediateLastFailure: false` for upgrades, and
explicitly sets install `remediateLastFailure: false`. Both retry counts stay
zero. Pinned rendering proves only these three flags change; values, images,
requests, claims, hooks, ownership and unrelated releases remain identical.
This prevents automatic last-failure rollback/uninstall and upgrade cleanup;
it does not undo completed changes, disable normal chart hook deletion policies,
make Flux choose a fresh install, or authorize another attempt. Review, release
and separately approved promotion are required before live use.

### Original guarded fresh-install design

The original approved approach used same-name native Helm `install --replace`
using the exact reviewed chart and privately resolved values while the root,
umbrella and child reconcilers are safely paused. No uninstall, Helm-history
Secret deletion, fabricated chart-info, disabled guard, take-ownership, force
conflict or controller-status edit belongs in this procedure. Real CLI tests on
a disposable synthetic API verify that Helm 4.2.4 (the controller's runtime) and
3.19.0 retain both failed records, allocate the next revision, run install hooks,
reject foreign ownership/deployed-name reuse, and retain history after failure.
These tests are not a real Kubernetes/SSA, migration or backup/restore rehearsal.

A bounded live read-only catalog transaction on 2026-11-05 verified the expected
application database/owner, only the four prerequisite extensions and public
schema, zero non-system relations/non-extension routines, and no migration
metadata. It used CNPG's existing local administrative socket, no password or
Secret-value retrieval, and ended with rollback. Repeat this check immediately
before recovery; it is not proof of backup restoration or absence of object-store
data. Any application relation/data, unknown owner or pending action stops recovery.

A separately reviewed recovery batch must include all of the following:

1. Verify exact cluster/release/chart, failed-only Helm history, empty application
   catalog, prepared Secret keys/custody, claim identities/health, existing resource
   ownership and Gitaly capacity. Resolve private values without printing them;
   no credential rotation or new persistent access. Independent backup/restore
   remains unverified and needs explicit risk acceptance or separate verification.
2. Capture original suspension states and use UID/version guards to pause root,
   umbrella, then child. Wait for in-flight actions to end and re-read all three;
   suspension does not cancel a running action. Stage only the separately reviewed
   source/policy release, retaining the app root. Pausing only the child allows its
   parent to overwrite the pause. Never edit owner annotations or controller status.
3. Execute one bounded native installation with existing installer authority,
   same release/target/storage namespace, normal hooks and no Namespace creation.
   Shared-secrets hooks can create missing app Secrets, label existing named
   Secrets and add missing keys; verify expected keys/targets first and preserve
   credential contents. Installation creates the real chart-info, workloads,
   migrations and a 10Gi Gitaly claim. Stop and preserve partial state on failure;
   deployment rollback does not reverse a database migration.
4. Verify chart-info and app/data health before child resume. Flux treats a native
   revision it did not observe as unmanaged and performs an upgrade to restore
   management. Approval must include that upgrade, its normal hook deletion/
   recreation and possible idempotent migrations; it is not a no-change adoption.
   Resume umbrella only after child readiness and matching source-owned policy;
   resume root last, restoring original suspension values and approved source.
5. Verify real HTTPS/local recovery, migrations, worker placement, preserved data
   and credential identities/history, controller reconciliation and cluster health.
   Any unexpected or uncertain result stops further mutation; no automatic broad
   cleanup or data rollback is authorized.

### Reset comparison and protected data

A data reset offers no demonstrated benefit: the application catalog is empty,
and no Gitaly claim exists. Valkey, CNPG/PostgreSQL and Garage are separate owned
resources in the same namespace, not disposable GitLab installation state. Their
four original claims remain Bound/healthy with Retain reclaim policy and two
running replicas across the storage workers. Existing credentials, CNPG Cluster,
Garage layout/key/buckets, Valkey contents and all four claims/PVs/replicas remain
outside either recovery method. Never delete the namespace or data foundation.
Retain is a safeguard, not permission to delete claims or proof of independent
backup. The configured Longhorn paths alone do not prove separate physical disks.

| Candidate | Release history | Controller actions and tradeoff |
|---|---|---|
| Native same-name install-replace | Retains failed revisions | One manual install, then Flux management upgrade/hooks; exact private values must be reproduced. Isolated CLI behavior is tested. |
| Helm-state-only reset | Permanently discards only the two failed GitLab Helm records | Could let Flux perform one normal managed install after explicit failure-counter reset; avoids manual values handoff but needs separate approval for exact record deletion and controller reset. Not yet live-tested. |
| Database/volume/namespace reset | Risks unrelated accepted data and credentials | No benefit shown; reject this scope for the present blocker. |

No reset is approved or implemented here. A metadata-only reset would still need
fresh identity/version guards, three-manager coordination, proof of failed-only
history, exact deletion targets, explicit acceptance of lost diagnostic history,
and a separately reviewed no-concurrent-action/reset sequence. It does not require
reinitializing PostgreSQL, Valkey or Garage. Both viable candidates share source
review/release and application startup/migration/image-pull waits; no wall-clock
saving is guaranteed. The current install-replace proposal remains the tested
history-preserving option until an alternative destructive scope is approved.

Source publication alone does not authorize live recovery/private input access.
The observed attempts above had separate approval; do not repeat a failed action
without inspecting its actual outcome or improvise a native command from this design.

## Versions and lab budget

The reviewed chain is Big Bang 3.35.1, GitLab package 10.4.2-bb.0 / GitLab19.4.2-ee
without a paid license, and separate runner package 0.91.2-bb.3 / Runner19.2.2.
The runner/server version difference needs real acceptance; no full feature
compatibility is inferred from rendering. Exact source archives are checksummed.
The tested hardened webservice image is pinned by its observed digest; other CNG
images were not run by the transport probe.

The prepared lab overlay constrains Gitaly to `storage.perkforge.io/worker=true`,
matching the already accepted PostgreSQL/Garage/Valkey consumer-node contract.
The Longhorn CSI driver must be registered on each eligible node. Gitaly's one
10Gi claim, image and resources are unchanged. The pinned chart changes its two
shared-secret hook Job names when the full-values hash changes; no credential
payload or extra resource is introduced. This source correction is not activated.

The lab overlay sets webservice, shell and Sidekiq HPA minima/maxima to one,
preserving vendor container requests/limits. Registry, KAS, Zoekt, AI gateway,
embedded OpenBao, bundled runner, monitoring stacks, ingress controllers and
cert-manager stay disabled. Migrations, Toolbox, Gitaly, Rails/Workhorse and
Sidekiq remain required. This is deliberately not service HA or production sizing.

Read-only snapshot at 2026-11-03 18:34 UTC: allocatable 18 CPU/45.60Gi across three
nodes, each 6 CPU/15.20Gi. Existing requests were 6.925 CPU/7.49Gi; actual use
approximately 0.769 CPU/9.12Gi. The vendor HPA floor was roughly 16.78Gi versus
11.83Gi for the one-replica app overlay; migrations add about 1.40Gi and a
possible Deployment surge about 7.74Gi. These are not measured runtime peaks.

Fresh requested-capacity check on 2026-11-04: the three nodes have about
9.225 CPU/34.49Gi unrequested in total. Control-1 has no Longhorn CSI driver;
only the two labeled workers can satisfy the new Gitaly constraint. Pinned app
render steady requests are about 5.1 CPU/11.83Gi; Gitaly accounts for .4 CPU/.586Gi.
Worker requested headroom was 2.28 CPU/10.74Gi and 3.03 CPU/12.20Gi, so either fits
Gitaly at that snapshot. The new claim schedules 20Gi across two Longhorn replicas.
Migrations and shared-secret hooks, node placement and Deployment surges require
fresh checks before activation; aggregate free requests are not runtime peak or
HA proof. No app resources were deployed to establish these rendered numbers.

Data planning requests approximately 1.85 CPU/3.625Gi: PostgreSQL 1 CPU/2Gi,
Valkey .25 CPU/.5Gi, Garage .5 CPU/1Gi and operator .1 CPU/.125Gi. Round the
reservation to 2 CPU/4Gi and allow 8Gi peak. Existing workloads plus app/data,
runner manager and one job are about 23.7Gi/14.6 CPU requested before migrations,
backup and surge. Per-node placement can fail before total capacity does.
Fresh metrics, admission requests/limits and rollout headroom are mandatory.

Data claims total 51Gi plus 10Gi Gitaly, or 61Gi logical/122Gi scheduled for two
Longhorn replicas. This is scheduled capacity, not physical occupancy. Replicas
are not independent backups and single-instance data services are not HA.

## Shared CloudNativePG and providers

Valkey's persistent pod requires `storage.perkforge.io/worker=true`. Every
eligible node must have the Longhorn CSI driver registered; disk-replica
placement alone does not make another node capable of mounting a volume.
The one-writer Deployment uses Recreate, preserving the named 2Gi claim and
Secrets without a rolling surge. Its post-renderer explicitly nulls rollingUpdate
so the API-defaulted old strategy fields cannot invalidate the transition.
Brief downtime on a later rollout is deliberate.

Observed recovery required a separately approved, UID/version/old-strategy
guarded JSON PATCH to Recreate: real Helm SSA rejected the API-defaulted old
rollingUpdate fields even with an explicit null, unlike the earlier strategic
dry-run. The one-time migration changed only strategy, then Helm applied the
worker selector. After the old Pending consumer disappeared, only the still
unbound claim's stale selected-node annotation was guarded-removed. No claim or
Secret was deleted/recreated. A bounded retry after binding cleared the earlier
stalled health result; root and eight releases became Ready. Do not repeat this
historical recovery automatically on a healthy or bound/data-bearing claim.

The accepted data stage used reviewed worker-placement and DNS prerequisites.
Both PostgreSQL `affinity.nodeSelector` and Garage Pod
`nodeSelector` require the same prepared-worker label. The existing ingress
policies remain identical. The two reviewed GitLab DNS records were added through
the [bounded existing-service maintenance procedure](../../../../infrastructure/ansible/DNS-MAINTENANCE.md),
not the first-install playbook. The two approved HTTPS leafs were signed locally;
no signing-key copy, host trust change or new Registry1 custody is implied.
PostgreSQL uses its own operator-managed CA; follow
[public CA delivery and client rotation](postgres-ca-lifecycle.md), never assume
the lab ingress CA validates that database. Future credentials, live maintenance, source promotion or recovery tests still
need action approval; do not repeat completed first-layout operations.

The live root has pruning disabled. Selecting a prior path therefore leaves
new stores/routes running; it is not a rollback. Separately review containment
(such as CNPG hibernation and Garage scaling after removing their desired stage)
while preserving all Clusters/PVCs/Secrets. Never uninstall the shared operator,
delete a Cluster or assume an image rollback restores database state.

Corey explicitly chose CloudNativePG as the platform database foundation. The
pinned chart0.29.1/operator1.30.1 is shared, deployed in `cnpg-system`, initially
watching only `gitlab`. Public config and post-rendered Deployment agree on that
watch scope. A mirrored namespace Role and exact operator ServiceAccount binding
supply database permissions; common database Secret permissions are not granted
cluster-wide. Future namespaces need reviewed Roles/bindings and watch-list edits.

Eleven global CRDs, fixed-name admission webhooks, node discovery and webhook
patches remain real privileges. Built-in user-role aggregation is off.
`../cloudnative-pg/authority-review.yaml` records the pinned rendering, and
`prerequisites.yaml` authors the separate owner-admin installer delegation. Named
bind/escalate is privileged and Kubernetes cannot restrict create by name. These privileges were separately approved for the accepted foundation/provider
stages; no new authority is added by the Gitaly placement correction. Reject
existing foreign CRDs, webhooks,
operator or Helm ownership; do not silently adopt the spike. The chart emits CRDs as templates: crds.create=false explicitly removes them
from the operator release, and its installer has no CRD mutation authority. The
owner-admin foundation checksums the pinned chart, renders it in fresh private
scratch, and creates missing owned schemas only. Existing foreign or changed
schemas refuse; upgrades require an explicit procedure. Disabling GitLab must not uninstall the
shared operator or remove databases.

PostgreSQL17.11 is one dedicated CNPG instance, 16Gi Longhorn, no application
superuser, required GitLab extensions and rejection of non-TLS network clients.
Valkey7.2.15 (chart0.12.1, explicitly overriding its newer default image) uses
standalone ACL authentication, TLS, AOF, noeviction and retained 2Gi storage.
Garage2.2.0 is a standalone namespace-only StatefulSet, retained 1Gi metadata and
32Gi object data, no Kubernetes discovery/RBAC or service-account token. Its RPC
and admin APIs bind loopback; only S3 is a Service. S3 client connections use
HTTPS at Traefik; the isolated Traefik-to-Garage3900 backend hop is plaintext,
not end-to-end TLS. NetworkPolicy/CNI acceptance remains essential. All image candidates are
pinned. The vendor disposable development setup scripts are not used.

The data stage denies all ingress into the dedicated GitLab namespace by default.
Trusted same-namespace app/data traffic is allowed, excluding Garage: S3 stays
Traefik-only. Traefik gets Workhorse8181 and Garage3900 through exact pod peers;
the shared operator gets only its PostgreSQL5432/status8000 targets. Tenant and
runner namespaces receive no direct database/Gitaly/Valkey path. This is an
application-namespace trust boundary, not isolation between its own co-resident
services. CNI enforcement, node-origin probes and denied tenant connectivity must
be verified live before acceptance. See the [operator networking requirements](https://cloudnative-pg.github.io/docs/1.27/networking/).

## Transport and protected delivery

PostgreSQL's optional chart mTLS helper hardcodes verify-ca. The reviewed overlay
leaves that helper off, supplies supported extraEnv PGSSLMODE=verify-full and
PGSSLROOTCERT, and mounts only a public CA ConfigMap into webservice, Sidekiq,
migrations and Toolbox. Rendered generated configuration must not override it.
Native libpq and exact webservice CNG ActiveRecord/PG probes passed matching
CA/hostname and wrong-host, wrong/missing-CA and plaintext rejection cases. An
explicit verify-ca control demonstrated why the helper must remain off. The
CNG probe used a disposable read-only, network-isolated container and fake local
TLS protocol endpoint, not a real database or full application startup.

The one authorized Registry1 pull used an anonymous in-memory auth descriptor;
no saved registry login, credential output or cluster pull Secret was created.
Actual workload image-pull credential delivery is a separate live scope.
Default-off `prepare-registry.yaml` and exact registry-gitlab/manager/job delivery
profiles prepare/create private-registry Secrets in gitlab, gitlab-runner and
gitlab-ci-platform only. This is persistent credential custody and needs explicit
approval beyond the prior one-time pull; no real input was read or copied during
source preparation. The trusted manager can read its job-namespace Secrets by
design; jobs have no API token or Secret-read role. These copies are not an
agent unlock and do not rotate or create Registry1 access.

Ansible assembles existing owner-held credentials; it generates none here.
`prepare-foundation.yaml` covers root recovery/Garage RPC/admin inputs;
`prepare-credentials.yaml` has two independent stages: `application` writes
`application-credentials.json` for DB/Valkey/OIDC before GitLab exists; `runner`
writes `runner-credentials.json` only after native registration returns its token.
Each has a matching exact delivery profile/scope. The early stage never reads a
runner token, avoiding a first-install dependency cycle.
`prepare-object-credentials.yaml` covers existing S3 key formats.
`prepare-transport.yaml` checks a reviewed CA SHA256, constraints, server purpose,
exact hostname, one-day validity and key match before making a private leaf
manifest. It accepts directly CA-signed leaves; no intermediate-chain, issuance,
renewal or trust-store modification is implied.

Dedicated delivery profiles permit only exact names/types/keys, after canonical
owner0600 input, owner0700 output, context/API/cluster UID, labels and existing
object checks. Secrets are immutable and create-only; all existing targets are
checked before creates. Partial creation can resume; foreign/differing targets
refuse, never patch/adopt/rotate. Public CA delivery never distributes signing
keys. Its explicit runner stage creates the immutable Opaque
`gitlab-runner-public-ca` Secret in `gitlab-runner`, keyed by the reviewed GitLab
hostname plus `.crt`, without a port. This matches the chart’s required mount and
[Runner custom-certificate convention](https://docs.gitlab.com/runner/install/kubernetes_helm_chart_configuration/#access-gitlab-with-a-custom-certificate). Default/check modes contact no API. Protected variables stay under no_log;
Python only verifies state or models independent test fixtures.

## Garage initialization and uncertainty

After approved provider readiness, the owner establishes a loopback-only
Kubernetes port-forward to Garage admin3903. `reconcile-garage.yaml` creates no
forward and exposes no public admin endpoint. It requires explicit scope,
reviewed full node ID, existing private admin/application key files, owner0700
state directory and a separate first-layout approval flag. Proxies/redirects are
disabled and credentials never enter command arguments or output.

The only first layout is version0→1, one reviewed healthy2.2.0 node, zone
`gitlab-local`, tag `perkforge-gitlab-data-v1`, 28Gi within the 32Gi PVC with
operational headroom. It stages, previews the exact resulting role, applies and
reads back. Existing layout resizing, foreign staging, invalid capacity/version
and wrong-node states refuse. It imports only the supplied dedicated key, creates
LFS/artifacts/uploads/packages and backup/restore staging buckets, and grants
read/write without owner/create-bucket rights. It refuses unreceipted existing
keys/buckets or expanded permissions.

Each mutation is preceded by a private pending intent and followed by native GET
verification. A lost response leaves durable pending and blocks retries before
API writes. The owner must inspect actual state and explicitly recover the
receipt; uncertain creates are never auto-adopted. A local exclusive lock prevents
competing runs; stale locks are not automatically removed. No deletion, key
rotation, destructive rollback or independent-backup claim exists. Actual Ansible
fixtures cover complete bootstrap, zero-write repeat and uncertain-create refusal.
Those fixtures are not real Garage/S3/persistence acceptance.

## Keycloak and native GitLab authority

Use a dedicated confidential GitLab client with exact callback, stable sub,
authorization-code/S256, canonical scope/mapper validation and no app/realm role
mapping. Prepare it disabled; activate only after app/native/recovery gates.
The adapter ends only its own verifier refresh-token session. It never signs in
as Corey, approves a GitLab account or grants instance administration.

Free OmniAuth login blocks auto-created accounts and disables automatic email
linking. Owner-local approval and stable provider/subject linking are required;
never assume paid required-group admission, group sync or group-derived admin.
The merged role matrix governs explicit instance-admin and native tenant roles.
Native-ready means migrations/local recovery work before enabling the client,
not that an OIDC-created account already exists. First named OIDC enrollment
creates a blocked account; an independent native admin must verify its exact
provider/subject, approve it and assign reviewed authority before the next login.
Realm MFA readiness precedes client activation; fresh app login acceptance follows.
A blocked new user is not completed enrollment. An approved platform admin needs
an explicit native instance-admin grant; logging in with a Keycloak group is not
proof of that grant.

`reconcile-membership.yaml` scopes one reviewed nonadmin UID/provider/subject to
one exact private tenant group, only the approved direct native role. It rejects
foreign/higher/inherited/pending/expiring state; revoke uses skip_subresources to
preserve descendants. Inherited access after direct removal fails acceptance.
This is not whole-person offboarding: sessions, PATs, deploy/project tokens,
runner/machine credentials and unrelated memberships require separate reviewed
revocation. Keep independent GitLab local recovery outside the SSO dependency.

## Runner boundary

Use modern POST/user/runners project registration, not a legacy shared token.
The exact reviewed private platform project/default protected branch, actor ID,
no-force-push rule, protected tag and native runner fields are checked. Create
paused/locked/ref_protected/run_untagged=false with concurrency one and timeout300.
No receipt plus an existing matching runner refuses adoption. Write creation
intent before POST, store one-time glrt token privately, and never retry uncertain
creation blindly or reset/rotate it. Activation needs separately verified manager
readiness. Pause does not cancel jobs or revoke credentials; active jobs prevent
a false drained result. Rollback must separately verify job/pod cleanup.

The manager uses its own namespace and API identity. Jobs use restricted PSA,
nonroot/dropALL/RuntimeDefault, no API token, no privilege/host/PVC mounts, no
namespace/service-account/label/annotation/bearer override and an exact allowed
image/helper pair. One protected trusted platform project is not a tenant or
untrusted MR runner. Manager and job resource budgets are separate.

Job default-deny plus DNS is in foundation; `prepare-runner-network.yaml` prepares
endpoint policies from explicit reviewed host /32 or /128 addresses and actual
Traefik target/API ports. Only the manager gets API egress. Shared ingress targets
also serve other HTTPS virtual hosts: L3/L4 policy is not a hostname allowlist.
Application authorization remains essential. No unrestricted Internet allowance
is generated. Node/kubelet image pulls are outside job egress. Exact DNS,
pre/post-DNAT behavior and CNI enforcement still require live allow/deny tests.

## Dormant activation sequence

All stages come from one reviewed, published immutable release. Generic route
skeletons and certificate preparation have no home-domain default; local hosts
and public runtime inputs live under the selected cluster roots and
`local-gitlab-review/environment.example.yaml`. Credentials and physical endpoint
addresses remain owner-local inputs. Images are not rebuilt for an environment. Directory presence
and successful rendering are not approval to select a source.

1. **Inspect:** verify release/tag/commit, context/API/kube-system UID, current
   resources/ownership, capacity, image access, DNS/CA/leaf SANs, independent
   recovery, backup plan and per-stage diff. Reject foreign CNPG ownership.
2. **Foundation:** separately approve the default-off
   `configuration/ansible/gitlab-prerequisites.yaml` owner-admin batch. Its
   published/clean-release, context/API/cluster checks precede pinned create-only
   CRDs, namespace/installer/runtime delegation, quotas and default-deny policies.
   A private owner0700 artifact cache is required. Every existing target is
   compared before creates; foreign or broadened RBAC/schema state refuses and
   no patch/adoption is attempted. Separately approve protected input
   creation/delivery, public trust and exact endpoint policies. No passwords in chat or inline variables. No signing key in pods.
3. **`local-gitlab-providers`:** select only shared CNPG and Valkey; app/runner
   remain off. Wait for operator/webhook/CRDs and Valkey health before proceeding.
4. **`local-gitlab-data`:** add CNPG Cluster, Garage and HTTPS-only local routes.
   Establish PostgreSQL/Valkey trust, initialize Garage with the bounded adapter,
   verify actual DB/TLS/S3 access and persistent restart behavior. A web route can
   have no backend until the app stage; do not mistake that for app readiness.
5. **`local-gitlab-app`:** enable the one-replica GitLab overlay, preserving the
   existing unrelated packages. Verify migrations and local recovery first; then
   separately activate the prepared Keycloak client, approve/link the named
   account and assign only reviewed native authority. Test fresh MFA and denial.
6. **`local-gitlab-runner`:** only after explicit private-project/registration and
   manager/egress/pull-credential prerequisites. Prepare/deliver the separate
   runner credential manifest from the registration-issued token and deliver
   the runner public CA before selecting its stage. Verify one protected clone/artifact
   job plus denied untagged/unprotected/wrong-namespace/image and tenant cases.

The ordinary/review roots stay disabled. Roll back in reverse: pause/drain runner,
disable only owned GitLab OIDC client/native grants, select the prior reviewed app
stage. Preserve all database/Gitaly/Garage PVCs, Rails secrets and shared operator;
never uninstall the data foundation or delete CNPG Cluster as an SSO rollback.
GitOps data-writer permission deliberately omits destructive data pruning; cleanup
is a separate approved retention operation. Database schema changes may make an
older GitLab image unsafe: do not assume Helm rollback is database rollback.

## Backup and independent restore

Corey selected a nominal128GB encrypted external drive, about119.2Gi before
filesystem/encryption/other files. No device access, inspection, mount, unlock or
write is authorized/performed. The future workflow requires the exact verified
mount/device, owner-local unlock, connection/awake availability and a fail-closed
space check; never fall back to the workstation root filesystem.

Two retained generations plus one incoming generation and20% free space imply
roughly31.8Gi per equal generation before other use. A61Gi occupied dataset would
not fit even two full copies. Measure real occupied/archive size; do not assume
compression/deduplication. Garage backup/restore staging is in-cluster and not an
independent backup. Toolbox cron stays disabled. Preserve database, repositories,
objects and exact Rails/config/recovery secrets, encrypted in independent custody.
Do not prune the last verified generation before its replacement is verified.
Retention/capacity changes need approval. A separately approved isolated restore
must preserve the source drive and not overwrite the live instance, enable public
routing or send outgoing integration traffic. Actual backup/restore is unverified.

## Coordinated acceptance

GitLab is complete only when app, SSO, native access and runner work together:
actual provider/persistence/TLS, local recovery, named fresh MFA login, correct
native admin/tenant roles and denied cross-tenant/ungranted access; protected
clone/artifact success with negative runner tests; safe pause/drain, credential
custody and scoped rollback; repeat with no unintended changes; health/resources;
independent backup/restore and documented remaining limitations. Temporary users,
tokens, jobs or restore targets need a separately approved bounded batch and
verified cleanup. The owner closes tickets.

Offline tests are synthetic proof of validation/transactions, not vendor support
certification or live browser/startup/backup evidence. Tests are discovered by the
existing full platform CI residual shard; new package/shared paths conservatively
select full coverage. The optional CNG probe never pulls/authenticates by default.
