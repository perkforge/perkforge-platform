# Homelab session handoff

Last updated: 2026-10-23

## Resume location and local checkout move

- Use `/home/corey/src/perkforge-platform` as the working directory. The old
  local checkout `/home/corey/src/homelab` has been removed.
- `.secrets/` was verified identical to the original local copy. The RHEL ISO
  and both VM disks are under `images/`; the libvirt `images` pool and both VM
  definitions use this checkout's image paths.
- `cks-control` and `cks-worker` are running RKE2 and both nodes are Ready.
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
- Fleet's `local-lab` and `platform-apps` GitRepos both fetched the public
  PerkForge `main` revision and reported `Stalled=False`. The seven bundles in
  the conservative profile reported `1/1` ready.
- The active `platform-apps` profile manages Keycloak, its PostgreSQL cluster,
  and GitLab's PostgreSQL/Valkey dependencies. The GitLab application, Harbor
  Fleet bundle, and Mattermost are opt-in paths, disabled while VM memory
  headroom is limited. Harbor remains outside the active Fleet profile.
- After reconciliation, `keycloak-db`, Keycloak, `gitlab-db`, and Valkey pods
  were Ready; their database and Valkey PVCs were Bound. Node memory was about
  82% on `cks-control` and 62% on `cks-worker` at that check. Review headroom
  before enabling the heavier app bundles.
- Both VMs have 4 GiB RAM. The one-command rebuild now installs the conservative
  Fleet profile and does not install GitLab itself, Harbor through Fleet, or
  Mattermost.

## Kubeconfig

- The default `/home/corey/.kube/config` now selects `rancher-local`, which uses Rancher’s proxy endpoint for the local cluster. Its direct `rke2-lab` context remains available.
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
- Phase 5 tenant observability remains unverified because its optional profile is not deployed. Phase 6 has runner/evidence groundwork; scheduling and findings/remediation workflow remain. Phase 7 is future work.
- CAC note for a future IL5-like target: Playwright's built-in client-certificate setting accepts PEM key material or a PKCS#12/PFX bundle; do not export a CAC private key for automation. Routine identity/authorization checks should use synthetic identities. A separate authorized CAC end-to-end test should use approved smart-card middleware and test credentials, with an attended step if policy requires user presence. See `docs/TENANT-SECURITY-BOUNDARY.md`.
- Next: verify Keycloak-authenticated tenant login and Rancher project/dashboard permissions in the local synthetic-identity environment; keep CAC authentication as a separate authorized integration test for environments that require it. Then continue Phase 5 and Phase 6 acceptance criteria.
