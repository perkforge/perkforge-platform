> HISTORICAL execution proposal; not current operating instructions.
> Start at [PXE README](../../README.md). Commands below are retained evidence.

# Workstation pilot activation — operator evidence and pause contract

Corrected operator native retry succeeded at23:53UTC (ok78 changed12 failed0
rescued0). Operator requested a supper pause before first boot; explicit shutdown
status is maintained in HANDOFF.md and the journal.

The operator supplied native isolated-fixture evidence: daemon PASS, guarded
PASS, wrong-interface PASS, final-controls PASS, namespaces ABSENT; recap
ok54 changed16 failed0 rescued0 ignored0. This tests current shared templates
in synthetic namespaces, not router coexistence, physical firmware or Secure Boot.

## Exact next approval

Approve **workstation-only** reviewed config/state/log placement, replacement of
only the TFTP GRUB menu, the dedicated nft guard table, final config checks
including a brief LAN TCP8080 bind/listen, and two dedicated transient services
for **at most30minutes**. Approval includes identity-checked shutdown on failure
and the explicit shutdown command. No node boot, firmware change, installer
selection, disk write, package/credential action, default-service start/unmask
or additional packet test is included.

`pilot.sh` dispatches to `activate.yml` / `shutdown.yml`; never source it.
Ignored0600 activation-review.yml records exact source SHA256 values, original
menu hash and wired identity. Public docs contain no private MAC/IP inventory.
After approval, from this checkout:

```sh
bash "$REPO_ROOT/pxe/pilot/pilot.sh" activate
```

Do not run during preparation. Enter sudo password only at Ansible's prompt.
On failure preserve output; never blindly retry. No agent sandbox bypass.

## Exact placement and ordering

1. Fresh preflight requires absent pilot runtime/log roots, dedicated unit names
   and nft table; masked/inactive default nginx; current wired IPv4/24; reserved
   ports free. Existing DHCP67 is permitted only on reviewed libvirt-bound virbr0,
   never on the pilot LAN. Unknown listeners cause STOP, not service termination.
   Record existing dnsmasq PID/argv privately.
2. Check all four source hashes. Reject media symlinks/special files, nonroot
   ownership, writable media and alternative TFTP grub.cfg files. Compare staged
   kernel/initrd/loaders and require the original ISO-reviewed menu hash.
3. Create only the layout below; copy reviewed files into a unique root-only
   config session. Rehash copies before use; no daemon reads editable /tmp sources.
4. Save the original TFTP menu outside served roots. Atomically replace only
   TFTP EFI/BOOT/grub.cfg, root0444, with the reviewed indefinite/default-exit
   menu; assert hash and absence of Kickstart/unattended storage commands.
   HTTP DVD stays unchanged. Never restore its60second menu while serving.
5. Parse installed dnsmasq/GRUB/nft copies. Apply an exclusive atomic nft batch:
   create the dedicated table and include its reviewed definition. A concurrent
   existing table causes failure rather than modification. Snapshot actual table
   JSON before starting anything. No existing table edits.
6. Behind that guard, nginx-t validates actual installed config/state/log paths
   and can briefly bind/listen on LAN TCP8080. Rehash copies/menu before launch.
7. Start only perkforge-pxe-pilot-dnsmasq.service and
   perkforge-pxe-pilot-http.service: Type=exec, Restart=no, KillMode=control-group,
   RuntimeMaxSec=1800, unique root-controlled config paths. Capture InvocationID/
   MainPID/ExecStart. Verify active units/listeners, unchanged original dnsmasq
   identities and masked/inactive default nginx.
8. **STOP for review; no node boot or additional packet probe.** Later approval
   may permit control-1 one-time IPv4 boot with Secure Boot ON, stopping at GRUB.
   Firmware architecture/db/dbx/SBAT/request acceptance remains runtime evidence;
   installer/kernel acceptance and disk approval are later separate steps.

## Ownership

| Location | Owner/mode |
|---|---|
| /run/perkforge-pxe-pilot, /var/log/perkforge-pxe-pilot | root:root0711; traversal only |
| runtime/config and unique session | root:root0700; configs/records0600 |
| logs/control and original menu backup | root:root0700 /0600 |
| runtime/dnsmasq, logs/dnsmasq | dnsmasq:nogroup0700; dedicated PID/lease/log |
| runtime/http, logs/http, HTTP temp children | www-data:www-data0700; PID/lock/temp/log |
| Served TFTP menu | root:root0444, parent root0555 |

Logs precreated0600; no shared service group, media chown, home/repository root or
secrets served. Writable PID files are not shutdown authority; systemd invocation
and executable identity are checked instead.

## Ports and limits

| Port | Scope |
|---|---|
| UDP67, client68 | Wired-interface proxy DHCP, pilot MAC; source0.0.0.0 permitted before address; router sole allocator |
| UDP4011 | Pilot PXE boot-server requests; interface/IP/MAC guards |
| UDP69,20000–20009 | Dedicated nonsecret TFTP root; transfer ACKs guarded too |
| TCP8080 | Wired workstation IPv4; nft interface/IP/MAC checks plus nginx pilot-IP allowlist, GET/HEAD, no autoindex/symlinks |

Only inet perkforge_pxe_pilot, input priority-10, defaultaccept, is applied.
It restricts reserved ports (including alternate-address/IPv6 bypasses) and inbound
DHCP67 on the selected wired interface. No NAT, forwarding, routing, other tables
or unrelated ports change. Accept does not override another chain's drop.
Existing system DNS/libvirt remain intact. MAC/IP filters are spoofable; Secure
Boot does not authenticate GRUB config/HTTP transport. Router/firmware coexistence
still needs observed evidence; never disable controls to force success.

## Shutdown / failure

```sh
bash "$REPO_ROOT/pxe/pilot/pilot.sh" shutdown
```

Shutdown verifies protected transaction, unique config path, KillMode and recorded
InvocationIDs, then stops only the two dedicated units. It requires MainPID0,
reserved listeners absent, original dnsmasq unchanged and default nginx still
masked/inactive. It removes only the guard whose JSON matches this session's
record. Changed/unrecorded rules are retained for inspection; query failures are
not absence. No pkill, killall, flush or whole-ruleset restore.

Activation failures after network mutation invoke the same bounded shutdown.
Pre-network partial placement can leave protected dirs/safe menu; inspect before
retry. A failed cleanup/identity check remains failure. Corrected LAN activation and first-attempt bounded rollback have native evidence;
see the handoff for current pause/shutdown state.

Transient units are not enabled for reboot and stop after30minutes; timeout does
not remove guard rules. Run shutdown explicitly. Runtime/log evidence and safe
TFTP menu remain; later activation refuses retained roots pending reviewed reset.
No media deletion or automatic restoration of the old timeout menu.

Exclusive table creation semantics: [official nft manual](https://netfilter.org/projects/nftables/manpage.html).

## Current held state and explicit retry

The original-process query now uses numeric validated first tokens, never a
replacement backreference. Original baseline/session snapshots are untouched.
Native23:42:10 status confirmed dedicated units inactive/MainPID0, reserved
listeners absent and guard absent. Native23:45:37 metadata showed both retained
roots are root-owned0711 directories and both proposed held destinations absent.
The operator subsequently approved and completed both quarantine moves at23:50:53;
corrected retry then succeeded. Those held roots remain preserved.

Before approving moves, compare current served-menu SHA256 and protected original
backup: current must equal the reviewed menu snapshot; backup must equal the
ISO-reviewed original. Inspect that neither source root is a mountpoint/symlink.
The reviewed move flags available in installed coreutils are --no-copy,
--update=none-fail, -T and --verbose: no cross-filesystem copy fallback, no existing
destination replacement or silent skip, and no directory nesting. Moves are an
explicit separate approval, never automatic activation cleanup. Preserve both
roots through same-filesystem quarantine renames, no deletion; if only one move
succeeds, stop and report the partial state rather than undoing/retrying blindly.

pilot.sh now has explicit retry mode. It uses the same bounded activation but
requires exactly the reviewed-menu hash; first activation requires exactly the
stock hash. Neither mode accepts an arbitrary alternate hash. Runtime/log roots
must still be absent, so retry remains blocked until reviewed quarantine is done.
Retry keeps the reviewed safe menu and the original backup in held logs; the new
attempt's pre-activation backup may itself be the reviewed safe menu.

After hash/metadata inspection, explicit quarantine approval, successful moves
and post-move verification, use the short reviewed retry command:

```sh
bash "$REPO_ROOT/pxe/pilot/pilot.sh" retry
```

Do not run retry merely because code is corrected. Shutdown command is unchanged.

## Approved current-session rearm

After reaching the indefinite GRUB menu, the operator explicitly selected no
runtime timeout for this pilot session, replacing the proposed two-hour choice.
This is not a new deployment-wide default: normal activation remains30minutes.

`pilot.sh rearm` invokes `rearm.yml`: verify protected transaction/config/menu
hashes, exact unchanged guard, unit path/KillMode/InvocationIDs and saved original
process baseline; archive old transaction/invocation records; stop only matching
dedicated units; require old names/listeners absent; recreate those same units
with RuntimeMaxSec=infinity; capture new start timestamps/identities, update
shutdown records and verify guard/default-service/baseline preservation.
Already-expired absent units are accepted only with trusted prior identity records.
A half-failed rearm stops only matching pilot units and retains guard/evidence.
No staging, quarantine, media/GRUB rewrite or firewall apply/removal occurs.

Hold at GRUB throughout; rearm does not approve installer selection. The final
message must report RuntimeMaxUSec=infinity for both units. With no automatic
timeout, explicit shutdown and verification when finished are required. Never use
set-property for the running257 service; it does not support this property update.
