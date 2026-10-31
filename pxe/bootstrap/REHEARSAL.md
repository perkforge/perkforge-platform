> DEFERRED / OPTIONAL. Not an active worker-1 prerequisite or execution request.
> The custom runner is incomplete; preserve code/evidence without running it.
> Active strategy: [controlled physical pilot](../../infrastructure/TOMORROW-READINESS.md).
> Earlier proposal below remains review history, not current gates.

# Isolated installer rehearsal — proposed batch, not executed

**Not ready to execute.** Install/session/reboot/disarm integration and RHEL10 validator remain missing.
Exact-disk/initial-policy adapters and controller credential handoff now have
offline fixtures; real storage/account/SSH/sudo behavior has not been exercised. No ready-to-run command is claimed.
This is a disposable installer test, not restored support for VM clusters.

## Requested future scope

- One new UEFI x86_64 VM,4 vCPU,8GiB RAM; fresh64GiB sparse target and1GiB
  canary disk. Reserve up to65GiB actual disk growth plus evidence; preflight free
  space/host memory and available OVMF Secure Boot firmware before approval.
- Read verified RHEL10.2 DVD; no old trial disks/VMs or physical nodes involved.
- Private isolated virtual network with **no uplink, bridge to LAN, NAT or default
  route**. Temporary DHCP/proxyDHCP,TFTP,HTTP only inside isolated network. Exact
  transport/controller attachment must be reviewed before execution; no libvirt
  default network or host firewall changes. No package installation implicit.
- Synthetic MAC/hostname/disk identities. New disposable bootstrap/test-human keys
  and test password needed under separate explicit credential-generation approval;
  private values stay protected, never served/logged/arguments. No real user keys,
  passwords, subscription credentials or private inventory reused.
- Exercise install, disk boot, trusted host fingerprint, bootstrap key/root sudo,
  human key/password-sudo handoff, bootstrap revocation and retained human access.
  Then wrong-disk zero-write rejection, second boot, interrupted postinstall,
  controller-loss/resume and repeated stop. Canary hash unchanged in every case.
- Evidence: source/tool/media/input/output identities, bounded sanitized logs,
  account/grant ledger (including failures), assertions and final residual report.
- Cleanup only resources created by this run, matched by recorded identities;
  confirm processes/network/VM absent. Retain evidence and failed disks until
  reviewed; disk deletion is part of the separately approved cleanup scope.

## Time and gate

Planning allowance2–3hours after implementation, not a measured duration. The operator removed the earlier hard stop; this does not authorize execution.
The actual batch still needs exact resource names/paths/commands, execution access
and explicit approval.
No physical worker boot until these tests pass and its disk/erase/trust plan is
separately approved. Merely generating a blocked draft is not rehearsal success.
