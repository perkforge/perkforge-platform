# Worker-1 controlled pilot readiness

**Strategy agreed: standard Kickstart + proven PXE serving + short Ansible access
handoff. Full VM rehearsal is optional, not a launch gate.** The first physical
worker is the controlled pilot; accept possible reinstall and bounded corrections.
No node/service/wipe/credential action has been approved yet. All physical nodes
are off per operator report; control-1 remains intact. RKE2/Rancher are excluded.

## Actual evidence

- The earlier physical pilot booted this RHEL10.2 media through the reviewed
  PXE/TFTP/nginx path. Namespace packet checks passed previously. That establishes
  transport evidence, not unattended installation on worker-1.
- The verified DVD SHA256 is recorded in the execution journal. Approved local
  pykickstart3.78 matched its published archive hash and the fully populated
  synthetic candidate passed `ksvalidator -v RHEL10`, exit0. Actual worker-specific
  file still needs its own validation after required inputs are supplied.
- Storage/initial-policy/access components have offline success/failure fixtures.
  Native Anaconda/PAM/package/first-boot behavior is still untested. Do not turn
  those fixture counts into a successful worker install claim.
- Current protected draft: `pxe/local/worker-1/plan.md`; input: `inputs.yml` in that
  directory; original renders/evidence remain under `runs/`. Private values are
  not in this tracked checklist. Source generation remains unconditionally blocked.

## Pilot approval

1. Inspect worker-1's actual disk model, persistent ID, serial and exact capacity
   read-only. Review the proposed EFI/boot/root layout and Windows data loss.
   Control-1's earlier wipe approval cannot be reused.
2. Complete the worker input: disk/layout, hostname/time/network choices and
   public-key/account references. Dedicated temporary key-only root-equivalent
   bootstrap design is approved for preparation; real key generation/access is not.
3. Render the target-specific installation file for review; run the RHEL10 parser,
   script syntax/disk-guard/access fixtures and final source/media checks. Keep the
   generic default draft blocked. No silent conversion of a BLOCKED file to live.
4. Retarget proven service templates to worker-1 only. Review exact binding/MAC/IP,
   nonsecret serving roots, native existing-service/port state and scoped shutdown.
   Then approve one concrete batch covering service exposure, exact-disk erase,
   credential actions and any required RHEL agreement—not each routine subcommand.

## Installation and access

Operator handles approved power/BIOS/network boot. Kickstart performs the reviewed
install and initial public-key/key-only SSH policy. Keep a small workstation
checkpoint: compare the physical console host fingerprint, then enter the human
password privately into the short Ansible handoff. No password SSH bridge, secret
provider, serial-trust automation or root-secret HTTP artifact is needed.

Verify a fresh human key login/password-required sudo and remove temporary
bootstrap authorization. Keep console/recovery access if a check fails. Correct
bounded defects within the approved target; stop for unexpected storage, credential
exposure or broader network/security changes. Do not improvise an erase/retry.

## Finish

Restore/confirm local-disk boot so another PXE boot cannot repeat installation.
Explicitly stop only the reviewed temporary session and verify scoped absence;
preserve media/logs/failed-state evidence. Installation/SSH success is not RKE2
readiness. No automatic mid-install service cutoff.

Parked: `pxe/ansible/rehearsal.yml` and its custom VM/session/recovery machinery.
It is incomplete and not an active prerequisite. Its first full mock failed in
memory parsing before resource creation; preserve that evidence, do not present
it as a passed VM rehearsal. Broad deletion/refactoring is deferred. After worker-1
RHEL/access succeeds, review PXE/Kickstart/Ansible responsibility boundaries and
consolidate the final tested runbook/current-state C4.

## Private-input recovery follow-up

Worker inputs/renders are protected local files with source/input/output hashes.
Encrypted backup and restore/regeneration of these new inputs are **not verified**.
Earlier SSH-key backup evidence does not prove inventory recovery. No secret
migration, backup, VM or credential operation was performed by preparation.
