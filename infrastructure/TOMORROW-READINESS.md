# Tomorrow's physical provisioning readiness

Offline preparation only, after the operator's2026-10-31 02:14:52 checkpoint.
No new node/workstation services, firewall, credentials, disk writes or VM runs.
**Verdict: not ready for an unattended worker install yet.** Offline checks pass;
a complete RHEL install/reboot/access rehearsal has not been run or authorized.
Do not start an operator-driven debugging session on a worker to close that gap.
Prepared for feature-branch review on docs/physical-execution-journal; publishing
source does not authorize installation. Preserve private media and held evidence.

## Current outcome

Pilot RHEL10.2 disk boot, personal key-only SSH and password-sudo are verified by
operator evidence. Key-only policy was validated/reloaded; temporary password SSH
ended. Operator reports pilot shutdown successful, without a final exact recap
or independent resource probes. Node power-off was suggested, not confirmed.
Workers, host readiness and RKE2/Rancher/Flux remain unperformed. Do not repeat the
manual installation on the working control node to validate a replacement.

## Ready for review

- [Interactive LikeC4 documentation](../docs/architecture/README.md):8 small views,
  numbered operations1–7 and linked local runbook. Model/layout and static build
  pass; no viewer server/browser interaction was started. It documents current
  blocked versus planned/observed state, not install approval.
- [Current Red Hat guidance map](RHEL-PROVISIONING-GUIDANCE.md): vendor workflow leads;
  Debian/router/exposure/disk/credential deviations are explicit. RHEL10 syntax
  and10.2 installer release notes reviewed; no example treated as drop-in validated.
- [Offline Ansible preparation](../pxe/ansible/README.md) is implemented and tested:
  new private plan + blocked Kickstart only, no install/service/apply path. Current
  [PXE layout](../pxe/README.md) supersedes manual pilot as the normal starting point.
- [Concise redesign](PROVISIONING-REDESIGN.md) and [detailed retrospective](PROVISIONING-RETRO-2026-10-31.md).
- [Non-deployable Kickstart candidate](../pxe/kickstart/rhel10.ks.j2): required
  inventory placeholders, unconditional pre-install abort, **no active storage
  mutation**, no passwords/hashes or bootstrap sudo grant. It can be rendered
  privately for review, but is not served, connected to GRUB or approved to run. Public-key/locked-account shape
  does not establish that login/sudo works. [Candidate limitations](../pxe/kickstart/README.md).
- Existing controller contract proposed as plan → approve exact node/disk/exposure/
  credentials → install/verify → stop. One native operator entrypoint, no repeated
  console typing. Install/status/stop still need implementation; current pilot scripts do not
  become that workflow merely because their tests pass.

## Offline checks

| Area | Evidence and limits |
|---|---|
| New normal preparation |4 real-Ansible offline tests pass: unknown/filled blocked drafts, check mode, existing-output preservation and unsafe/secret-input rejection. New preparation playbook syntax passes. |
| PXE tests | 32 tests passed at the prior full-suite checkpoint, including3 candidate checks; includes original rendering/packet-codec/gating mocks, retry menu hashes, shutdown normal/already-stopped/mismatch/residual cases, and expanded rearm task-body flows. No real namespace/service/firewall operation. |
| Rearm positive flows | Real Ansible task body with all native command calls mocked and root/served paths adapted to temporary files: active, expired-absent and expired-failed success; guard mismatch stops before recreation. New identity/lifetime ledger and old evidence preservation asserted. Outer rescue/native systemd races are not proven by this fixture. |
| SSH regression tests |17 pass: explicit old empty-filtered-systemctl errexit reproduction; corrected empty-match handling; enabled socket rejection; description-only false-positive reproduction; full mocked enrollment success/failure and successful/rejected hardening flows. This does not prove the failed native console-enrollment route. |
| Infrastructure |18 tests pass; source gating/server-agent separation and Rancher fixtures, not actual node installation. |
| Release/evidence |10 offline release-workflow checks pass; no remote GitHub/cluster calls. |
| Syntax |10 Ansible playbooks,6 shell scripts and12 Python files pass parser checks. |
| Kickstart candidate |4 current static specimen tests pass after vendor-guidance integration; required inputs, unconditional abort, no active disk commands/secrets and intended package list. No RHEL parser or boot execution. |

Source-level socket conclusion: filtered empty systemctl results explain a concrete
silent-exit defect; broad matching of SSH text in descriptions/names is overbroad.
ISO sshd.socket is TCP22; vendor presets enable sshd.service and disable unmatched
units. Exact native triggering socket remains unknown. Do not bypass or polish the
HTTP console-enrollment path into a worker dependency; keep it historical until
retired after replacement. Successful access used standard SSH recovery instead.

Media directory listing confirms ISO RPMs for openssh-server, sudo, python3 and
kernel-modules-extra. This proves file presence only, not package dependency,
minimal-environment group, kernel-match, repository or host-readiness validation.

## Not ready / decisions

1. **Credential bootstrap:** approve a protected way to retain human password-sudo
   without serving its password/hash. Evaluate explicitly temporary key-only
   bootstrap passwordless sudo with removal after verified human access, versus
   controlled private media or one private console-password step. No privilege
   mode, new key or password has been selected/generated by this preparation.
2. **Worker disks:** complete serial/stable ID/capacity and each erasure/layout
   approval. Missing values remain blocking; control-node approval is not reusable.
3. **Installation trust:** scoped home-LAN HTTP/TFTP is not authenticated by Secure
   Boot; choose accepted trust boundary or physical-media fallback. Do not claim
   HTTPS Kickstart fixes earlier unauthenticated GRUB configuration.
4. **Implementation/rehearsal:** finish standard disk targeting (only necessary extra checks), install-time SSH policy,
   host identity display/trust, first-boot credential transition, safe one-shot
   install/disarm and resumable lifecycle before a worker install.
5. **Host preparation:** current configure-hosts is scaffolding. Verify Python,
   entitlement/repositories, DNS/time, SELinux, NetworkManager/CNI/firewall, capacity,
   RHEL/RKE2 compatibility and kernel-modules-extra/nf_conntrack. Working SSH is not
   readiness; no RKE2 install is authorized by the OS checkpoint.

## Smallest next engineering batch

Resolve the credential/trust choices, complete private disk metadata, then finish
the Ansible-owned Kickstart install/lifecycle path using the new preparation and its compact result contract. Do
this before asking the operator to boot a worker. Confirm native execution access
first: this assistant's restricted projection cannot perform host privileged work.
If native operator execution is required, provide one tested short invocation,
not a stream of manual commands. Do not bypass the environment restrictions.

Missing validation tooling: command lookup and Python import check found neither
ksvalidator nor pykickstart. No installation/download attempted. Obtain approved
RHEL10-compatible validation tooling before claiming syntax validation; static
specimen tests are not its substitute.

QEMU, qemu-img and virt-install binaries are present. Their presence is not
permission or proof of a working rehearsal environment. The next real test needs
separate approval for a disposable isolated UEFI installer fixture using only
verified media and new disposable disks, no LAN uplink, no preserved trial changes,
and no supported VM-cluster workflow. Rehearse complete install/reboot/key/sudo,
wrong-disk zero-write rejection, failed postinstall, controller loss, restart/resume,
second boot and repeated stop. Follow with one separately approved physical worker
pilot. No new operator commands or physical experiments are requested tonight.

The parent's1–2hour first-worker OS/access planning allowance is unmeasured, not
an installation benchmark or readiness claim. Give a fresh ready/not-ready verdict
before asking the operator to begin; do not treat tomorrow's intent as live install
authorization. No further operator commands are needed tonight.

The operator is considering control-1 again, not approving its wipe. Current
working OS/access and existing shutdown/recovery entrypoint are preserved. UEFI
HTTP boot is a vendor-preferred option only if firmware support is demonstrated;
no switch from the proven pilot TFTP route or DHCP ownership change occurred.

Operator accepts manual power/BIOS/network-boot steps and trusted physical identity
or host-fingerprint checks when needed. Normal provisioning must otherwise be
workstation-operated: no node command transcription or interactive installer.
This future operator boundary does not authorize changing firmware or booting now.
