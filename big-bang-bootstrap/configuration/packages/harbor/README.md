# Harbor: one release, staged activation

This source combines dedicated PostgreSQL, Valkey, Harbor and Keycloak OIDC.
**Publication does not deploy it.** Existing roots are unchanged; only the new
`local-harbor-data` and `local-harbor-app` roots select these additions. Keep CI
workflows disabled while maintaining and running local checks.

## Scope

- Big Bang 3.35.1, Harbor package 1.19.2-bb.3 / native 2.15.2; dedicated CNPG
  PostgreSQL 17.11 and Valkey 7.2.15 using the existing reviewed operator/chart pins.
- Separate Harbor namespace, data, credentials and PVCs. No reuse or resizing of
  GitLab/Nextcloud stores, no new operator, no shared application secret access.
- Existing accepted root is inherited. The only existing operator change adds
  `harbor` after `gitlab,tenant-home-nextcloud`; do not replace a newer watch list.
- Five app containers request 500m CPU / 1280Mi. Data requests 350m / 768Mi.
  Total: **850m / 2048Mi**, plus runtime/init peaks and future workload growth.
- Registry 10Gi, job logs 1Gi, PostgreSQL 8Gi, Valkey 2Gi. Two-replica Longhorn
  scheduling adds **42Gi**: 40Gi dedicated disks, 2Gi root disks. Snapshot, backup,
  restore and growth headroom are additional. This is not a capacity acceptance.
- Scanner/exporter, robots, CI publishing, tenant project synchronization and
  offboarding remain outside this pilot. No scanned-image or HA claim.

## Transport and authority

- External HTTPS origin: `https://harbor.perkforge.home.arpa`.
- Native Traefik Ingress replaces the bundled nginx path that disables backend
  certificate verification. Core/portal use HTTPS and namespace-local
  ServersTransport objects with exact server names and `harbor-internal-ca`.
- All internal components use dedicated TLS Secrets. A final narrow post-renderer
  corrects Big Bang's inherited registry Service port 5000 to TLS port 5443.
- PostgreSQL uses `verify-full`, explicit core
  `PGSSLROOTCERT=/harbor_cust_cert/custom-ca.crt`, and a 50-open/10-idle pool.
  Valkey requires TLS plus a dedicated password, with indexes 0/1/2.
- NetworkPolicy denies ingress by default, admitting only Traefik, the exact
  Harbor consumers and existing CNPG operator. **Egress is not restricted.**
  Exact endpoint/CNI-reviewed egress is separate work; do not describe this as
  complete network isolation. Host-local/CNI behavior still needs live tests.
- The create-only foundation has 13 objects: Harbor namespace; two installer
  ServiceAccounts in `bigbang`; five namespace Roles and five bindings. No new
  ClusterRole, bind/escalate permission or shared `bigbang` Secret-history grant.
  CNPG's existing namespace authority includes workload/Secret management and
  Pod exec; adding Harbor is an explicit access expansion.

## One-MR rollout order

Use one reviewed MR and one immutable published release containing all source.
The data and app checkpoints are two selections of that same release, not two MRs.
Do not replay cluster bootstrap or manually override a child against Git values.

1. **Preflight and preservation.** Verify the clean release checkout and immutable
   tag/commit. Recheck all nodes/releases, per-worker requested capacity, Longhorn
   replicas/free space and current watches. Capture pre-Harbor preservation
   evidence with `scripts/harbor-stage-audit.py --verify --mode snapshot`.
2. **Foundation and protected inputs.** Obtain the action-time approvals below.
   Run default-off `configuration/ansible/harbor-prerequisites.yaml` against the
   exact API/context/cluster/operator identities. It checks every target first,
   creates only missing owned objects, stops/readbacks per object and refuses
   adoption, rotation or patching. Prepare and deliver only the data profile.
3. **Data root.** Conditionally select the published tag and
   `./big-bang-bootstrap/clusters/local-harbor-data` through the existing owner
   promotion procedure. Verify exact source artifact/root revision and run the
   read-only audit in `data` mode. Test correct password/CA/hostname and rejection
   of wrong password, wrong CA, wrong hostname, plaintext and other namespaces.
   Run one explicitly approved bounded persistence test. Preserve existing PVCs.
4. **Application inputs.** Export only the new CNPG server CA's `ca.crt`, after
   checking its owning Cluster UID and `status.certificates.serverCASecret`.
   Never export `ca.key`. Build the public CA bundle with internal and existing
   issuer/lab roots. Deliver the separate app profile, internal/service TLS and
   dedicated registry pull input. Preserve all credentials for recovery.
5. **App root.** Select `./big-bang-bootstrap/clusters/local-harbor-app` at the same
   release. Verify exact artifact/revision, all deployments/PVCs, installed
   Traefik CRD schema and actual Service/transport references with the `app`
   audit. Test public HTTPS, native TLS and independent built-in `admin` login.
   Ready is not proof of transport, authentication, data integrity or performance.
6. **Private project boundary.** Harbor's pinned initial SQL seeds project 1,
   `library`, as **public**. Keep it empty. After checking its exact identity and
   zero artifacts, obtain approval to make only that project's visibility private,
   preserving its ID and all other metadata. Read it back. Do not push real data
   before anonymous/unassigned private-project denial passes; SSO cannot fix this.
7. **SSO.** Follow the [dedicated client and native adapter](../../authorization/sso/harbor/README.md):
   create the exact disabled client, configure native OIDC before any non-admin
   local account, grant its one admin role only to the existing exact
   `/platform/admins` group, then enable after separate approval/readback. Verify
   fresh MFA login/logout, named admin, independent local admin recovery, non-admin
   system-admin denial and unassigned private-project push/pull denial.
8. **Acceptance.** Approve a disposable private-project image push/pull and
   persistence test; retain evidence/data until cleanup is approved. Check unchanged
   existing releases/databases/PVCs after every stage. Do not onboard production
   data until consistent database + registry + credential backup and isolated
   restore are demonstrated. Velero design alone is not that evidence.

## Required action-time approval bundle

Confirm the exact target/release/root and the following consequences before running
any corresponding operation. Approval flags in source are guards, not permission.

- The 13 foundation objects, CNPG Harbor namespace access/watch and dedicated
  data/app resource/storage proposal. Existing apps stay unchanged.
- Local protected credential/key generation, existing-CA leaf signing and the
  explicit Harbor-only Secret delivery, including the registry credential copy.
  CA signing keys stay local. No password/token appears in chat, argv or Git.
- The two conditional GitOps selections and their new workloads, HTTPS route and
  namespace-only policies/transport grants. Scanner is off and egress unrestricted.
- Exact empty default `library` project public-to-private change before data use.
- Dedicated confidential Keycloak client/secret, the admin-group role grant for
  **current and future** `/platform/admins` members, native Harbor OIDC settings
  and client enablement. No other realm groups, users, clients or roles change.
- Separately bounded live data/push-pull/persistence/restore tests and later cleanup.

OIDC group filtering limits imported groups, not who can sign in. Manual onboarding
is not login denial. Unmapped realm users may reach onboarding but receive no
system-admin/private-project permission from this source. Harbor's configuration
GET omits the client secret, so public readback cannot prove secret equality;
only a successful real token exchange establishes that acceptance.

## Checks and failure handling

- `test_harbor_review.py`, `test_harbor_data.py`, `test_harbor_activation.py` render
  pinned charts, apply every Flux post-renderer and compare existing resources.
- `test_harbor_foundation.py` runs real Ansible against isolated CLI fixtures,
  including wrong target/ownership, zero-change repeat and partial/uncertain writes.
- Native/client SSO tests run real Ansible against disposable HTTPS services.
- `test_harbor_stage.py` checks read-only exact-release, runtime-schema, readiness
  and UID/spec-preservation refusals. The audit reads no Kubernetes Secrets,
  performs no exec, and never declares TLS/login/push-pull/restore acceptance.
- No offline pass substitutes for physical TLS/CNI, image pull, browser/MFA,
  migrations, load, persistence or restore tests. CI skipping is not a pass.

For the audit, supply canonical owner-only 0600 kubeconfig/evidence files in owned
0700 directories, exact `--context`, `--expected-api`, `--expected-cluster-uid`,
`--baseline`; data/app modes also require `--expected-namespace-uid`, `--release`
and `--commit`. Snapshot creates a new evidence file and never overwrites it.
Without `--verify`, it reads no files and contacts no APIs.

Stop on any mismatch. Inspect uncertain outcomes before retrying. Preserve created
objects and UIDs; do not delete/recreate, rotate credentials, reset failed releases
or roll back database migrations automatically. To contain SSO, the guarded client
`disable` operation stops new logins but does not revoke issued Harbor sessions,
CLI secrets or robots. Never blindly switch back to database auth. Suspend only
an explicitly approved exact reconciler/release if needed; suspension leaves data
and workloads intact. Returning to the old prune-false root does not uninstall
Harbor or remove the new operator watch.

[Data/foundation details](data-services/README.md) ·
[Native OIDC contract](../../authorization/sso/harbor/NATIVE.md) ·
[Harbor 2.15.2 default project](https://github.com/goharbor/harbor/blob/v2.15.2/make/migrations/postgresql/0001_initial_schema.up.sql) ·
[Harbor pgx configuration](https://github.com/goharbor/harbor/blob/v2.15.2/src/common/dao/pgsql.go)
