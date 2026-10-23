# Repository guidance for Codex

## Start here

- Read [`README.md`](README.md) for the project structure.
- Read [`HANDOFF.md`](HANDOFF.md) before resuming operational work; it records the current lab state and recent decisions.
- Use [`local-lab/README.md`](local-lab/README.md) for the disposable VM workflow and [`ansible/README.md`](ansible/README.md) for the future physical cluster boundary.
- Use [`ansible/aws-lab/README.md`](ansible/aws-lab/README.md) for the separate disposable EC2 environment. Do not run its provision, start, teardown, or budget playbooks without action-specific authorization.

## Keep deployment environments separate

- The root-level inventory and playbooks in `ansible/` are reserved for future
  physical machines. `ansible/aws-lab/` is a separate, disposable EC2
  implementation. Do not share inventories, addresses, or environment settings
  between those subprojects.
- `local-lab/` contains the disposable libvirt VMs, their Ansible configuration, Fleet bundles, and local scripts.
- The local VMs use `192.168.122.201` (`cks-control`) and `192.168.122.202` (`cks-worker`). Do not reuse those addresses for physical hardware.
- AWS lab playbooks can create billable resources and permanently delete disks.
  Do not run them without explicit user authorization for that AWS action.

## Secrets and kubeconfigs

- Never print, commit, or copy values from `.secrets/` into tracked files. The directory is ignored by Git.
- `.secrets/rke2.yaml` is the direct RKE2 kubeconfig. The default `~/.kube/config` currently selects `rancher-local`, which accesses the cluster through Rancher; its `rke2-lab` context is preserved as a direct endpoint.
- The Mattermost database password is not an application login. Mattermost has no seeded admin password; its first registered user receives the System Admin role.
- Root-level downloaded `kubectl` artifacts are ignored; do not add them to commits.

## Running the local lab

- The destructive rebuild is `local-lab/scripts/rebuild-local-lab.sh --confirm-destroy`. It deletes both VM disks and all cluster data on them, then rebuilds RHEL, host configuration, RKE2, Rancher, and the configured low-footprint Fleet profile.
- Run the full rebuild only when the user explicitly asks. It is designed to execute as one command with no interactive prompts: direct libvirt access is required, host sudo is disabled, Ansible reads the private VM password file, and teardown receives `--yes`.
- If Codex runs a multi-stage operation, use one elevated command invocation for the entire authorized pipeline. Do not ask for separate approval between stages.
- If a stage fails, use the user's existing authorization to diagnose and attempt safe recovery. Stop and report when recovery would exceed that authorization or cannot proceed safely; include useful diagnostics and log paths.
- `local-lab/scripts/deploy-platform-profile.sh` applies and waits for the conservative local Fleet profile. `deploy-mattermost.sh` is an opt-in full application profile and checks that its required paths are enabled.
- The full rebuild command is `local-lab/scripts/rebuild-local-lab.sh --confirm-destroy`. After a completed teardown checkpoint, `--resume` reruns the idempotent provisioning and deployment stages without deleting VM disks. The rebuild only reports success after Fleet, Keycloak pods and ingress, Valkey `PING`, and Rancher's `/ping` endpoint pass.
- During fresh RHEL provisioning, the script watches install DVD and root-disk I/O. It may automatically discard and reinstall a newly created VM once after six minutes with no I/O; it never retries by deleting a pre-existing VM or disk.
- Do not commit or push unless the user asks.
- Do not add or run tests unless the user asks.
