# Fresh local RKE2 trial

Preparation only. Do not run the action commands until the exact teardown and
security-sensitive initialization are approved. `dev` is unchanged.

Rancher remains the intended cluster-management UI for platform engineers.
Omitting it here is temporary: the resource-constrained local VM trial first
measures the minimal RKE2/Big Bang/Flux stack. Flux owns GitOps for this new
stack; Fleet must not reconcile its resources. Later Rancher management
integration is a separate reviewed stage, with its own server/agent resource
budget, capacity measurements and security checks. That cost is not included in
the initial tiny-trial budget. This preparation neither installs Rancher nor
changes the planned architecture or `dev` configuration.

## Scope to approve

Verified read-only on 2026-10-28: both VMs have one qcow2 disk and no libvirt
snapshots. Recheck immediately before destruction:

| VM | Disk to delete | Virtual capacity |
| --- | --- | --- |
| cks-control | `/home/corey/src/perkforge-platform/images/cks-control.qcow2` | 30 GiB |
| cks-worker | `/home/corey/src/perkforge-platform/images/cks-worker.qcow2` | 100 GiB |

Deleting these disks discards etcd, all Kubernetes objects, and VM application
storage: Nextcloud, Keycloak, GitLab/Valkey and OpenBao, including recovery-relevant
state stored inside the guests. Corey selected fresh data with no migration.
That decision does not authorize running teardown yet.

Preserve the workstation repositories, ISO, `.secrets` contents, encrypted backups,
libvirt default network and DHCP reservations. The existing teardown discovers
attached disks; approve only if its preview still lists exactly these two paths.
If another disk or snapshot appears, stop and review. Do not run the old
`rebuild-local-lab.sh`: it installs Rancher/Fleet.

## Staged commands

Run from the reviewed feature checkout. No commands below have been executed
except `plan` and offline validation.

1. **Read-only preview** (direct libvirt access required):

   ```sh
   local-lab-big-bang/provision/prepare.sh plan
   LOCAL_LAB_USE_SUDO=never local-lab/scripts/teardown-vms.sh
   ```

2. **After specific deletion approval**, remove only the approved VMs/disks:

   ```sh
   LOCAL_LAB_USE_SUDO=never local-lab/scripts/teardown-vms.sh --apply --yes
   ```

   Teardown requests graceful shutdown and refuses to proceed if it cannot finish;
   no force-off recovery is authorized. Recheck exact paths before this command.

3. **After initialization approval**, choose a new, unused trial output directory:

   ```sh
   export LOCAL_TRIAL_STATE=/home/corey/src/perkforge-platform/.secrets/bigbang-local-trial-01
   export LOCAL_TRIAL_APPROVED=yes
   local-lab-big-bang/provision/prepare.sh rhel
   local-lab-big-bang/provision/prepare.sh rke2
   ```

   The flag is an execution guard, not a substitute for human approval. RHEL uses
   the existing SSH key and console password by reference; missing credentials
   fail rather than generating replacements. New Kickstart/known-hosts and RKE2
   kubeconfig/client outputs go only into the new trial directory. Keep that
   directory private; it contains credentials. A stalled fresh install is retained
   for diagnosis, without automatic deletion/retry. Do not rerun `rhel` against a
   partial trial; inspect it first. `rke2` can rerun against that trial's state.

The shared installer pins RKE2 `v1.36.5+rke2r1` and checks the existing RHEL 10.2
ISO checksum. It still downloads the upstream RKE2 installer script over HTTPS;
review that script/provenance before live execution. Existing host configuration
includes SELinux/network/firewall settings and privileged guest access. These are
part of the pending initialization approval, not a claim of security readiness.

## Stop before applications

The Ansible entrypoint imports host configuration and RKE2 only. RKE2 brings its
bundled system components; it does not mean zero controllers. No Rancher, Fleet,
Flux, Big Bang, storage provisioner or applications are installed by this path.
The shared RKE2 installer fetches the new administrative kubeconfig and join token;
review their handling before initialization. It does not update workstation
`~/.kube/config` or preserve the old cluster identity inside the deleted guests.

After bare nodes are Ready, collect fresh node/system requests and actual memory,
verify absence of Rancher/Fleet/Flux and compare with
[`LOCAL-TINY.md`](../preflight/LOCAL-TINY.md). Approve each later Flux/storage,
DB/Keycloak, OpenBao, Headlamp and tenant stage separately. The published defaults
remain paused and are not the Flux-only stage configuration. DNS/TLS, identity,
secret/recovery setup, storage pin/render and tenant boundaries remain gates.
Runtime memory peaks and rollout headroom remain unvalidated; a fitting request
budget does not prove this two-node trial will operate reliably.

## Record hurdles during the approved trial

Follow the existing timestamped local evidence convention. Use a new UTC run
directory under the operational checkout's ignored `local-lab/evidence/`, for
example `bigbang-trial/bigbang-trial-20261028T190000Z/`; create it only when the
trial is approved, with directory mode 0700 and files 0600 (`umask 077`). Verify
`git check-ignore` before collecting anything. Never overwrite an earlier run.

Keep `timeline.md` with one row per attempt:

| UTC start/end | Stage / attempt | Safe command label / exit | Symptom | Confirmed cause / hypothesis | Fix | Verification / evidence |
| --- | --- | --- | --- | --- | --- | --- |

Record exact non-secret revisions, selected target and resource sizing. Preserve
failed-attempt files and append a new attempt for each retry; do not rewrite a
failure as success. A cause stays a hypothesis until a check supports it. Record
the exit status even when a command stops early; never let `tee` hide a failure.

Capture only reviewed, relevant output: VM state and disk/installer-I/O counters;
node capacity/requests/conditions; selected Pod status and restart/termination
reasons; namespace-scoped warning events; Flux reconciliation status/events
once Flux exists. For a failed service, collect bounded, time-scoped journal or
container logs after checking that service's output for credentials. Capture
before changing or retrying the failed stage, then repeat the same verification.
Do not dump complete Pod specs, Helm values/history, ConfigMaps, manifests or
unfiltered cluster reports just to debug readiness.

Do not enable `set -x`, Ansible debug verbosity, global `ANSIBLE_LOG_PATH` or
automatic all-output recording. The existing token/kubeconfig tasks use
`no_log`; preserve it. Never record passwords, join/unseal/recovery tokens,
kubeconfig contents, Secret contents, private keys, credential environment or
sensitive Ansible results. Application logs and event messages can contain
sensitive values too: review/filter before retaining excerpts, and record an
omission if safe capture is uncertain. Raw local evidence is not automatically
safe to publish. Only an authorized, manually sanitized hurdle summary belongs
in Git or a PR. No operational evidence has been collected by these offline tests.
