# Human-operated physical RHEL installation

Use the workstation to serve the verified RHEL10.2 media, the physical console for
firmware/Anaconda, and SSH for installed-host access. There is no unattended disk
installer, bootstrap-account framework or AI dependency. The retained scripts and
Ansible playbooks run only when an operator invokes and approves them.

[Current network inventory](../infrastructure/ansible/inventory/hosts.yml) and the
[C4 topology](../docs/architecture/README.md) identify the workstation and nodes.
[HANDOFF.md](../HANDOFF.md) contains current readiness, not a session history.

## 1. Prerequisites and media

Use a wired IPv4 LAN with the existing router allocating DHCP addresses. Confirm
or reserve each intended address against its wired MAC before using it; do not
assume sequential addresses. Keep Secure Boot enabled. The serving workstation
needs Ansible/Python, dnsmasq, nginx, nftables, GRUB validation, xorriso and OpenSSH.
Service users must already exist and be separate (this Debian workstation uses
dnsmasq/nogroup and www-data/www-data). Installing tools or altering services is a
separately reviewed workstation action. The gated
[nginx installer](transport/install-nginx.yml) refuses unsafe existing service state.

Keep the verified RHEL10.2 x86_64 DVD ISO available. Its approved SHA256 is
`e15cb333529c332e76e4b1b946efe3515c99f996546675aec18e8effdf2540a5`.
The [staging script](transport/stage-media.sh) checks it before extraction.
Existing root-owned, read-only media under `/srv/perkforge-pxe-pilot` is reused;
never restage it merely to select a new client.

For an explicitly approved **fresh** staging only, first confirm that
`/srv/perkforge-pxe-pilot` is absent and not a symlink. If present, stop and inspect
instead of changing its modes. Create root:root0700 staging directories:

```sh
sudo install -d -o root -g root -m 0700 \
  /srv/perkforge-pxe-pilot /srv/perkforge-pxe-pilot/http \
  /srv/perkforge-pxe-pilot/http/rhel-10.2 /srv/perkforge-pxe-pilot/tftp
bash pxe/transport/stage-media.sh /absolute/path/to/rhel-10.2-x86_64-dvd.iso
```

Stop at any failure. The script refuses nonempty trees, extracts without mounting,
compares EFI/kernel/initrd copies and applies root-owned read-only modes. Verify
full HTTP DVD contents including `.treeinfo`, BaseOS and AppStream; TFTP serves the
matching vendor EFI chain. No secret belongs in HTTP/TFTP. Do not disable Secure
Boot or replace the proven PXE/TFTP route with an untested protocol.

## 2. Prepare a fresh operator run

Copy [workspace.inputs.example.yml](transport/workspace.inputs.example.yml) to a
protected operator input location outside Git; mode0600. Fill confirmed metadata
from inventory: node and fresh run name; client MAC/IP; workstation interface/IP;
subnet, existing service identities and media/boot paths. Keep unknown required
fields UNCONFIGURED. There are no password/private-key inputs.

Select `workspace_menu_state: stock` only for the inspected original ISO menu and
supply its actual SHA256. Select `reviewed` only when the existing served menu is
the exact indefinite default-exit menu. Human content review remains necessary.
Set lifetime1800seconds, or0 only when explicitly choosing indefinite service
availability and manual shutdown. A timer must not cut off an installation.

Run without sudo, replacing the input path and fresh run label:

```sh
ansible-playbook -i localhost, -c local pxe/transport/workspace.yml \
  -e @/absolute/path/to/operator-inputs.yml -e workspace_run=NEW_RUN_NAME
```

This creates `pxe/local/<node>/runs/<run>/` with input snapshot, README, standard
`session.sh`, discovery configuration/hash manifest and an empty access directory.
It also renders a fresh private `/tmp/perkforge-pxe-review-*` source directory.
Directories0700, metadata0600, caller0700. It refuses existing outputs/symlinked
ancestors and performs no live network, package, service, disk or credential action.
Review the actual rendered files and hashes before any live start.

The local directory is disposable generated work, not credential custody or a
history repository. Start from a fresh run after moving the checkout or losing
/tmp. Keep the human-maintained input externally if desired; otherwise reconstruct
it from the schema, current inventory and inspected native state. Do not copy a
previous node's one-off launcher or assume its approval transfers.

## 3. Activate reviewed serving

Change into the generated run. After approving this exact client, exposure, menu
and lifetime:

```sh
bash session.sh start approved
```

The existing guarded activation checks absent runtime/log roots, dedicated units,
ports/table, wired identity, source hashes and read-only media; records original
service identities; installs root-controlled configuration and a dedicated guard
before LAN binding; then verifies unit/runtime/listener state and original services.
No node boots or erases automatically. Default nginx stays masked/inactive; router
and unrelated system/libvirt services remain untouched.

If a prior stopped session left runtime/log roots, start must refuse them.
For separately approved preservation, fill the prior manifest path, exact protected
config-session path and fresh `held-...` label in the operator input before building.
Then use `bash session.sh preserve approved`. It verifies unloaded/inactive PID0
units, absent listeners/guard, prior config/units/hashes/lifetime, ownership and
non-mountpoint roots before non-overwriting moves. It never resets/stops/starts
services. Unknown/partial state requires inspection, not broad cleanup.

## 4. Physical boot and interactive installation

Record existing firmware order. Use one-time wired UEFI IPv4 PXE when reliable;
otherwise temporarily put network first under Startup / Primary Boot Sequence.
Keep Secure Boot enabled. At the indefinite GRUB menu, select the interactive
installer only within the approved scope; menu acceptance alone is not erase approval.

Inspect Installation Destination. For a single-drive interactive installation,
confirm internal-drive count, model, capacity and current Linux device. Approve
this node's entire existing-data loss; do not reuse another node's approval or
weaken persistent identity checks for any automated erasure.

Choose Custom and remove old partitions only on the approved disk. Use:

| Mount | Capacity | Device | Filesystem |
|---|---|---|---|
| /boot/efi | 600MiB | Standard partition | EFI System Partition |
| /boot | 2GiB | Standard partition | XFS |
| / | Remaining | Ordinary LVM | XFS |

This local-lab profile has no separate home/swap, encryption or FIPS; it is not a
production/compliance baseline. Verify Summary of Changes touches only the selected
disk. Choose Minimal Install, node hostname, wired networking and reviewed timezone.
Keep root disabled; create the approved named administrator with password required.
Enter passwords only locally. With warnings resolved, Begin Installation commits
storage changes. Keep workstation/source available through explicit completion.

## 5. First disk boot

After installation finishes, restore disk-first in the relevant **Primary and
Automatic Boot Sequences**, retaining Secure Boot. Verify with Ethernet connected.
If PXE runs first, wait for its failure to fall through; if it reports no OS or
loops, inspect both sequences, disk detection and the RHEL UEFI entry before repair.
A temporary Ethernet disconnect after installation can allow disk boot but does
not prove saved ordering is correct. Reconnect Ethernet at installed login.
Verify hostname, address and password-authenticated sudo before leaving the console.

## 6. SSH access from the workstation

Keep the existing private key in the workstation SSH store, never in this project.
The current physical inventory references its path, not its contents. Unlock a
passphrase-protected key locally if needed:

```sh
ssh-add -t 3600 ~/.ssh/perkforge-local-corey-admin
```

Current verified host-key pins are in the ignored operator trust file
`infrastructure/ansible/inventory/known_hosts.local`. A fresh checkout must verify
host identity through physical console before rebuilding that trust; never accept
a changed key automatically. For a new approved access handoff, set shell variables
`host`, `operator`, `key`, `client`, `expected_hostname` and `run` from reviewed
metadata and the generated run, then create a fresh trust directory:

```sh
umask 077
trust_run=$(mktemp -d "$run/access/handoff-XXXXXXXX")
ssh-keyscan -T 5 -t ed25519 "$host" > "$trust_run/host-key.unverified"
ssh-keygen -lf "$trust_run/host-key.unverified"
```

Compare the **complete** fingerprint against this command at physical console:

```sh
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Only after a real match, pin the candidate and record confirmation:

```sh
cp --no-clobber "$trust_run/host-key.unverified" "$trust_run/known_hosts"
printf 'Complete fingerprint compared and matched at physical console.\n' \
  > "$trust_run/trust-confirmed.txt"
bash pxe/transport/access.sh approved "$host" "$operator" "$key" "$client" \
  "$trust_run" "$expected_hostname"
```

The shared human-invoked caller enrolls the existing public key, proves fresh
key-only login/user/hostname/client, transfers/hashes the checked policy helper,
then applies it through approved local sudo input. It refuses an existing managed
policy, validates syntax/effective settings before reload and finally verifies a
separate fresh key-only login and password-required sudo. Root/password/keyboard-
interactive SSH are disabled; PAM remains. Keep console/current recovery access
until success. If enrollment needs a temporary password-SSH window, approve and
verify closure explicitly rather than silently changing host authentication.
No secret is recorded; private output/exit summaries contain operational results.

## 7. Stop and leave the workstation clean

Once the installer no longer needs its source, separately approve and run:

```sh
bash session.sh stop approved
```

Shutdown verifies transaction/unit/guard identity, stops only owned units and checks
processes/listeners/guard absent and original services preserved. It retains native
runtime/log records and read-only media; it does not shut down nodes. Do not clear
unrelated services or firewall rules. Review failures before retrying.

After use, remove disposable local runs only after confirming required current
inventory/trust and any needed recovery input are retained. Do not keep historical
source trees, narrative journals or duplicate generated docs. Never delete keys or
unique recovery material merely to clean a working directory. An installed RHEL/
SSH/sudo checkpoint is not RKE2 readiness; continue with
[infrastructure](../infrastructure/README.md) only under separate host/cluster scope.

## Retained checks

The focused [tests](tests/) exercise the supported transport, input validation,
state ownership, shutdown, media guards and SSH policy with disposable fixtures.
They do not constitute live validation of another node:

```sh
python3 -m unittest discover -s pxe/tests -p 'test_*.py'
```
