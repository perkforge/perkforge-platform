# PXE → RHEL: staged preparation

These are **examples, not a deployable PXE service**. No DHCP/TFTP/HTTP service,
bootloader, MAC allowlist or automatic renderer is installed here. The physical
nodes still run Windows. Do not boot the installer or change the LAN tonight.

## Decisions before booting one node

| Required input | Current status / stop condition |
|---|---|
| Target | Start with control-1 only; workers stay out of the boot allowlist |
| Firmware/NIC | Confirm exact Lenovo M920q model, UEFI mode, wired boot NIC/MAC, firmware and Secure Boot trust |
| Windows | Decide whether to preserve/recover Windows; verify backup and BitLocker recovery material outside the node before disk approval |
| RHEL | Select exact RHEL 9 minor release and x86_64 media; review RKE2/Rancher support matrix, hardware drivers, entitlement and EULA |
| Media/source | Authorized Red Hat download; verify published checksum; extract full DVD tree including hidden `.treeinfo`, BaseOS/AppStream and `images/pxeboot` |
| Network | Select provisioning server/interface/address, serving root, DNS/gateway and isolated provisioning segment or reviewed LAN coexistence |
| Storage | Record disk model, serial/WWN, size and Windows partitions; choose one target and layout explicitly; no disk default |
| SSH | Select administrator, public key and sudo policy; private key stays on workstation with encrypted backup |

The boot ISO alone is not the full package tree. Installation media does not
replace entitlement and working post-install repositories. Do not embed Red Hat
credentials, activation keys or agreement acceptance in served files.

## Boot chain and household DHCP

Firmware → DHCP address and architecture-specific boot information → trusted
UEFI loader (or separately selected BIOS loader) → boot menu → matching RHEL
kernel/initrd → Anaconda `inst.repo` tree and optional per-host `inst.ks` → reviewed
OS installation. `boot.ipxe.example` begins **after iPXE is already running**; it
does not arrange firmware chainloading or DHCP. Avoid chainloading iPXE back into
itself: its second DHCP request must resolve to the script rather than its binary.

Keep AT&T as the household DHCP owner. Reservations do not supply PXE boot
information. Verify the actual gateway model's supported settings; do not assume
options 66/67 or proxy-DHCP work. Prefer an isolated wired provisioning segment
with explicitly approved DHCP ownership when the gateway cannot supply a safe
boot path. Proxy-DHCP on the existing LAN is a separate design/approval decision,
not permission to start another address-allocating DHCP server.

Before serving anything, review exact interface bindings for DHCP/proxy-DHCP,
TFTP and HTTP(S), firewall rules and routing. Bind only to the selected provisioning
interface/address; serve only a dedicated nonsecret directory, never the checkout,
home or `.secrets`. Review UDP 67/68, TFTP 69 plus transfer traffic and HTTP(S)
ports for the selected design; do not open them broadly. Allowlist only the chosen
boot MAC in DHCP/boot menus and restrict per-host file access. Unknown clients
must receive no installer entry. A MAC-derived filename is identification, not
authentication; MAC allowlisting does not make HTTP confidential or tamper-proof.

For UEFI/Secure Boot, prefer the Red Hat documented signed shim/GRUB chain from
the selected release. An arbitrary `ipxe.efi` is not automatically trusted. If iPXE
is selected, review its signed binary and Linux handoff requirements against the
actual firmware trust database; do not disable Secure Boot as a workaround.
Legacy BIOS needs a different loader and separate review.

## Windows and the first boot (later approval)

Lenovo documents **F12** during startup for the M920q boot menu. With local
keyboard/display attached, use its one-time UEFI network/PXE entry for the wired
NIC before Windows Boot Manager. Do not change persistent boot order. If that
entry is absent, stop to inspect firmware network-stack/PXE settings and NIC
support; firmware changes require their own approval. Exact menu wording depends
on installed firmware. A failed network boot can return to Windows; this is not a
Windows backup and ceases to be a recovery path after overwriting its disk.

1. Approve only the boot-service/network scope and one named node. Verify media,
   allowlist, loader trust and nonsecret served content before powering/booting it.
2. Boot the installer and inspect network identity and all disks at the console.
   Match the reserved address to the correct NIC. Multi-NIC systems need an
   explicitly reviewed boot interface; `ip=dhcp`/`--device=link` are examples only.
3. **Stop before accepting storage changes / Begin Installation.** Obtain separate
   approval identifying node, disk serial and loss of Windows/data. Booting PXE
   does not authorize erasing a disk. Keep other disks disconnected if feasible.
4. For the first node, use the graphical interactive installer with reviewed media.
   The partial `rhel.ks.j2` is optional, must be rendered/reviewed for one host and
   validated for the selected RHEL 9 release with `ksvalidator -v RHEL9` when the
   matching tool is available. It has no storage automation or usable login setup;
   do not interpret it as unattended-ready. Text mode has storage limitations.
5. At the console configure the named admin, install only its reviewed **public**
   SSH key and establish the approved sudo policy. No private key, password/hash,
   join token or registry/subscription credential may enter HTTP Kickstart. Root
   stays locked; verify sshd/public-key authentication and host-key fingerprint
   before ending console access. The template halts after installation.
6. Remove the node's install entry before the next boot. Select local RHEL at the
   console. Verify OS/repositories/Python, SELinux enforcing, SSH/become, routing,
   DNS/time and storage under separate connection authorization. Then stop and
   review the [infrastructure handoff](../infrastructure/PREPARATION.md).

The iPXE timeout exits to firmware; whether firmware then selects Windows/local
disk depends on firmware boot order. `exit` is not a guaranteed local-disk boot.
The shell returns to the menu; no entry should silently start installation.

## Sources and validation limits

Reviewed 2026-10-30: Red Hat RHEL 9 [PXE server/UEFI chain](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/automatically_installing_rhel/preparing-for-a-network-install_rhel-installer),
[network repository tree](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/interactively_installing_rhel_over_the_network/preparing-network-based-repositories_rhel-installer),
[Kickstart reference](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/automatically_installing_rhel/kickstart-commands-and-options-reference_rhel-installer),
[text-mode/storage limits](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/interactively_installing_rhel_over_the_network/customizing-the-system-in-the-installer_rhel-installer),
[iPXE Secure Boot](https://ipxe.org/secboot), and Lenovo's
[M920q startup instructions](https://support.lenovo.com/us/en/products/desktops-and-all-in-ones/thinkcentre-m-series-desktops/thinkcentre-m920q/solutions/ht500209).
No physical boot, firmware trust, network coexistence, Kickstart installation,
Windows recovery or hardware compatibility has been tested. These are tomorrow's
explicit checkpoints, not inferred success from offline tests.
