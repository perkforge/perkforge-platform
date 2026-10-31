# Physical pilot: installed OS and key-only access verified

For next-session preparation, start with [tomorrow readiness](../../infrastructure/TOMORROW-READINESS.md).
Its candidate is intentionally non-deployable; no worker boot is requested.
The [interactive architecture/runbook](../../docs/architecture/README.md) shows the
ordered proposed operations separately from this observed pilot checkpoint.

At 2026-10-31 02:13:22 UTC the operator completed a fresh public-key-only SSH
login and password-authenticated sudo check; hostname returned control-1 and the
connection closed normally. RHEL10.2 Minimal Install is installed on the pilot.
At02:14:52 the operator reported workstation pilot shutdown successful; exact
recap and independent resource probes were not supplied.
No further boot, provisioning or package changes are implied by this checkpoint.

## Completed, with operator evidence

- Verified RHEL10.2 x86_64 DVD and root-owned read-only HTTP/TFTP media staging.
- Secure Boot/UEFIOnly/IPv4 PXE reported enabled. Actual physical PXE reached the
  reviewed indefinite GRUB menu, then the interactive installer GUI. This is boot
  acceptance evidence, not complete firmware attestation.
- Isolated packet fixture: four PASS phases; test namespaces confirmed absent.
- Activation PID-check defect fixed; failed-attempt rollback verified and evidence
  retained. Later activation/rearm passed. Session lifetime changed to unlimited
  by explicit operator choice, requiring explicit shutdown and verification.
- Pilot's only identified 256GB SK hynix NVMe was explicitly approved for Windows
  replacement. Installation completed successfully per operator. Layout:600MiB
  EFI,2GiB XFS /boot, remaining approximately235.89GiB XFS root on ordinary LVM;
  no separate home/swap, no disk encryption, non-FIPS local-lab choice.
- Disk-first boot restored, installed console login and hostname verified. Named
  administrator uses password-authenticated sudo; root was disabled in installer.
- Existing passphrase-protected personal SSH key added with standard ssh-copy-id.
  Operator compared full Ed25519 host fingerprint against console before trust.
- The approved temporary password-SSH setup window ended with validated key-only
  policy and SSH reload at02:12:29. Publickey required; password/keyboard-interactive
  and root SSH disabled; PAM retained. Fresh key-only login and sudo passed02:13:22.
  Private-key passphrase and sudo password were entered locally, never collected.
- Workers remain excluded; no worker OS installation or RKE2/Rancher/Flux action.

## Immediate pause checkpoint

Operator reports the reviewed workstation shutdown succeeded at02:14:52. This is
user-reported completion, not independent unit/listener/table inspection. No more
commands tonight. Preserve protected records/logs, held roots, private inputs,
public delivery files and read-only staged media; no cleanup is implied. Before
any future reuse, review current dedicated unit/listener/table state while leaving
original system DNS/libvirt services and tables untouched.

Shutdown retains /run/perkforge-pxe-pilot and /var/log/perkforge-pxe-pilot. Any future
activation must review retained state and current scripts; activate/retry refuse
existing roots deliberately. Do not blindly restage media, reinstall packages,
reuse held names, overwrite evidence or reactivate simply to inspect readiness.
Any further reset/rearm/start requires its own reviewed purpose and authorization.

## Access workflow and unresolved preparation defects

The successful path was standard ssh-copy-id, a separate key-only login, then the
reviewed [standalone hardening file](console/harden-ssh.sh) transferred over the
host-verified SSH connection. It refuses an existing managed drop-in. Do not rerun
it blindly. Keep existing access until any future authentication change is tested.

The earlier HTTP-delivered console enrollment script did **not** finish. Its first
empty-filtered-systemctl exit defect was corrected; a later broad SSH-socket text
guard rejected before mutation. Exact native triggering socket remains unresolved.
ISO sshd.socket is TCP22, while packaged presets enable sshd.service and disable
unmatched units. Native state cannot be inferred from those presets. Do not call
that console route successful, bypass its guard or resume its helper scripts.
Public delivery files remain staged unless later cleanup is explicitly approved;
no private key was published. Twelve console-enrollment fixture tests include full
mocked success/failure flow; they are not real RHEL policy integration evidence.

## Before host/RKE2 preparation

Stop at the OS/access checkpoint. Before workers, implement and rehearse the
[consolidated provisioning proposal](../../infrastructure/PROVISIONING-REDESIGN.md),
with the [retrospective](../../infrastructure/PROVISIONING-RETRO-2026-10-31.md) as context; do not repeat the prolonged manual
console workflow. Inspect and review the physical Ansible inventory
and actual host prerequisites before any separately approved host configuration.
Official RKE2 requirements specify kernel-modules-extra on RHEL10 for nf_conntrack.
The current RKE2 prerequisite task installs only curl/tar/gzip; configure-hosts is
scaffolding. This gap remains unresolved; do not infer readiness from Minimal
Install or working SSH. Python, repositories/subscription registration, time,
NetworkManager/CNI, firewall and pinned RKE2 compatibility still need review.
Source: https://docs.rke2.io/install/requirements . No prerequisite install yet.

## Evidence and local verification

[Chronological journal](../../infrastructure/EXECUTION-JOURNAL.md) distinguishes
user execution from offline tests and pending results. [Activation contract](ACTIVATION-PROPOSAL.md)
contains lifecycle/rollback details. No credentials, personal fingerprints, private
addresses, raw native logs or ignored inventory belong in tracked documentation.

Earlier branch checkpoint:25 PXE,18 infrastructure and8 evidence tests passed,
nine Ansible syntax checks and shell/verification/link/privacy checks passed.
Later rearm tests and16 console tests passed, including four whole hardening-flow
fixtures (success reload, policy/syntax rejection and existing-file preservation).
Fixtures use temporary paths and mocked privilege/service/SELinux operations;
native operator results are separately attributed. Latest documentation diff
check passes. No native packet/service rerun was performed for this update.
