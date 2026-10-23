# Homelab session handoff

Last updated: 2026-10-23

## Resume location and local checkout move

- Use `/home/corey/src/perkforge-platform` as the working directory. The old
  local checkout `/home/corey/src/homelab` has been removed.
- `.secrets/` was verified identical to the original local copy. The RHEL ISO
  and both VM disks are under `images/`; the libvirt `images` pool and both VM
  definitions use this checkout's image paths.
- After the move, `cks-control` and `cks-worker` were started and both RKE2
  nodes were verified `Ready` through this checkout's kubeconfig.
- Git remote `origin` is `perkforge/perkforge-platform`; `source` retains
  `coreyperkins/homelab`. Keep the old GitHub repository until the in-cluster
  Fleet source is migrated and verified. Deleting that GitHub repository
  requires a separate explicit approval.

## Product direction and repository move

- The project identity is Perkins Forge / PerkForge Platform: a functional,
  secure, multi-tenant Kubernetes PaaS reference implementation demonstrating
  platform engineering, DevSecOps, security architecture, and RMF/GRC.
- Continue local development in the disposable VM harness while the physical
  ThinkCentre hardware is shipped, then move to the three-node RKE2 cluster.
  The current operator uses synthetic tenants to test genuine tenant
  provisioning and security boundaries. Keep portable deployment patterns
  where practical; EKS, AKS, and multiple production environments are not
  active targets. Commercial billing and public onboarding are out of scope.
- The engineering objective includes working PaaS capabilities, implemented
  security controls, repeatable assessment evidence, findings, and risk
  remediation. Do not describe the project primarily as a single-user
  homelab experiment.
- A history-preserving migration from `coreyperkins/homelab` to
  `perkforge/perkforge-platform` is documented in
  [`docs/MIGRATION-PLAN.md`](docs/MIGRATION-PLAN.md). The reviewed changes
  and migration status are in commits `ead1fb2`, `5f7f30e`, `c5cff46`, and
  `c4698d5` on the destination's `main` branch. The PerkForge repository is now the
  canonical `origin`; the former `coreyperkins/homelab` remote is retained as
  `source`. No infrastructure identifiers or Fleet source URLs have changed.
- On 2026-10-23, GitHub CLI authentication was verified for `coreyperkins`.
  `perkforge/perkforge-platform` is private and the account reports `ADMIN`
  permission. The pushed `main` branch was verified at `c4698d5`. Local
  `main` tracks PerkForge `origin/main`; `source/main` retains the old remote.
- Repository settings and operational Fleet references remain for a later
  approved migration stage. See [`docs/MIGRATION-PLAN.md`](docs/MIGRATION-PLAN.md).

## Current local lab state

- `cks-control` is RHEL 10.2 at `192.168.122.201`.
- `cks-worker` is RHEL 10.2 at `192.168.122.202`.
- Both nodes are configured with SELinux enforcing, the RHEL DVD repositories, and host prerequisites for RKE2.
- RKE2 `v1.36.5+rke2r1` is installed; both nodes were verified `Ready` after
  the checkout and libvirt image-path move.
- Rancher `2.15.2` is installed at <https://rancher.local-lab.test>.
- Mattermost Team Edition `12.0.0` is deployed at <http://mattermost.local-lab.test> through Fleet. At the last recorded check, its GitRepo reported 4/4 ready bundle deployments, the app and database pods were Ready, and both PVCs were Bound.
- Keycloak and Valkey have deployed Helm releases; Keycloak's pod is Ready. Harbor's first install succeeded, but a later upgrade failed while its database was OOM-killed (exit 137); its core is Ready at the last inspection, while one jobservice pod is CrashLooping. Harbor needs recovery and lower resource use before relying on its UI. GitLab's PostgreSQL and Valkey dependencies are running, but GitLab itself was not installed; its chart initially used the Rancher proxy context, now fixed in the script. GitLab Runner remains disabled in this low-footprint profile.
- The app trial reached 86% memory use on `cks-control` and 72% on `cks-worker` before the Harbor OOM. Do not tear down/rebuild or rerun the all-app Fleet profile until the app resource profile is adjusted. The latest user-approved run stopped before GitLab after Harbor's database restart.
- `/etc/hosts` maps both `rancher.local-lab.test` and `mattermost.local-lab.test` to `192.168.122.201`.

## Kubeconfig

- The default `/home/corey/.kube/config` now selects `rancher-local`, which uses Rancher’s proxy endpoint for the local cluster. Its direct `rke2-lab` context remains available.
- The original kubeconfig backup is `/home/corey/.kube/config.bak-20261023-094404`.
- `.secrets/rke2.yaml` remains the direct RKE2 kubeconfig used by the local scripts. `.secrets/kubectl` is the bundled client.
- The Rancher-generated kubeconfig token may expire according to Rancher’s kubeconfig-token TTL. If it stops authenticating, download/regenerate a cluster kubeconfig from Rancher and merge it into `~/.kube/config` while preserving both contexts.

## Mattermost account and secrets

- No Mattermost application admin account or password is preconfigured. Create the first account through the Mattermost UI; Mattermost assigns the first user the System Admin role.
- `.secrets/mattermost-db-password` is only the PostgreSQL password and cannot be used to log into Mattermost.
- Rancher username is `admin`; bootstrap and any updated admin password files are under `.secrets/`.
- Never print or commit any `.secrets/` contents.

## One-command rebuild

The complete local stack is rebuilt with:

```sh
local-lab/scripts/rebuild-local-lab.sh --confirm-destroy
```

This deletes both VM disks and cluster data, then provisions RHEL, configures hosts, installs RKE2 and Rancher, and deploys the platform applications through Fleet. It checks the ISO, direct libvirt access, and remote Fleet files before teardown. It stops on the first failure and records output in `.secrets/local-lab-rebuild-*.log`. Do not run this unless the user explicitly requests a destructive rebuild.

The Fleet deploy command is `local-lab/scripts/deploy-mattermost.sh`. It preserves or recovers existing platform credentials, applies the foundation and platform-app GitRepos, and waits for ten bundles and Mattermost pods. Its Fleet readiness check uses the bundle deployment `1/1` count; Fleet leaves the display state blank for ready bundles. To try the local Keycloak/GitLab/Harbor charts before publishing their Fleet files, use `local-lab/scripts/deploy-platform-baseline.sh`.

## Pending local Fleet changes

The tenant-foundation bundle and separate Fleet GitRepos are pushed to
PerkForge `main`: `local-lab` manages storage, tenant controls, and the database
operator; `platform-apps` manages Keycloak, GitLab dependencies and app, Harbor,
and Mattermost. They have not been reconciled to the cluster because the
in-cluster Fleet GitRepo still references the old GitHub repository. Migrate
and verify Fleet's source URL before considering deletion of the old GitHub
repository. The current 8-GiB VM footprint OOMed Harbor's database during an
upgrade, before GitLab was installed; profile app resources before another
full app run.

## Recent fixes

- Removed the inventory-wide `ansible_become: true` setting so delegated localhost tasks do not try to use the VM sudo password. Host and RKE2 plays enable become explicitly.
- Added a bounded wait for Rancher to create its webhook deployment before checking its rollout.
- Fixed Fleet readiness parsing in the Mattermost script and added periodic status output and a grace period for transient dependency errors.
- Fixed the Kickstart sudoers rule, persistent DVD attachment, host-playbook ordering, and Ansible variable-file loading. Details are in `local-lab/README.md`.

## Working tree

Review `git status` before committing. Root-level `kubectl` and `kubectl.sha256` artifacts are ignored and should not be committed.
