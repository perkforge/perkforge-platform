# Physical RHEL provisioning

Start with [Red Hat's current workflow and our adaptations](../infrastructure/RHEL-PROVISIONING-GUIDANCE.md).
The target experience is review a per-node plan, approve the exact install, select
network boot, and receive a verified installed-host result. **Installation is not
ready or armed yet.** Current code implements offline preparation only. Human steps are power,
BIOS/network-boot selection and a trusted physical identity/fingerprint check when
needed. Normal installation must otherwise run from the workstation, with no
node command transcription or interactive installer. This is an agreed future
operator boundary, not approval to change firmware or boot a node now.

Follow along in the [interactive LikeC4 views](../docs/architecture/README.md):
context, numbered operations1–7, boot sequence, stop gates and observed checkpoint.

## Normal starting point

| Path | Role |
|---|---|
| ansible/prepare.yml | Local Ansible preparation: render two private, inert review files; no host/services/packages/network actions |
| inputs.example.yml | Nonsecret input shape; missing values explicit, credential mode undecided |
| kickstart/rhel10.ks.j2 | Standard RHEL10 candidate; unconditional abort, no active disk-erasure/layout commands |
| tests/ | Real Ansible preparation tests with synthetic metadata and temporary output only |
| pilot/ | Historical interactive pilot, evidence-producing fixtures and existing recovery/shutdown compatibility; not the default install path |

[Preparation details](ansible/README.md), [redesign](../infrastructure/PROVISIONING-REDESIGN.md),
[retrospective](../infrastructure/PROVISIONING-RETRO-2026-10-31.md) and
[readiness](../infrastructure/TOMORROW-READINESS.md) distinguish working code from
proposed install/status/stop behavior. There is no apply/install switch hidden in
preparation. Filling metadata cannot remove the Kickstart's hardcoded abort.

This offline example writes only a **new** private temporary review directory;
choose a fresh name if it already exists. It does not inspect or install a node:

```sh
ansible-playbook -i localhost, -c local pxe/ansible/prepare.yml -e output_dir=/tmp/perkforge-pxe-plan-review
```

Real operator metadata belongs in ignored private inputs, never this example or
Git. `--check` validates without creating output. Both generated files remain
BLOCKED; no media is copied or served. Existing output is preserved, not reset.

## Red Hat solution and nginx

Red Hat documents DHCP plus PXE/TFTP or UEFI HTTP boot, and an HTTP(S) installation
tree/Kickstart source. Nginx is a sound static HTTP server for that role on our
Debian workstation; it does not replace DHCP, firmware or Anaconda. Red Hat's
RHEL-server examples use different packages/services, so their host commands are
not a drop-in Debian recipe. Our router remains the address allocator; proxy
DHCP is an explicit coexistence adaptation. No need to replace nginx merely to
follow the installation workflow.

Red Hat prefers UEFI HTTP boot when firmware supports it because it is usually
more reliable; PXE/TFTP has wider support. Our pilot proved a TFTP-based boot,
**not UEFI HTTP support**. Treat HTTP boot as a candidate to verify, not an
unannounced protocol/firmware change. [Vendor overview](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/preparing-a-pxe-installation-source).
[Satellite](https://docs.redhat.com/en/documentation/red_hat_satellite/6.17/html/provisioning_hosts/index)
is Red Hat's larger managed provisioning solution; adopting that product is not
needed for this three-node project and is outside this refactor.

## Existing pilot is preserved

The first pilot completed RHEL10.2 installation, disk-first boot and key-only
SSH/password-sudo verification. Operator reports temporary PXE shutdown successful
at2026-10-31 02:14:52UTC; final independent probes were not supplied. Workers and
RKE2/platform preparation remain untouched. See [current handoff](pilot/HANDOFF.md)
and [journal](../infrastructure/EXECUTION-JOURNAL.md). Power-off is not confirmed.

The old `pilot/pilot.sh shutdown` path and protected identity checks are unchanged
by the new preparation. Preserve held/runtime/log/media evidence and ignored
backups. Do not run old activate/retry/rearm or console-enrollment helpers as a
new installer. The failed HTTP enrollment route is historical, not a dependency.
No files moved/deleted that would break current recovery or its regression tests.

Considering control-1 again is a possible future test target, **not disk-erasure
approval**. Keep its working OS/access intact until a complete replacement has
passed rehearsal and a new exact-disk/data-loss plan is explicitly approved.

## Gates and trust

Complete disk identity and protected credential mode, RHEL10 validation tooling,
actual install/reboot/key/sudo rehearsal and scoped service lifecycle before any
install. No private keys/passwords/hashes/tokens in served files or URLs. MAC/IP
filters are spoofable; Secure Boot does not authenticate fetched GRUB/Kickstart.
Do not disable security or widen the LAN to make a test pass. RKE2 is a separate
approved stage; working SSH does not establish host readiness.

Offline checks (no native packet/service test):

```sh
python3 -m unittest discover -s pxe/tests
python3 -m unittest discover -s pxe/pilot/tests
python3 -m unittest discover -s pxe/pilot/console
```
