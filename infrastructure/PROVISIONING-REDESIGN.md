# Physical provisioning: boot, install, verify

> Earlier design proposal, retained as review history. The agreed active approach
> is now the [controlled physical worker pilot](TOMORROW-READINESS.md), without a
> mandatory full VM rehearsal or general session/recovery framework. Requirements
> below describe that earlier proposal; they are not additional current gates.


**Proposal only, 2026-10-31.** No implementation or live approval follows from this
file. Tonight installed one RHEL10.2 host and verified key-only SSH/sudo, but the
operator had to help build and debug the installer workflow. That is not the
repeatable provisioning experience we need. See the [retrospective](PROVISIONING-RETRO-2026-10-31.md)
and [actual checkpoint](../pxe/pilot/HANDOFF.md).

## Recommended path

Follow Red Hat's [automated workflow and guidance map](RHEL-PROVISIONING-GUIDANCE.md)
first, with only the documented Debian/router/credential adaptations. Current
RHEL10 guidance and10.2 release notes were reviewed; no vendor example is treated
as a tested drop-in. Use standard RHEL Kickstart, the verified DVD and existing narrowly scoped
proxy-dnsmasq/nginx design. Router DHCP remains authoritative. One Ansible-owned
workflow should prepare the workstation, render a per-node install plan, arm only
the approved node/disk, wait for installation, verify access and stop its services.
Keep Python for verification. Do not add a provisioning service, database, agent
or replacement CLI framework.

RHEL documents fully automated PXE installation using a complete Kickstart and
`inst.ks=` in GRUB, and installation-time `sshkey` enrollment. Our current
[GRUB template](../pxe/pilot/templates/grub.cfg.j2) has no `inst.ks` and intentionally
requires manual installer selection. It is a pilot, not this proposed workflow.
Sources: [automated boot](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/starting-kickstart-installations),
[Kickstart command reference](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/kickstart-commands-and-options-reference).

| Approach | Fit and limitation |
|---|---|
| PXE + Kickstart | Preferred repeatable LAN path; reuses proven boot/media. Requires approved temporary services and an explicit trust assumption for LAN-served boot configuration. |
| DVD USB + per-node Kickstart USB/local volume | Practical fallback for three machines if proxy/firmware or LAN trust is troublesome. Same tested install policy; avoids workstation boot services, requires separate suitable media and physical handling. Never reuse the private-key backup USB. |
| Interactive installer | Recovery/discovery only; not the worker-install default. |

Red Hat supports local-volume Kickstart via `inst.ks=hd:UUID=...` or `OEMDRV` with
`ks.cfg`. OEMDRV supplies configuration, not necessarily the complete installation
source; use verified DVD media for a network-independent fallback. USB creation
is destructive and would need its own exact-device approval.
[Local-media guidance](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/semi-automated-installations-making-kickstart-files-available-to-the-rhel-installer).

## Operator journey and approval contract

Offline [Ansible preparation](../pxe/ansible/README.md) is now implemented; it
writes only a blocked draft. Future installation entrypoint contract, **not
commands/files available today**: one Ansible
playbook with `plan`, `install`, `status` and `stop` actions. Existing short shell
entrypoints may only dispatch Ansible. Normal path: three workstation invocations
(plan, install, stop; install includes verification), one physical network-boot selection, no hand-typed
node commands or installer GUI. Status is optional, not another required ritual. Human power/BIOS/network-boot actions are acceptable,
as are trusted physical identity/fingerprint checks when needed. Everything else
in the normal path is workstation-operated; no node command transcription.

1. **Plan:** validate known inventory/media/dependencies; render sanitized summary:
   node, expected MAC, disk serial/stable ID/model/capacity, partition layout,
   hostname/network/time, account/public-key fingerprint, credential mode,
   service/interface/ports and reboot/cleanup behavior. Missing disk identity or
   credential choice blocks arming. First-time discovery may need a separate
   non-destructive boot; do not disguise unknown hardware as an unattended plan.
2. **Approve one concrete install batch:** named node plus exact disk erasure,
   temporary workstation network exposure, stated credential/bootstrap privileges
   and reboot. Approval is bound to that rendered plan. Re-ask only if these
   consequential inputs change, not for every parser, directory or GUI field.
3. **Install:** prepare/start only owned resources; operator selects network boot
   once. Kickstart installs the agreed layout/packages/accounts/key-only SSH,
   then disk-boots. Controller reports progress and validates host identity,
   key login, sudo, OS/storage/network/time and readiness. A failure prints one
   concise reason, saved-log path and safe next action, without requiring log
   transcription. Never print success just because Ansible tasks completed.
4. **Finish:** preserve the report, disarm reinstall and verify owned listeners/
   services/rules removed. If verification fails, retain recovery access/evidence
   and report incomplete; do not wipe or blindly restart the installation.

Network service changes, disk erasure, credentials and later RKE2 remain genuine
approval boundaries. Offline review/tests and authorized implementation details
should not become repeated permission prompts. Explain workstation versus node
commands explicitly; the normal user should only operate the workstation entrypoint. Verify native controller privileges before scheduling the live batch; if the assistant
cannot execute there, supply one tested native invocation rather than delegating
a sequence of manual commands. Do not bypass the restricted execution environment.

## Installation policy and credentials

Per-node private inventory is the source for DHCP reservation/MAC-selected NIC,
hostname, DNS/time, disk identity, layout, public key and approval. Prefer current
router reservations; do not invent static gateways or change household DHCP.
Static installer and installed-OS settings, if selected, must be rendered together.
Keep workers unarmed until their own plans are approved.

Use standard persistent-disk selection with `ignoredisk`, disk-restricted
`clearpart` and partitions bound to the approved disk. Never unrestricted clear-all
or assume nvme0n1/sda is persistent identity. Missing identity blocks the plan;
rehearse absent/wrong-disk failure. Add a small `%pre --erroronfail` check only if
the vendor directives cannot enforce a demonstrated part of the approved plan;
do not build redundant NIC/identity scripts. `%pre-install` is too late for an
erase check because partitioning has happened. Candidate's unconditional abort
is a temporary non-deployment gate, not the proposed production preflight.
Retain selected EFI600MiB + /boot2GiB + remaining XFS/LVM root, no home/swap and
non-FIPS/unencrypted policy only for explicitly selected local targets. These
sizes are operator choices, not a universal vendor layout. No inferred worker disks.
[Vendor mapping and timing](RHEL-PROVISIONING-GUIDANCE.md).

Enroll approved public keys and key-only SSH **before first boot**, with correct
ownership/SELinux labels; keep root SSH and password/keyboard-interactive SSH off.
No ssh-copy-id/password bridge should be needed for workers. Do not put private
keys, passwords **or password hashes**, registration credentials, tokens or recovery
material in HTTP/TFTP, kernel arguments or logs. Sanitizing a Kickstart path/name
does not remove credentials inside it. Do not read/copy `/root/anaconda-ks.cfg`
blindly: Red Hat warns it contains account/password information.
[Generated Kickstart warning](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/creating-kickstart-files).

**Resolve before implementation:** password-authenticated human sudo plus completely
unattended installation needs a protected secret path. Recommended network option
to evaluate: dedicated key-only bootstrap identity with explicitly approved,
short-lived passwordless sudo; Ansible then provisions the human password from a
private encrypted controller source over verified SSH, verifies human key/sudo,
and removes bootstrap authorization. This temporarily gives that bootstrap key
root-equivalent power; it is a new decision, not already approved. Prove actual
RHEL account-lock/PAM/key behavior in rehearsal; do not assume omitting a password
produces a usable account. Root stays locked; human password-sudo remains the final
policy. Alternative: per-node credential-bearing Kickstart on controlled physical
media, or one private console password-entry step. No HTTP password-hash shortcut.
Reuse existing [credential custody/recovery policy](CREDENTIALS.md), not a new secret
broker; recovery must work after losing both laptop and cluster.

## Lifecycle, trust and readiness

Keep Secure Boot enabled and use verified vendor EFI/kernel components. MAC/IP
allowlisting is not authentication; signed EFI does not authenticate fetched GRUB
configuration or Kickstart. Existing HTTP/TFTP therefore assumes a trusted scoped
installation LAN. State that limitation in the plan; for a stronger threat model,
choose controlled physical media or separately design authenticated boot/config
transport. HTTPS Kickstart alone cannot repair a tampered earlier GRUB handoff.
Do not disable Secure Boot/firewalls or skip certificate checks to make boot work.

No mid-install runtime cutoff. Services are session-owned, not enabled at boot;
explicit stop/verification and a visible unfinished-session warning are required.
Do not stop on loss of controller polling while the installer still needs media.
Use standard systemd unit ownership and Ansible idempotence with retained attempt
logs/status; do not build another transaction engine or require a new set of
review booleans. Resume matching owned resources, reject changed ones with a
concise reason; already-stopped cleanup succeeds safely. Recoverable failures
must not require manual held-directory renaming. Withdraw the approved install
boot offer and return to disk boot so a reboot cannot accidentally repeat an
erase. Reinstall needs a new explicit plan. Test these normal lifecycle cases.

Finish at **RHEL + verified managed access + host-readiness report**, not RKE2.
Implement missing host preparation in Ansible: Python/sudo, repositories/entitlement,
SELinux, time/DNS, NetworkManager/CNI and firewall policy, capacity and required
packages. RHEL10 `kernel-modules-extra`/nf_conntrack is a known gap in current
[RKE2 tasks](ansible/tasks/rke2-node.yml). Check exact RHEL/RKE2 version support;
working SSH is not compatibility certification. RKE2 server/agent tokens, Rancher
and Flux remain separately authorized stages. [RKE2 requirements](https://docs.rke2.io/install/requirements).

## Delivery and acceptance before workers

One engineer owns the Ansible install contract, docs and end-to-end evidence;
the operator owns hardware/data-loss and credential decisions. Priorities:

1. Settle bootstrap credential/trust decisions; complete nonsecret disk inventory.
2. Implement one RHEL10 Kickstart template and consolidated Ansible lifecycle;
   reuse verified media/templates/packet checks, retire parallel manual helpers.
3. Validate syntax with `ksvalidator -v RHEL10`; rehearse complete install/reboot/
   first key login/sudo/hardening/removal/stop and failure/resume paths using the
   exact rendered artifacts. Validator does not test scripts/packages or guarantee
   installation. [Validation limits](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/creating-kickstart-files).
4. With separate authorization, use disposable UEFI test disks/VM solely as an
   installer rehearsal, never a supported VM cluster or a mutation of the preserved
   trial. Then one physical worker pilot; physical firmware/router acceptance still
   needs its own evidence. A future control-1 reinstall is only a candidate, not
   approved; preserve the working node unless a new exact-disk/data-loss plan is
   explicitly authorized after rehearsal.

Acceptance: no node command transcription, no password SSH bridge, correct disk
only (wrong identity causes zero writes), unknown client denied, realistic success
plus every destructive-boundary failure tested, no secrets served/logged, host
fingerprint displayed automatically at the physical console and compared through
that trusted channel (not an unauthenticated HTTP callback), valid key/sudo
access, no boot-loop reinstall, resume/stop repeatably safe, original workstation
services unchanged, and a compact sanitized command/result report. Do not promise
a fixed duration before measuring a successful rehearsal.

## Decisions needed, once

Choose the protected sudo-password/bootstrap mode and installation-LAN trust
boundary; obtain separate USB media only if choosing that fallback. Complete each
worker's disk serial/stable ID and approve its layout/data loss. Confirm that
“done” for this entrypoint means OS plus access/readiness, with RKE2 separately
approved. These decisions precede implementation; no further console experiments
or control-node reinstall are requested by this proposal.
