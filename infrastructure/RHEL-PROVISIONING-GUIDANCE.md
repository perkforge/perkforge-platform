# Red Hat guidance leads physical provisioning

Reviewed current official RHEL10 installation documentation and RHEL10.2 release
notes on2026-10-31. These references guide our RHEL10.2 DVD-based, package-mode
installation. They are not a claim that the Debian server adaptations or our
incomplete template have been vendor-validated. No account access, generator
submission, generated Kickstart read, installation or credential choice occurred.

## Vendor workflow → repository plan

| Step | Official reference | Our use / remaining evidence |
|---|---|---|
| Overall install | [Automated workflow](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/automated-installation-workflow) | Prepare Kickstart, make configuration/media accessible, boot and install. Ansible should wrap these ordinary stages, not replace Anaconda with a custom provisioning engine. |
| Network boot | [PXE preparation](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/preparing-a-pxe-installation-source) | Use vendor UEFI files, GRUB and kernel/initrd. Physical pilot reached installer; future per-node Kickstart handoff remains untested. |
| Package source | [Network repositories](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/preparing-network-based-repositories) | Preserve the complete DVD installation tree, including .treeinfo. Candidate records an explicit installation-source URL. Boot runtime location and package source must agree. |
| Create configuration | [Generator/manual-install/export/validation](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/creating-kickstart-files) | Use the supported RHEL10 generator or a hand-written template. Manual anaconda-ks.cfg can contain password information: never read/export it blindly or publish it. Any later approved reuse requires private sanitization before Git/HTTP. |
| Network/accounts/storage | [Command reference](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/kickstart-commands-and-options-reference) | Prefer network device selection, user/sshkey and disk-specific storage directives. Template is still blocked; complete actual per-node inputs and test account/key/sudo behavior. |
| Scripts | [Format and script timing](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/kickstart-script-file-format-reference) | Minimize scripts. Add a small pre-erase check only if standard disk selection cannot enforce our approved target; never use pre-install for protection after partitioning. Post-install changes need their own real tests. |
| Serve/start | [Kickstart delivery](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/adding-the-kickstart-file-to-a-uefi-http-or-pxe-installation-source), [start installation](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/starting-kickstart-installations) | Use inst.ks for configuration, with a valid installation source and complete file. Official example paths/addresses are examples, not our tested boot configuration. No candidate published. |
| Validate/handoff | [Validation limits](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/creating-kickstart-files) | ksvalidator -v RHEL10 checks syntax, not scripts/packages or a successful installation. Require actual install/reboot/key/sudo evidence; report OS/access separately from host/RKE2 readiness. |

## Relevant version changes

The [RHEL10 reference](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/kickstart-commands-and-options-reference)
replaces old timezone options with --utc and timesource, and removes auth/authconfig
and method. Do not copy old RHEL9 examples. The candidate uses explicit network
--device, url --url, timezone --utc and timesource --ntp-server. Keep user/sshkey
standard; no custom key-transfer service. Our EFI600MiB/boot2GiB/XFS-LVM sizes are
operator policy, not a Red Hat universal layout recommendation.

[RHEL10.2 release notes](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html-single/10.2_release_notes/index)
add an RDP Kickstart command; it is unnecessary for this unattended headless path.
They also document a stage2/remote-source issue involving encrypted DNS and a
custom CA: later Kickstart configuration cannot be assumed to fix initial runtime
fetching. Avoid adding that dependency here. bootc is Technology Preview in these
notes and is not a reason to change this package-mode design. The deprecated
inst.gpt option should not enter our boot configuration; use current documented
syntax if a disk-label option is required. No additional image-builder, Satellite
or image-mode workflow is needed for these hosts.

## Boot-server choice

Nginx fills the HTTP installation-source role; it was not the reason provisioning
became interactive. Red Hat's [network overview](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/preparing-a-pxe-installation-source)
prefers UEFI HTTP when supported and notes wider PXE/TFTP compatibility. Keep
UEFI HTTP as a firmware-dependent option, not a switch already tested or approved.
[Satellite provisioning](https://docs.redhat.com/en/documentation/red_hat_satellite/6.17/html/provisioning_hosts/index)
is a larger managed solution; using it for three nodes is not required here.

## Local adaptations, explicitly justified

- **Debian controller:** vendor examples use a RHEL server, dnf/httpd, Kea/TFTP and
  firewalld. Our installed Debian nginx/dnsmasq/systemd/nft implementation serves
  the same file/protocol roles. Do not translate package/service commands blindly
  or claim Red Hat validated that translation. Keep ordinary Ansible tasks.
- **Existing router:** preserve DHCP reservations/allocator. dnsmasq's documented
  [proxy-DHCP mode](https://thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html) supplies
  PXE information while another server allocates addresses. This coexistence
  choice differs from owning the DHCP server in the vendor example; it is not a
  second address pool or new requirement imposed by RHEL.
- **Exposure:** dedicated nonsecret roots, existing interface/client restrictions
  and explicit service stop are our shared-LAN policy. MAC/IP checks are spoofable.
  Signed EFI does not authenticate fetched GRUB/Kickstart; TLS for one later fetch
  does not fix earlier trust. Do not adopt certificate-verification bypasses from
  examples; use proper trust or controlled media if that boundary is unacceptable.
- **Destructive disk choice:** bind each approved plan to a persistent disk ID and
  restrict ignoredisk/clearpart/partitions to it. Rehearse missing/wrong-disk failure.
  Do not create a separate hardware-identity framework or require redundant MAC
  scripting when standard network/disk selection suffices. A minimal extra guard
  is justified only by a demonstrated gap, not by a growing list of booleans.
- **Credentials:** sshkey carries a public key, not a usable sudo password. We
  exclude passwords/hashes/tokens/private keys from served content. Temporary key-only bootstrap design was approved for preparation; actual
  credentials/grants still need scoped execution approval. Vendor examples do not
  authorize new privileges.
- **Lifecycle:** no installer cutoff or manual quarantine dance. Use standard
  systemd ownership/Ansible idempotence plus a compact status/report; preserve
  evidence and prevent accidental reinstallation. No new transaction service,
  credential broker or controller agent is needed.

## Current gate

The default [candidate](../pxe/kickstart/rhel10.ks.j2) always aborts before any
storage/post-install work. RHEL10 validator tooling is now local and a fully
populated synthetic candidate passed; the exact worker file still needs checking.
The operator selected a controlled physical pilot, not mandatory VM rehearsal.
Native package/PAM/install behavior is untested and may need bounded corrections.
Complete exact disk/access inputs and approve one concrete service/install scope.
[Current readiness](TOMORROW-READINESS.md) is authoritative; the earlier
[design](PROVISIONING-REDESIGN.md) remains history, not extra gates.
