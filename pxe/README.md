# Physical RHEL 10.2 PXE pilot

Selected target: **control-1 only**, RHEL10.2 x86_64 DVD, interactive non-FIPS
installation. Workers remain excluded. The pilot node is in firmware setup;
**no physical network boot or installation has happened**.

The operator verified/staged the media, completed isolated packet tests, and
successfully activated the bounded workstation pilot at23:53UTC after fixing a
PID-check quoting bug. A pause/shutdown was requested before supper; consult
[the current handoff](pilot/HANDOFF.md) and [chronological evidence](../infrastructure/EXECUTION-JOURNAL.md)
for its confirmed outcome. Historical RHEL9/iPXE/partial Kickstart examples were
removed; do not use them.

## Completed preparation and remaining limits

| Item | Evidence / remaining stop |
|---|---|
| Media | DVD SHA256 matched Red Hat's published value; dedicated full-tree staging completed |
| EFI chain | Staged loaders match ISO; GRUB verifies against CA8 embedded in ISO shim; firmware db/dbx/SBAT acceptance pending |
| Firmware | Operator reports UEFIOnly, Secure Boot enabled and wired IPv4 PXE enabled; no settings changed |
| Network | Router remains sole allocator; workstation proxy targets pilot only; namespace positive/negative tests passed |
| Services | Dedicated root-controlled configs/state; isolated dnsmasq/nginx, nft guard and30minute transient units; original system/libvirt preserved |
| Recovery | First activation failed at PID parsing; bounded rollback confirmed, evidence quarantined; corrected retry succeeded |
| Access | Personal key backup tested by operator; node public-key account/password-sudo design selected, not installed |
| Storage | No Windows preservation requested; exact node/disk/data-loss approval still required |
| Platform | No RHEL install, SSH handoff, host configuration, RKE2/Rancher/Flux action or compatibility certification |

See [pilot files/checks](pilot/README.md), [activation/shutdown contract](pilot/ACTIVATION-PROPOSAL.md),
[isolated fixture](pilot/PACKET-VALIDATION-PROPOSAL.md), and
[subsequent infrastructure stages](../infrastructure/PREPARATION.md).

## Boot chain and exposure

UEFI → router address + targeted proxy boot information → DVD shim/GRUB →
kernel/initrd → Anaconda inst.repo tree → interactive review. The selected DVD
includes .treeinfo, installer runtime and BaseOS/AppStream. There is no inst.ks,
automatic agreement acceptance or unattended disk command.

Dedicated nonsecret TFTP/HTTP roots only: never repository, home, .secrets or the
images directory. No private keys, passwords/hashes, tokens or subscription/registry
credentials in served content or URLs. DHCP MAC targeting is not file access
authentication: independent interface/IP/MAC ingress guards and nginx IP allowlist
restrict file traffic; spoofing remains possible. Secure Boot does not authenticate
GRUB configuration or HTTP transport. Stop on coexistence/trust failure rather
than disabling security or widening targeting.

## First physical boot checkpoint

1. Confirm current shutdown/retained-state evidence and review reactivation; never
   blindly run fresh activate/retry against retained roots. Recheck named unit,
   listener and guard status. Existing DNS/libvirt and router remain untouched.
2. After **separate boot approval**, select the Lenovo **F12** one-time UEFI wired
   IPv4 network entry before Windows; no permanent boot-order change.
3. **Stop at the indefinite GRUB menu. Do not choose the installer.** Record actual
   architecture/request paths and Secure Boot acceptance or exact error. Firmware
   fallback is not proof of a Windows recovery path.
4. Installer/kernel loading, OS configuration and exact disk/data-loss confirmation
   are later approvals. No wipe/Begin Installation permission follows from boot.
5. Use identity-checked dedicated shutdown; confirm units/listeners/guard absent,
   preserve evidence and safe menu. Timer expiry alone does not remove the guard.

Sources: [Red Hat RHEL10 PXE preparation](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/preparing-a-pxe-installation-source),
[dnsmasq](https://thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html),
[Lenovo one-time startup guidance](https://support.lenovo.com/us/en/products/desktops-and-all-in-ones/thinkcentre-m-series-desktops/thinkcentre-m920q/solutions/ht500209).
