# Homelab session handoff

Last updated: 2026-10-26

## Nextcloud working local deployment — 2026-10-26

- User authorized committing/pushing both repositories and carrying out the
  published activation and trial acceptance workflow. Both repositories were
  pushed; application workload pin is `3feb9b09686d5e1e08e9bf6616f6126335a1653f`.
- Fleet app GitRepo is in dedicated Rancher Fleet workspace
  `fleet-home-nextcloud`; app bundles 2/2, local-lab 5/5, platform-apps 4/4 Ready.
  Home is associated with Rancher Project local:p-home-local. Keycloak stays 0/0.
- The workspace Policy requires the scoped deployer and disables namespace
  creation. A mapping selects only Home bundles for fleet-local/local. No tenant
  namespace patch permission was added; namespace/policy/quota/RBAC remain owned
  by the platform. Rancher owns its Fleet workspace namespace. A temporary
  duplicate namespace declaration was removed only after Helm keep protection
  was recorded in the installed release.
- Nextcloud35.0.2/chart9.4.1 and single-instance CNPG PG17.6 are Ready on worker.
  Both PVCs Bound (app4Gi, DB2Gi). Fixed live-discovered constraints through Git:
  single-instance update strategy must be unsupervised; UID33 must create PVC
  subdirectories before kubelet subPath mounts; trusted domain is explicit;
  startup hook sets Cron mode; single Apache worker needs backend KeepAlive Off.
  One-time ownership repair changed only the seven new app-volume directories,
  with no file deletion or data reset. No privileged app container was added.
- Developer-only bootstrap approval was taken from the user's activation
  instruction. Credentials are in ignored owner-only
  .secrets/nextcloud/nextcloud-admin-password and nextcloud-db-app-password.
  Username home-admin. Immutable Secrets exist; no credentials were published.
  Public self-signed certificate is .secrets/nextcloud/public-tls.crt.
- Acceptance passed: verified-certificate HTTPS/WebDAV upload/download, checksum
  after app-pod deletion/recreation, same app/DB PVC/volume identities, browser
  login to dashboard, successful scheduled CronJobs, non-root app with no API
  token, selected cross-tenant authorization denials and deployer RBAC denials.
  Private evidence in application .evidence/smoke-20261027T011531Z/ and
  .evidence/browser-20261027T012251Z/. Browser used local-only TLS bypass; HTTPS
  curl used the verified public certificate. No browser state or screenshots.
- Current profile: app512Mi, DB320Mi, cron128Mi limits; PHP192M with 64Mi opcode
  cache; one Apache worker; CronJob concurrency Forbid, 900-second deadline.
  Pre-deployment gate derives total960Mi plus512Mi reserve. After browser trial,
  observed headroom was roughly0.75Gi control and1.1Gi worker; both nodes Ready.
- Unverified/pending: separate home-LAN client access, full pod-network denial,
  backup/restore and node-failure recovery. The workstation has LAN192.168.1.183;
  VMs are behind libvirt NAT. Tests used temporary hostname mapping to
  192.168.122.202. No host/router/network changes made. User was asked to approve
  only a workstation hosts entry; answer is pending. Do not silently change
  routing or public exposure. Use replaceable data until backup/restore exists.
- The initial failed CronJob history remains; subsequent jobs completed. Do not
  mistake those historical failures for a current failure or erase evidence.
  Unit tests were not run; live trial checks were explicitly authorized.
  Existing untracked evidence, .orig files and caches were preserved.
- See docs/NEXTCLOUD-INTEGRATION.md and the separate app repo's operations and
  recovery docs. Full platform deploy/rebuild scripts still assume running
  Keycloak and must not be used on this temporary paused-identity profile.

## Worker storage expansion — 2026-10-26

- The user explicitly authorized expanding only cks-worker's virtual disk to
  100 GiB and persisting that size in provisioning for a future approved rebuild.
- Expanded the live qcow2 via libvirt blockresize, then extended GPT partition
  vda3, resized its LVM PV, extended /dev/rhel_cks-worker/root into free extents,
  and grew XFS online. No reboot, formatting, data deletion, image cleanup or
  physical-disk partition changes occurred. Control VM storage is unchanged.
- Verified worker disk 100 GiB, root about 95 GiB, swap 3 GiB, /boot 2 GiB,
  and about 74 GiB free. local-path uses /opt/local-path-provisioner on root.
  Guest metadata backup is /var/tmp/perkforge-worker-storage-before.mfc8cD/
  (partition-table.sfdisk and lvm.conf); this is metadata, not a data backup.
- provision-vms.sh now selects disk sizes by VM name (control 30, worker 100)
  and explicitly allocates the new worker's remaining capacity to root instead
  of a separate /home or a capped automatic root. Existing-VM provisioning
  continues to leave disks untouched. Shell syntax validation passed; no
  provisioning/rebuild or tests were run. Changes remain local, uncommitted.
- The earlier disk-space blocker below is resolved; fresh Nextcloud capacity
  checks and the remaining secret/bootstrap, LAN, publication and activation
  gates still apply. Protected Nextcloud remains undeployed.

## Tenant catalog layout refactor — 2026-10-26

- The user approved splitting the unwieldy catalog and generated manifest.
  `local-lab/tenant-config/tenants.yaml` is now a small index; editable tenant
  records live under `tenant-config/tenants/{tenant-alpha,tenant-bravo,home}.yaml`.
- Added shared `tenant_catalog.py` loader; all catalog-reading runtime scripts
  use it. Explicit relative references prevent accidental discovery; legacy
  inline catalogs remain supported. Existing test fixtures use the loader and
  retain their two-synthetic-tenant scope. No tests were added or run.
- Renderer still validates the assembled catalog globally. Output is now
  `tenant-foundation/shared/roletemplates.yaml` plus `tenants/<id>/` files for
  Project, namespaces, quotas, limits and NetworkPolicies. The old combined
  generated `tenant-foundation/tenants.yaml` was removed.
- Retained the same parent Fleet bundle identity and all resource identifiers
  and content. Shared roles have a separate directory in that same bundle,
  rather than a new Fleet bundle, to avoid transferring resource ownership.
  No nested fleet.yaml files or GitRepo path migration are needed.
- Semantic comparison confirmed all 20 generated objects identical before
  and after splitting. Catalog sync, compilation and plan-only entry points
  passed; no live API changes, tests, commits or pushes occurred for this work.
- Nextcloud activation is still blocked by worker disk capacity, secret
  bootstrap approval and LAN routing. The user declined cache cleanup; do not
  reclaim cached images. Do not publish tenant removal as a harmless refactor.

## Nextcloud implementation continuation — 2026-10-26

- Keycloak pause commit `bb9c417` was pushed by the user; Fleet reconciled it.
  Keycloak is 0/0, its DB is healthy. Subsequent Nextcloud files remain local
  and uncommitted. No application deployment or secret bootstrap occurred.
- Read `docs/NEXTCLOUD-INTEGRATION.md` for discovery, ownership, remaining gates,
  and all validation limits. The separate application repo now contains two
  Fleet bundles, pinned Helm values, architecture/operations/recovery docs and
  a read-only capacity preflight. The platform has protected classification,
  rendered Home foundation, support RBAC/policies, PAUSED Fleet registration,
  and a plan-only development credential helper.
- Chart 9.4.1 / Nextcloud 35.0.2-apache rendered successfully; chart archive
  SHA256 matched its repository index. CNPG reuses the existing PG17.6 pin.
  Python compilation, catalog synchronization and whitespace checks passed.
  No tests were added or run (repository guidance). Runtime compatibility,
  registry images, server admission, LAN access and persistence are unverified.
- Network escalation is now available through automatic review; the public
  chart downloads and read-only node stats succeeded with require_escalated.
- Worker free space is only about 5.16 GiB, below the planned 6-GiB PVC requests
  and 8-GiB preflight floor. Activation remains blocked. No image cleanup,
  disk modification, workload deletion, or shared capacity change authorized.
- Pending user answers: approve development-only secret bootstrap and confirm
  hostname/private LAN route. Also obtain commit/push authorization for these
  concrete new changes before publication. Preserve existing untracked files.
- Publish/reconcile platform foundation/support before secrets and activation;
  registration stays paused until prerequisites pass. Pin reviewed application
  commit in registration before unpausing. Do not bypass GitOps with Helm install.

## Nextcloud preparation and Keycloak pause — 2026-10-26

- The user requested Nextcloud as a protected reference tenant in the separate
  `perkforge-tenant-nextcloud` repository, which is currently empty.
- Read-only discovery confirmed both nodes Ready, Fleet at `b7f666d` with 3/3
  foundation and 4/4 application bundles Ready, explicit `local-path` storage
  (not default, WaitForFirstConsumer, Delete reclaim), Traefik with node host
  ports 80/443, and the existing CNPG operator. Only Rancher's namespace-scoped
  certificate Issuer exists; no CNPG Backups or ScheduledBackups were found.
- Metrics API working sets were 3,075,780 Ki on control and 2,451,072 Ki on
  worker, against 3,740,808 Ki allocatable each. Observability stays disabled.
- The user authorized pausing Keycloak to make room for Nextcloud, whose
  initial deployment will not use Keycloak SSO. Local AuthConfig was verified
  enabled. The Keycloak Helm values now request zero application replicas;
  its PostgreSQL cluster, PVCs, secrets, ingress, and OIDC config are retained.
  Tenant Keycloak/Rancher SSO is unavailable while the application is paused.
- This is a LOCAL, UNPUBLISHED change until committed and pushed with explicit
  authorization. The live StatefulSet was still 1/1 at preparation time.
  Fleet watches origin/main; direct scaling would conflict with GitOps.
- Restore `replicas: 1` through GitOps to resume. The existing full deployment
  and rebuild checks assume running Keycloak and are incompatible with this
  temporary paused profile; do not use them to apply this change. Allow Fleet
  to reconcile the values change, then verify zero replicas and fresh capacity.
- Nextcloud deployment remains pending: private LAN hostname/routing decision,
  development-only secret bootstrap approval, reviewed application manifests,
  and sufficient measured worker capacity after Keycloak is paused. No cluster
  mutation, secret bootstrap, disk changes, commit, push, or tests performed.

## Resume location and local checkout move

- Use `/home/corey/src/perkforge-platform` as the working directory. The old
  local checkout `/home/corey/src/homelab` has been removed.
- `.secrets/` was verified identical to the original local copy. The RHEL ISO
  and both VM disks are under `images/`; the libvirt `images` pool and both VM
  definitions use this checkout's image paths.
- `cks-control` and `cks-worker` are running RKE2. The API readiness endpoint
  recovered after the control node OOM-killed `kube-apiserver`; however, the
  control VM remains critically short on memory. See the 2026-10-26 incident
  record below.
- Git remote `origin` is `perkforge/perkforge-platform`; `source` retains
  `coreyperkins/homelab`. The PerkForge repository is public, and anonymous
  access to its `main` branch was verified. Both in-cluster Fleet GitRepos now
  use PerkForge and reconciled the conservative profile.
- `coreyperkins/homelab` is now archived and read-only; it has not been deleted.
  Deletion requires separate explicit approval.

## Product direction and repository move

- The project identity is Perkins Forge / PerkForge Platform: a functional,
  secure, multi-tenant Kubernetes PaaS reference implementation demonstrating
  platform engineering, DevSecOps, security architecture, and RMF/GRC.
- Continue local development in the disposable VM harness while the physical
  ThinkCentre hardware is shipped, then move to the three-node RKE2 cluster.
  Use synthetic tenants to exercise real tenant provisioning and isolation.
  Keep portable deployment patterns where practical; EKS, AKS, and multiple
  production environments are not active targets.
- The engineering objective connects working PaaS capabilities to implemented
  security controls, repeatable assessment evidence, findings, and risk
  remediation. Do not describe the project primarily as a single-user
  homelab experiment or claim formal authorization.
- The history-preserving move from `coreyperkins/homelab` is documented in
  [`docs/MIGRATION-PLAN.md`](docs/MIGRATION-PLAN.md). The PerkForge repository
  is canonical `origin`; the old source remote remains `source`. The user
  changed the destination visibility to public. No cluster names, namespaces,
  labels, or VM addresses were changed as part of the brand move.

## Current local lab state

- `cks-control` is RHEL 10.2 at `192.168.122.201`; `cks-worker` is RHEL 10.2
  at `192.168.122.202`. Both use SELinux enforcing and RKE2 `v1.36.5+rke2r1`.
- Rancher `2.15.2` is installed at <https://rancher.local-lab.test>.
- Fleet's `local-lab` and `platform-apps` GitRepos use the public PerkForge
  `main` branch. The active app profile has been returned to its prior
  low-footprint state after the observability rollout coincided with a control
  node OOM. Keep Prometheus/Grafana and OpenCost disabled on these VMs.
- The active `platform-apps` profile manages Keycloak, its PostgreSQL cluster,
  and GitLab's PostgreSQL/Valkey dependencies. The GitLab application, Harbor
  Fleet bundle, and Mattermost are opt-in paths, disabled while VM memory
  headroom is limited. Harbor remains outside the active Fleet profile.
- The VMs have 4 GiB RAM and 2 vCPUs each. After the rollback and Keycloak move,
  `cks-control` used about 2.8 GiB with 799 MiB available; `cks-worker` used
  about 2.6 GiB with 952 MiB available. Both nodes are Ready. The host reported
  14 GiB total RAM, 3.7 GiB available, and 8.5 GiB of swap in use. Do not
  increase VM memory on this host.
- The one-command rebuild now installs the conservative
  Fleet profile and does not install GitLab itself, Harbor through Fleet, or
  Mattermost.
- Keycloak is now pinned to `cks-worker`; this rebalances its roughly 750 MiB
  runtime away from the control VM. Fleet reports 4/4 active app bundles Ready;
  Keycloak is Ready on the worker, Keycloak ingress returned HTTP 302, Rancher's
  `/ping` returned `pong`, and the API readiness endpoint returned `ok`.

## Kubeconfig

- The default `/home/corey/.kube/config` now contains only the verified direct
  `rke2-lab` context and has mode `600`. Rancher-proxy contexts were removed
  after CA verification failed. `.secrets/rke2.yaml` remains the private source
  used by lab scripts.
- The original kubeconfig backup is `/home/corey/.kube/config.bak-20261023-094404`.
- After the latest Rancher reinstall, its CA and generated token were refreshed; `rancher-local` was verified against both Ready nodes. Backups made during that repair are `/home/corey/.kube/config.bak-20261023-rancher-ca-before-rebuild` and `/home/corey/.kube/config.bak-20261023-rancher-token-refresh`.
- `.secrets/rancher-current-ca.crt` and `.secrets/rancher-generated.yaml` contain the current Rancher trust and generated kubeconfig; keep them private and ignored.
- `.secrets/rke2.yaml` remains the direct RKE2 kubeconfig used by the local scripts. `.secrets/kubectl` is the bundled client.
- The Rancher-generated kubeconfig token may expire according to Rancher’s kubeconfig-token TTL. If it stops authenticating, download/regenerate a cluster kubeconfig from Rancher and merge it into `~/.kube/config` while preserving both contexts.

## Mattermost account and secrets

- No Mattermost application admin account or password is preconfigured. Create the first account through the Mattermost UI; Mattermost assigns the first user the System Admin role.
- `.secrets/mattermost-db-password` is only the PostgreSQL password and cannot be used to log into Mattermost.
- Rancher username is `admin`; bootstrap and any updated admin password files are under `.secrets/`.
- Never print or commit any `.secrets/` contents.

## One-command rebuild

The local lab rebuild command is:

```sh
local-lab/scripts/rebuild-local-lab.sh --confirm-destroy
```

The rebuild records a private checkpoint in `.secrets/local-lab-rebuild-state`.
After teardown has completed, a failed run can be continued without deleting
VM disks by running:

```sh
local-lab/scripts/rebuild-local-lab.sh --resume
```

The resume path reruns idempotent provisioning and deployment stages. It
refuses to resume if the prior run stopped during teardown, because VM and
disk state must be reviewed before another destructive action. A successful
run now verifies Fleet's expected remote revision, waits for Keycloak and the
GitLab dependency pods, checks Valkey with `PING`, checks Keycloak through
Traefik ingress, and checks Rancher's `/ping` endpoint. The browser still
requires the documented laptop `/etc/hosts` entries.

It deletes both VM disks and cluster data, then provisions RHEL, configures
hosts, installs RKE2 and Rancher, and deploys the conservative Fleet profile.
It checks the ISO, libvirt access, and remote Fleet files before teardown. The
ISO and `.secrets/` are preserved. The current profile includes Keycloak and
GitLab's database/Valkey dependencies; GitLab, Harbor Fleet deployment, and
Mattermost require deliberate opt-in and a memory review.

`local-lab/scripts/deploy-platform-profile.sh` applies the GitRepos and waits
for both sources and all seven selected bundles to report the expected Git
revision and Ready state. `local-lab/scripts/deploy-mattermost.sh` is reserved
for the explicitly enabled full app profile; it checks required paths before
creating credentials or waiting for workloads.

## Disposable AWS lab scaffolding

- `ansible/aws-lab/` contains a separate EC2/RKE2 implementation; it does not
  reuse the physical-host inventory or local VM settings.
- The planned lab uses three `t3a.large` nodes in `us-east-1`, one server and
  two agents, no public ingress, SSM-tunneled access, Standard CPU credits, and
  encrypted EBS volumes that teardown deletes.
- OS/AMI selection is intentionally unresolved. A pinned AMI ID, root-device
  name, and OS family must be reviewed before provisioning. RHEL PAYG versus an
  AWS Linux AMI remains a cost and compatibility decision.
- Provision, start, configure, teardown, and account-level budget playbooks
  have separate confirmation gates. The budget remains outside per-run teardown.
- No AWS API calls, account changes, provisioning, or tests were run while
  creating the scaffolding. See `ansible/aws-lab/README.md`.

## Fleet migration status

The Fleet source migration is complete for the local VM cluster. Both GitRepos
use the public PerkForge repository and reconciled the conservative profile.
The new GitLab dependency layout separates the PostgreSQL Cluster manifest
from the Valkey Helm bundle; existing database resources were adopted in place
by Fleet. The old GitHub repository is archived and read-only; its local
`source` remote is retained. Deletion requires separate explicit approval.

## Recent fixes

- Removed the inventory-wide `ansible_become: true` setting so delegated localhost tasks do not try to use the VM sudo password. Host and RKE2 plays enable become explicitly.
- Added a bounded wait for Rancher to create its webhook deployment before checking its rollout.
- Fixed Fleet readiness parsing in the Mattermost script and added periodic status output and a grace period for transient dependency errors.
- Fixed the Kickstart sudoers rule, persistent DVD attachment, host-playbook ordering, and Ansible variable-file loading. Details are in `local-lab/README.md`.
- Quoted the GitLab database CPU quantity so Fleet no longer sees a persistent `Modified` drift after Kubernetes normalizes the resource quantity.
- The latest rebuild encountered a worker installer stall. A clean worker reinstall succeeded; the provisioner now detects six minutes without DVD or root-disk I/O and retries once only for a VM it created in that run. Existing VM disks are preserved. This new retry path has not yet been exercised end-to-end.

## Working tree

Review `git status` before committing. Root-level `kubectl` and `kubectl.sha256` artifacts are ignored and should not be committed.

## Tenant isolation implementation handoff — 2026-10-23

The active implementation is in `/home/corey/src/perkforge-platform`, branch
`main`. The working tree has a large set of uncommitted tenant-foundation,
Keycloak/Rancher binding, security verification, and optional monitoring/OpenCost
changes. Nothing was committed or pushed in this session.

The latest work added
`local-lab/scripts/verify-tenant-observability.py` and its tests. It is
plan-only unless `--apply` is given. The live path checks tenant attribution
labels in Prometheus, shared-service denial from restricted tenant probe Pods,
Prometheus scrape ingress policy, and observability service exposure. It writes
sanitized JSON/Markdown evidence and removes uniquely labeled probe Pods. The
live path has not been run; the optional monitoring and OpenCost Fleet bundles
remain disabled and undeployed.

Validation before the last verifier edit: all 53 tests passed,
`render-tenant-foundation.py --check` passed, the verifier plan-only command
passed, and `git diff --check` passed. A direct `py_compile` attempt could not
write the repository's `__pycache__` because that location is read-only; use
`PYTHONPYCACHEPREFIX=/tmp/perkforge-pycache python3 -m py_compile ...` if needed.

The final verifier edit broadened exposure checks to reject any non-ClusterIP
Service or Ingress in the dedicated `monitoring` and `opencost` namespaces. It
was not re-tested before stopping. Begin by updating the verifier tests to
match this behavior (the existing service-exposure assertions still expect the
older error wording), then rerun the suite and static checks. Afterwards add
operator instructions to `local-lab/README.md` and the appropriate row to
`docs/CONTROL-EVIDENCE-MATRIX.md`. Do not run the verifier with `--apply` or
change the live cluster without explicit authorization.

The main objective remains the full multi-tenant platform capability, not just
the observability verifier. Rancher OIDC is still not enabled, and live
Keycloak-to-Rancher login, effective dashboard permissions, runtime/network
enforcement, and quota behavior need actual cluster verification before any
completion claim.

## Current tenant-platform state — 2026-10-26

Read-only cluster checks were run after resuming work:

- `cks-control` and `cks-worker` are Ready on RKE2 `v1.36.5+rke2r1`.
- Fleet GitRepos `local-lab` and `platform-apps` are Ready at remote commit
  `ead406248994b53ab133f01522ad11c5e3ba0a85`; the current tenant changes are
  uncommitted and are not what Fleet is reconciling.
- The tenant foundation bundle currently reports Ready, but this is the older
  deployed revision. `tenant-alpha` and `tenant-bravo` exist with legacy
  `platform.homelab/tenant` labels, restricted Pod Security labels, default
  deny policies, and tenant-specific allow policy names. They do not yet have
  the new `platform.perkforge.io/*` ownership labels or Rancher project
  association annotations expected by the current catalog/verifiers.
- The only Rancher projects are the system `p-fbkk4` and default `p-s5xx7` in
  management namespace `local`; neither has PerkForge tenant ownership labels
  or project quotas. Do not silently adopt them or move namespaces into another
  project. The current renderer/reconciler expects catalog-owned project IDs
  and has ownership safeguards; review migration behavior before applying.
- Rancher local AuthConfig is not enabled for OIDC. Keycloak client/group
  provisioning is scripted, but it does not establish effective Rancher
  authentication. No live tenant RBAC, project association, quota, or new
  network/admission enforcement validation has passed.
- The monitoring and OpenCost Fleet paths are disabled. The optional verifier's
  live mode was not run.

The observability verifier's exposure tests were aligned with its current
behavior. Validation now passes: 54 local tests, tenant manifest renderer
`--check`, Python compilation using `PYTHONPYCACHEPREFIX=/tmp/perkforge-pycache`,
verifier plan-only mode, and `git diff --check`. No cluster resources were
changed. The verifier workflow and its limits are documented in
`local-lab/README.md`, `docs/OBSERVABILITY-AND-COST.md`, and
`docs/CONTROL-EVIDENCE-MATRIX.md`.

Next work should review the uncommitted tenant foundation migration against the
existing Helm-managed tenant namespaces, complete a safe and idempotent
association/adoption path (or document the required explicit transition), and
resolve the Rancher OIDC activation flow. Keep changes local until reviewed;
Fleet watches the older published revision. Do not push or run deployment/live
verification without the user's applicable authorization. Preserve existing
projects and namespaces during this review.

Additional read-only inspection on 2026-10-26 confirmed the installed tenant
NetworkPolicies select all Pods in each namespace. Their allow policy permits
same-namespace ingress/egress plus CoreDNS; there is no Keycloak egress or
Prometheus scrape-ingress exception in the currently deployed revision.

## Tenant-platform continuation — 2026-10-26

The user clarified that the local RKE2 environment is intentionally disposable:
when starting over, prefer the fastest reproducible teardown/rebuild over
preserving synthetic tenant state. This supersedes the prior recommendation to
preserve/migrate the existing tenant Projects and namespaces. Rancher local
bootstrap/admin access must remain available throughout.

Rancher authentication safeguards and validation:

- `configure-rancher-oidc.py` refuses to configure OIDC unless Rancher's `local`
  AuthConfig exists and is enabled. Its apply path rechecks local auth remains
  enabled after configuring Generic OIDC. It does not modify the `local`
  AuthConfig or Rancher local user records.
- The rebuild playbook stores the Rancher bootstrap password in ignored,
  owner-only `.secrets/rancher-bootstrap-password`; reruns reuse that file.
- Read-only live checks confirmed `local` is enabled (`localConfig`),
  `genericoidc` is currently disabled, and the Rancher `admin` user object is
  present. No live authentication configuration was changed.
- All 61 `local-lab/tests` tests pass; `git diff --check` and shell syntax
  checks for the deploy and rebuild scripts pass.
- A Rancher API server-side dry-run accepted the planned Generic OIDC
  AuthConfig. It used a temporary dummy secret and did not persist resources.

The cluster API is reachable only with network access outside the restricted
execution sandbox; ordinary sandboxed kubectl calls fail with `operation not
permitted`. The server-side dry-run and read-only auth checks succeeded when run
with elevated access. Do not enable OIDC, apply tenant policies, or start the
rebuild unless that is part of the user's explicitly authorized next action.

Next: update the checklist/implementation phase status to account for this
validation, then proceed with the controlled clean-rebuild path when authorized.
After rebuild, validate Keycloak login, Rancher project access, and the tenant
isolation evidence against the actual cluster. Local Rancher bootstrap/admin
login remains the recovery path and must not be disabled.

## Clean rebuild and tenant verification — 2026-10-26

The user authorized a destructive clean rebuild, followed by non-destructive
resumes. The first run deleted both VM definitions and root disks, then installed
fresh RHEL 10.2 VMs. Later `--resume` runs preserved both VM disks. The final
`local-lab/scripts/rebuild-local-lab.sh --resume` completed successfully and
stored checkpoint `completed` in `.secrets/local-lab-rebuild-state`.

Final live state:

- `cks-control` (`192.168.122.201`) and `cks-worker` (`192.168.122.202`) are
  Ready on RKE2 `v1.36.5+rke2r1`.
- Rancher is reachable at `https://rancher.local-lab.test`; `/ping` returned
  `pong`. Local authentication remains enabled, the local `admin` user exists,
  and Generic OIDC is enabled with restricted tenant-group access. The bootstrap
  password remains at `.secrets/rancher-bootstrap-password`.
- Keycloak and its database are Ready; `http://keycloak.local-lab.test/auth/`
  returned HTTP 302. Keycloak admin credentials are in
  `.secrets/keycloak-admin-password`.
- Six synthetic tenant users/groups and six Rancher Project RoleTemplateBindings
  were reconciled. The three tenant role templates use least-privilege rules;
  tenant admins cannot directly create Pods, which also prevents `pods/exec`
  through that permission path.
- Fleet fetched the published `main` revision and all seven enabled profile
  bundles became Ready. Valkey returned `PONG`; GitLab's database is Ready while
  the GitLab application remains opt-in.
- Live evidence passed: RBAC 94/94, Pod Security Admission 9/9, quota 4/4, and
  network isolation 7/7. Final JSON/Markdown artifacts are present under
  `local-lab/evidence/{tenant-rbac,tenant-admission,tenant-quota,tenant-network}/`.

The final automated rebuild does not test interactive browser SSO. The user
should confirm Rancher local admin login, Keycloak admin login, and tenant login
through Keycloak in the two UIs. Until that browser flow is checked, mark
Keycloak-to-Rancher interactive login and tenant dashboard access as pending;
the Kubernetes RBAC evidence verifies API authorization only.

Implementation corrections published during the rebuild: Rancher quota
annotation key ordering and unset RoleTemplate defaults were normalized for
Fleet; Keycloak 26 mapper defaults were pinned; synthetic account ownership now
uses catalog group membership because unmanaged user attributes are disabled by
default; the RBAC verifier handles kubectl's non-namespace-scoped warning; and
the privileged Pod probe is valid before Pod Security Admission evaluates it.

## Tenant test automation update — 2026-10-26

- Commit `7190639` added a plan-only-by-default suite runner and operator instructions.
- Local unit suite: 72 tests passed. Live suite: RBAC 94/94, admission 9/9, quota 4/4, network 7/7. Overall evidence: `local-lab/evidence/tenant-suite/tenant-suite-20261026T172504322350Z/`.
- These results verify the current project/binding preflights, impersonated-group Kubernetes authorization, selected admission/quota paths, and tested pod-network paths. Browser SSO, Rancher dashboard behavior, group revocation, aggregate/storage quota enforcement, runtime isolation, and broader network paths remain unverified.
- Phase 5 tenant observability remains unverified because its optional profile is disabled. Phase 6 has a runner, timestamped evidence, and untriaged finding-candidate extraction. Scheduling, alerting, risk assessment, findings ownership, and remediation workflow remain. Phase 7 is future work.
- CAC note for a future IL5-like target: Playwright's built-in client-certificate setting accepts PEM key material or a PKCS#12/PFX bundle; do not export a CAC private key for automation. Routine identity/authorization checks should use synthetic identities. A separate authorized CAC end-to-end test should use approved smart-card middleware and test credentials, with an attended step if policy requires user presence. See `docs/TENANT-SECURITY-BOUNDARY.md`.
- Next: verify Keycloak-authenticated tenant login and Rancher project/dashboard permissions in the local synthetic-identity environment; keep CAC authentication as a separate authorized integration test for environments that require it. Then continue Phase 5 and Phase 6 acceptance criteria.

## Phase 2 browser validation and Phase 5 observability — 2026-10-26

The user authorized Playwright for Phase 2 and asked to complete all feasible
Phase 5 work, leaving the Phase 5 dashboard Playwright test as a follow-up.

### Phase 2

- Diagnosed why Rancher's OIDC button generated an invalid login URL. The
  Generic OIDC reconciler nested the provider settings under
  `genericOIDCConfig`; Rancher 2.15.2 expects the inline OIDC fields at the
  AuthConfig root. The wrong shape was accepted as unknown CRD data, so the
  provider appeared populated but returned nil-valued client/redirect fields.
- Updated `local-lab/scripts/configure-rancher-oidc.py` and its tests to emit
  inline fields, use Rancher's `/verify-auth` callback URL, validate ownership,
  and retain the check that Rancher `local` authentication remains enabled.
- Applied the corrected, ownership-checked config to the live cluster. Rancher
  local auth was confirmed enabled before and after; the public provider API
  now returns `https://rancher.local-lab.test/v1-oidc/genericoidc`.
- Added `local-lab/scripts/verify-rancher-tenant-ui.py` and pinned
  `playwright==1.64.1` in `local-lab/requirements-e2e.txt`. Live Playwright
  validation passed 10/10 checks as `tenant-alpha-viewers`: Keycloak redirect
  and login, Rancher dashboard, Alpha project visibility/read, Bravo project
  denial (403), Alpha pods readable, Bravo pods denied (403), and secrets
  denied in both namespaces (403).
- The test used `--allow-local-tls-bypass` because Chromium did not trust the
  disposable lab ingress certificate. It uses a fresh context and does not
  persist browser state, tokens, cookies, screenshots, or traces. The bypass is
  documented as local-lab-only.
- Still unverified: other browser roles and workflows, group membership
  removal/revocation, session expiry, and CAC/PIV middleware.

### Phase 5

- Reviewed live node headroom. At the check, worker use was 2,024 MiB with
  1,152 MiB in requests and 3,740,808 Ki allocatable; control requests were
  about 90% of memory and 91% of CPU. The observability workloads are pinned to
  `cks-worker` except node-exporter, which runs as a daemonset on both nodes.
- Tuned the pinned chart values to about 525m CPU / 688 MiB memory requests and
  1,792 MiB summed main-container memory limits; Prometheus uses 3-day,
  1-GiB retention on a 2-GiB capped ephemeral volume. These are configuration
  estimates, not measured post-deployment use.
- Initially enabled the Prometheus/Grafana and OpenCost Fleet paths, retained
  private ClusterIP-only services, and added a platform-operator Grafana
  overview dashboard. Tenant Grafana access remains prohibited until a
  tenant-safe data plane or query proxy is implemented and verified.
- Static profile tests cover the chart pins, exposure settings, resource
  budgets, node selectors, label allowlist, and dashboard JSON. Updated the
  observability runbook and control-evidence matrix.
- Commit `4e50b17` was pushed to `origin/main`; Fleet fetched it. Prometheus and
  Grafana became Ready on `cks-worker`; Grafana used about 248 MiB and its two
  sidecars about 80 MiB each. Prometheus was also running. An OpenCost pod was
  observed on `cks-control` in `CrashLoopBackOff` (0/2 Ready, 16 restarts).
  The chart's node selector was at the root, but chart version `2.5.33` expects
  `opencost.nodeSelector`; the value is corrected in the disabled bundle and
  guarded by a static assertion.
- At 14:20:35, the control node's kernel OOM killer terminated
  `kube-apiserver` at about 2.25 GiB RSS. At the next inspection, Keycloak used
  about 750 MiB, etcd 168 MiB, and control memory was 3.4 GiB of 3.6 GiB with
  141 MiB available. The RKE2 server restarted and the API readiness endpoint
  later returned `ok`. The rollout timing suggests observability contributed
  to memory pressure, but does not prove the worker-side workload alone caused
  the control-node OOM.
- The workstation itself reported 14 GiB RAM, 3.7 GiB available, and 8.5 GiB
  swap used. Larger VMs are not a safe option on this host. Commit `75629bf`
  removed the observability paths from the live GitRepo; Fleet converged to 4/4
  retained bundles and both monitoring namespaces have no Pods. The OpenCost
  allocation verifier, scrape-policy runtime checks, and Phase 5 dashboard
  Playwright test remain pending until the ThinkCentre cluster is available.

### Working tree / next actions

- Do not alter the existing untracked `local-lab/evidence/` and `.orig` files.
- Keep live cluster changes paused until the ThinkCentre cluster is available.
  The observability workloads are removed; do not re-enable them on the two
  4-GiB VMs.
- After the ThinkCentres arrive, restore the observability paths, validate
  Prometheus scraping and OpenCost attribution, run tenant denial probes, and
  complete the Phase 5 dashboard Playwright test. Do not grant tenant Grafana
  access before tenant-safe query isolation is implemented and verified.
- Continue Phase 3/4 test-gap implementation and Phase 6 evidence workflow
  work offline. Do not describe CAC/PIV or IL authorization as validated.

## Current implementation phase tracker — 2026-10-26

| Phase | Current state | Remaining work | Wait for ThinkCentres |
|---|---|---|---|
| 0 — Repository discovery | Complete | None for the current architecture | No |
| 1 — Tenant foundation and Rancher | Implemented and exercised in the local lab | Revalidate the rebuild and project/namespace association on the physical cluster | For final physical-cluster validation |
| 2 — Identity and RBAC | OIDC fixed; Alpha viewer Playwright passed 10/10 | Browser coverage for other roles, group revocation, and session expiry | For remaining live browser checks; code work can continue now |
| 3 — Security isolation | Network suite 7/7; admission suite 9/9 | Broader ingress/egress and host paths; actual runtime isolation beyond admission | For broader live enforcement checks |
| 4 — Resource governance | Selected quota checks 4/4 | Aggregate tenant usage, storage enforcement, and bypass validation | For live capacity and enforcement checks |
| 5 — Observability and cost | Prometheus/Grafana briefly reconciled; OpenCost CrashLooped on control due to a misplaced chart selector; paths removed, cluster recovered, capacity preflight added | On larger nodes, validate ingestion and tenant denial, deploy corrected OpenCost placement, then dashboard Playwright | Yes — defer runtime acceptance |
| 6 — Lifecycle and security evidence | Runner, timestamped evidence, finding workflow/register, and catalog-driven suspend/resume/offboarding access state | Live revocation/session and GitOps suspension validation; data-safe decommission; evidence retention/alerting; scheduled execution | Yes for live acceptance and lifecycle data-plane decisions |
| 7 — Advanced isolation | Future work | Dedicated node pools and dedicated clusters with enforced placement and boundaries | Yes — requires suitable infrastructure |

## Phase 6 offline evidence enhancement — 2026-10-26

- `run-tenant-security-suite.py` now writes `candidate-findings.json` and
  `candidate-findings.md` alongside each live suite summary. It extracts only
  explicit failed check rows; verifier execution errors are not security
  findings.
- Candidates contain the expected/actual result, evidence path, and potential
  NIST control mappings. They remain `untriaged`; risk is `unassessed`, owner
  and remediation are `unassigned`. The runner does not assign severity,
  accept risk, or close findings.
- Focused offline unit suite passed 6/6. No cluster tests were run for this
  change. Scheduling, alerting, persistent finding ownership, and remediation
  tracking remain future Phase 6 work.

## Phase 6 finding workflow — 2026-10-26

- Added `docs/SECURITY-FINDINGS-WORKFLOW.md` and a reusable record skeleton at
  `docs/templates/security-finding.yaml`.
- The workflow distinguishes machine-generated candidates from reviewed
  findings and defines triage, risk assessment, accountable decisions,
  remediation, retesting, and closure without fabricating ratings or accepting
  risk automatically.
- Updated the CA-7 evidence matrix. This is a documented workflow, not a
  persistent register or operational scheduler. No cluster activity occurred.

## Phase 6 review packet — 2026-10-26

- Added `docs/PHASE-6-REVIEW.md` with current capability status, an offline
  implementation sequence, safe lifecycle semantics for review, evidence and
  scheduling recommendations, and a checklist of decisions.
- It distinguishes private operational evidence from sanitized public examples
  and keeps CAC-dependent browser checks attended unless the target environment
  expressly supports an approved automation path.
- No schedule or cluster operation was enabled. Recommendations in this packet
  are proposals for review, not approved policy.

## Phase 6 offline findings register — 2026-10-26

- Added `local-lab/scripts/manage-security-findings.py`. It imports runner
  candidates idempotently into a mode-0600 local register under `.secrets/`,
  serializes concurrent writers, and appends actor/rationale/timestamp for each
  allowed state change.
- Risk assessment requires impact, likelihood, and residual-risk rationale but
  calculates no rating. Risk acceptance requires a named authority and
  expiry/review date.
  Remediation planning requires owner and due date. Closure requires passing
  retest evidence; regression can reopen a closed record.
- Added 8 offline unit tests. The tool is not a multi-user register or alerting
  system. No live cluster was accessed and no schedule was enabled.

## Phase 6 tenant lifecycle foundation — 2026-10-26

- `TenantCatalog` now accepts optional lifecycle states `active`, `suspended`,
  or `offboarding`; omitted state preserves existing active behavior.
- Foundation rendering adds the lifecycle label only when the catalog opts in.
  The Rancher binding reconciler omits suspended/offboarding access and deletes
  only exact deterministic PRTBs whose project, role, group principal, and
  ownership labels match the catalog. Returning to `active` recreates the
  expected bindings. Conflicts fail closed.
- **Limits:** existing workloads continue running; tenant Fleet application
  reconciliation is not paused; Keycloak group membership and existing login
  sessions are not revoked. `offboarding` currently retains Projects,
  namespaces, workloads, and data. Destructive decommission is not implemented.
- The live tenant catalog and rendered Fleet bundle were not changed, so this
  code change did not request a tenant lifecycle transition. Renderer sync
  check passed. Focused renderer and binding tests passed 20/20. The full suite
  had passed 86/86 before this increment; it was not rerun afterward.
- Cluster state was not changed. Do not describe suspend/offboard as a complete
  enforcement or data-plane operation until the stated limitations are tested
  and addressed.
