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
- All Harbor application and data Pods require `storage.perkforge.io/worker=true`;
  init containers share their Pod's placement. Core/portal add 200m CPU / 512Mi
  to worker requests when moving off the control plane. Before acceptance, check
  the label exists only on workers and every Harbor Pod is on one of those nodes.
  The four application Deployments also require absence of both control-plane
  and master role labels, with no control-plane tolerations. Existing database/cache
  selectors and accepted data specs remain unchanged; their worker-only guarantee
  depends on correct node labels. The acceptance audit rejects worker-labelled
  control-plane nodes and misplaced Pods. It cannot prevent an administrator from
  later changing labels or scheduling policies.
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
- Iron Bank core/jobservice startup appends internal/custom CAs to the UBI trust
  bundle. Each uses its own same-digest, non-root init to copy existing image roots
  into a 4Mi `emptyDir`; only `/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem`
  is overlaid for the unchanged entrypoint. The init refuses a missing, empty or
  differently resolved bundle. UID 10000, existing application requests and all
  security restrictions remain unchanged; the init requests 20m/32Mi, below the
  application's requests. Secret inputs stay read-only. No root init, capability,
  broad filesystem permission change or TLS-verification bypass is used.
- PostgreSQL uses `verify-full` and explicit core/jobservice
  `PGSSLROOTCERT=/harbor_cust_cert/custom-ca.crt`. Each process has a
  20-open/5-idle pool: 40 open/10 idle with one replica each, leaving room within
  the dedicated database's 100 connections. Reassess before scaling or load growth.
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

### Native jobservice database dependency

Harbor 2.15.2 jobservice directly connects to PostgreSQL during startup, before
starting its Redis worker pool. The immutable source chain is
[main/job context](https://github.com/goharbor/harbor/blob/a97e7b835d1364e2cc11fd706a15171a5c9d5d77/src/jobservice/job/impl/context.go#L67-L105)
→ [configuration mapping](https://github.com/goharbor/harbor/blob/a97e7b835d1364e2cc11fd706a15171a5c9d5d77/src/pkg/config/manager.go#L159-L176)
→ [DAO/pgx registration](https://github.com/goharbor/harbor/blob/a97e7b835d1364e2cc11fd706a15171a5c9d5d77/src/common/dao/pgsql.go#L81-L110).
The [REST manager](https://github.com/goharbor/harbor/blob/a97e7b835d1364e2cc11fd706a15171a5c9d5d77/src/pkg/config/rest/manager.go#L28-L54)
uses existing `JOBSERVICE_SECRET` and core's HTTPS `/api/v2.0/internalconfig`
to obtain the dedicated DB configuration, including credentials, `verify-full`
and pool limits. Do not add a separate DB Secret mount, role or credential copy.

The retained `harbor-postgres-from-core` policy identity now admits exact core
and jobservice Pods in `harbor` to only TCP 5432. Its operator rule is unchanged.
Existing policies already cover core/registry TLS and Valkey 6379; no other
ingress or egress expansion is needed by this startup path.

The build revision above is the parent of release-tag commit
`080b0220574cc853ae1e2946ce7a5610ba855757`; only `.buildbaselog` differs.
Both pin [pgx v5.10.0](https://github.com/goharbor/harbor/blob/a97e7b835d1364e2cc11fd706a15171a5c9d5d77/src/go.mod#L89),
whose [TLS configuration](https://github.com/jackc/pgx/blob/7293fb11125be0373a92f716683f2d494f6fd4b0/pgconn/config.go#L776-L963)
honors `PGSSLROOTCERT`. Explicit selection uses the already mounted approved
public bundle instead of depending on ambient system roots. These are source
contracts, not proof of image contents or live DB/TLS/CNI acceptance.

## One-MR rollout order

Use one reviewed MR and one immutable published release containing all source.
The data and app checkpoints are two selections of that same release, not two MRs.
Do not replay cluster bootstrap or manually override a child against Git values.

1. **Preflight and preservation.** Verify the clean release checkout and immutable
   tag/commit. Recheck all nodes/releases, per-worker requested capacity, Longhorn
   replicas/free space and current watches. Capture pre-Harbor preservation
   evidence with `scripts/harbor-stage-audit.py --verify --mode snapshot`.
   The [record-only DNS procedure](../../../../infrastructure/ansible/DNS-MAINTENANCE.md)
   adds only `harbor.perkforge.home.arpa` with `harbor-dns-record-v1`, preserving
   all eight prior names. Its source belongs in this review, but the DNS write and
   one service restart require separate network-change approval and the operator's
   hidden sudo prompt. Keep it default-off until the release/base hash is reviewed.
2. **Foundation and protected inputs.** Obtain the action-time approvals below.
   Run default-off `configuration/ansible/harbor-prerequisites.yaml` against the
   exact API/context/cluster/operator identities. It checks every target first,
   creates only missing owned objects, stops/readbacks per object and refuses
   adoption, rotation or patching. Prepare and deliver only the data profile.
3. **Data root.** Conditionally select the published tag and
   `./big-bang-bootstrap/clusters/local-harbor-data` through the existing owner
   promotion procedure. Verify exact source artifact/root revision and run the
   read-only audit in `data` mode and preserve its separate data checkpoint. Test correct password/CA/hostname and rejection
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

## Protected-input procedure

Run with Ansible, OpenSSL, Python `PyYAML`, `cryptography>=43` and `bcrypt` available.
Use an owned 0700 private directory outside Git and world-writable ancestors;
all supplied input/output files are canonical, single-link, owned 0600 files.
Password inputs contain the exact value with **no trailing newline**.

- `prepare-transport.yaml`: explicit `harbor_transport_run=true` and
  `harbor_transport_scope=harbor-internal-transport-issuance-v1`; supply
  `harbor_transport_output_parent`. Creates a fresh dedicated internal CA and
  five exact service leaf identities. Deliver only `delivery/internal/` after
  the bundle has `READY`. `signer/ca.key` stays local and is never an input to
  Secret assembly. This is fresh issuance, not an implicit renewal/rotation.
- `prepare-public-certificate.yaml`: explicit `harbor_public_certificate_run=true`,
  scope `harbor-public-leaf-issuance-v1`, existing CA/output private directories
  and exact SHA256 fingerprint. Existing `root-ca.key.pem` must remain encrypted
  PKCS8; unlock only through the local hidden prompt. Only
  `harbor.perkforge.home.arpa` is issued. Deliver only `delivery/external/`
  after `READY`; partial failed bundles are retained privately, never reused.
- `prepare-credentials.yaml`: set profile `data` or `application`,
  `harbor_credentials_run=true`, matching scope
  `harbor-<profile>-private-assembly-v1`, `harbor_private_root`,
  `harbor_credentials_manifest`, exact `harbor_expected_namespace_uid`, and
  `harbor_credentials_inputs` mapping Secret name → key → protected input path.
  The [exact contracts](tasks/contracts.yaml) contain four data and 16 app Secrets.
  This assembles existing values; it does not generate passwords/token signing
  material, fetch registry credentials or read the cluster. Arrange those exact
  protected inputs under the separately approved local custody procedure.
  Encryption `secretKey` is exactly 16 ASCII bytes; `CSRF_KEY` exactly 32.
  Initial admin is 16–128 ASCII bytes with lowercase/uppercase/digit; Valkey is
  24–128 URL-safe alphanumeric/underscore/hyphen characters. The registry bcrypt
  entry must match its password for `harbor_registry_user`; token signing uses
  a matching RSA key/certificate with digital-signature usage.
- App assembly also pins the deduplicated public trust bundle with
  `harbor_public_ca_sha256` and the separately approved
  `harbor_database_ca_sha256`, `harbor_valkey_ca_sha256`,
  `harbor_identity_ca_sha256`. Values are lowercase SHA256 DER fingerprints,
  not the colon-form OpenSSL fingerprint string used for external leaf issuance.
  Include the internal root; CNPG's public CA is available only after data startup.
- `deliver-credentials.yaml`: use the same profile/manifest/pins, exact
  `harbor_delivery_scope=harbor-<profile>-credential-delivery-v1`, explicit
  `harbor_delivery_run=true`, protected `harbor_kubeconfig`, canonical
  `harbor_kubectl`, `harbor_context`, expected API/cluster/namespace UIDs. It
  preflights all targets, dry-runs missing objects, then creates/readbacks one at
  a time. Existing immutable identical Secrets are reused; any foreign/changed
  object is refused before writes. No adoption, overwrite or automatic rotation.

Preserve the private manifest and original inputs for a zero-change repeat and
recovery. Public CA/leaf expiry and later renewal need an explicit reviewed
rotation plan because delivered inputs are immutable; no renewal automation is
claimed. Never put private manifests, rendered credential-bearing configuration,
key material or real operator variables in source, logs or chat.

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
- Harbor-only DNS maintenance and one DNS-service restart, separately approved
  against the reviewed existing configuration checksum; no client resolver changes.
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
- `test_harbor_pgx_tls.py` uses pinned native pgx 5.10.0 with synthetic roots and
  in-memory TLS, checking matching CA/hostname, wrong CA/hostname, invalid/missing
  roots and no plaintext fallback. See the [fixture instructions](../../../tests/fixtures/README.md).
  This does not start Harbor or PostgreSQL and is not database-auth acceptance.
- `test_harbor_image_startup.py` checks immutable Iron Bank 2.15.2 source hashes
  and runs its unchanged startup scripts as UID 10000/GID 1000 in rootless,
  network-isolated bubblewrap with synthetic certificates and sentinel binaries.
  It reproduces the unwritable-bundle failure, proves preserved/added roots and
  rejects wrong trust paths. A missing bubblewrap is reported as skipped, not a
  pass. This is not an image or Harbor-binary integration test. Before promotion,
  verify the selected image digests' actual trust-file layout and permissions;
  matching source version alone does not prove those image contents. The init
  guard remains fail-closed if an image layout differs.
- `test_harbor_foundation.py` runs real Ansible against isolated CLI fixtures,
  including wrong target/ownership, zero-change repeat and partial/uncertain writes.
- Native/client SSO tests run real Ansible against disposable HTTPS services.
- `test_harbor_stage.py` checks read-only exact-release, runtime-schema, readiness
  and UID/spec-preservation refusals, including the data-to-app checkpoint. The audit reads no Kubernetes Secrets,
  performs no exec, and never declares TLS/login/push-pull/restore acceptance.
- No offline pass substitutes for physical TLS/CNI, image pull, browser/MFA,
  migrations, load, persistence or restore tests. CI skipping is not a pass.

For the audit, supply canonical owner-only 0600 kubeconfig/evidence files in owned
0700 directories, exact `--context`, `--expected-api`, `--expected-cluster-uid`,
`--baseline`; data/app modes also require `--expected-namespace-uid`, `--release`
and `--commit`, plus `--data-checkpoint`. Data mode writes a new protected
checkpoint only after its checks pass, or verifies an identical existing one.
App mode requires that checkpoint and preserves the database, Valkey release and
two data PVC identities/specs; it cannot capture its own replacement checkpoint.
When an app-only correction uses a newer reviewed release, explicitly supply both
`--data-release` and `--data-commit` for the original accepted data checkpoint.
The current `--release`/`--commit` must still match the live source/root exactly.
Without the paired data options, the audit requires the same release for both
stages. Never edit or recapture the original checkpoint to make a correction pass.
Snapshot creates a new evidence file and never overwrites it.
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
