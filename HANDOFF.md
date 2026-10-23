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
