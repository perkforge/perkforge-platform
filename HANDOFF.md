# Platform handoff

## Codex CLI: worker OS/access verified, workstation PXE stopped

Use the **existing feature worktree** on `docs/physical-execution-journal`; do not
start a second checkout or discard its uncommitted work. Codex CLI can work in
this directory. Read AGENTS.md, this file and [the PXE entry](pxe/README.md) first.
The configured publication destination is `origin`:
`https://github.com/perkforge/perkforge-platform.git`. A separate legacy `source`
remote exists; it is not this task's publication destination. The operator has
authorized a conventional commit and push of the reviewed changes to this feature
branch on origin. Never push main or merge.

**Current worker checkpoint:** operator reports installation finished and
worker-1 reached installed RHEL login after Ethernet was disconnected for reboot.
Primary Boot Sequence had already been changed to disk above network, but a
connected restart still attempted PXE. Automatic Boot Sequence was not changed;
its effect and UEFI entry ordering remain unresolved. Operator subsequently
confirmed the expected LAN address and password-sudo.
A native approved SSH handoff completed at2026-10-31 16:21:56UTC, exit0: full
Ed25519 fingerprint compared against physical console, same existing public key
as control-1 enrolled, fresh key-only login succeeded, reviewed policy syntax/
effective settings validated before reload, then separate fresh key-only login
and password-required sudo succeeded. Username is corey; no credential values
collected. Private step logs/summary and storage inspection are under
`pxe/local/worker-1/access/handoff-t_qjuics/`. Do not rerun its one-time wrapper:
the managed policy now exists and is intentionally protected from overwrite.
Do not claim persistent connected disk-first boot behavior is fixed.

Operator identified one internal WDC PC SN520 SDAPNUW-256G-1006 at nvme0n1,
238.47GiB, and explicitly approved its data disposal for RHEL. The reviewed
interactive layout was600MiB standard EFI,2GiB standard XFS /boot and remaining
XFS root on ordinary LVM, without separate home/swap or encryption. Native
read-only SSH inspection confirmed the EFI, /boot and XFS LVM root mounts and
expected sizes; exact disk bytes are retained privately. Root was left disabled;
named user/
password entered locally, with administrator/password requirement, Minimal Install,
worker-1 hostname and wired networking acknowledged. No credential values were
collected. Persistent disk ID/serial remain unknown; automated
Kickstart guards stay unchanged and blocked. Control-1 and other nodes preserved.

Keep Secure Boot unchanged. The operator explicitly requested workstation PXE
shutdown; the native identity-checked playbook completed2026-10-31 16:24:13UTC,
exit0, ok33/changed2/failed0. It verified dedicated units/processes/listeners gone,
matching guard absent and original system/libvirt/default nginx preserved. No node
action was performed. Private log/summary:
`pxe/local/worker-1/discovery/shutdown-output-iWauEFig.log` and `.summary.txt`.
Runtime/log/media and held failed-run evidence remain. Worker OS/access is verified
as described above; persistent connected-boot ordering and RKE2 readiness remain
unresolved. Worker-2 is not configured or authorized by this session. Worker-1
poweroff was advised afterward; actual poweroff has not been confirmed.

**Earlier activation evidence (subsequently shut down):** approved recovery/
activation completed at 2026-10-31 15:41:44 UTC, exit0; recap107ok/14changed/
0failed/0rescued.
Private evidence is `pxe/local/worker-1/discovery/activation-output-mw1VaHuM.log`
and its `.summary.txt`. The protected prior transaction and both exact failed
invocation IDs were checked before resetting only those two PID0 failed states.
Both transient units then verified unloaded/stopped. Prior runtime/log roots were
preserved in non-overwriting `held-worker1-discovery-20261031-attempt2` paths;
earlier held evidence remains. The fresh activation passed read-only media,
reviewed hash, ingress guard, listener and original-service preservation checks.
A separate native systemctl query confirmed both dedicated units active with
RuntimeMaxUSec=infinity. This session was subsequently explicitly shut down as
recorded above;
do not rerun the one-time start wrapper. The one-time local recovery intentionally
requires the prior failed transaction and will reject the new active session.

The source maps the approved unlimited choice to explicit RuntimeMaxSec=infinity,
checks the reported runtime property, and retains the30-minute default and approval
gate. Eight offline activation tests and five local recovery scenarios passed;
Ansible/shell syntax checks passed. These fixtures are separate from native results.
No worker boot, installer selection or disk write was performed by this recovery.

Architecture upkeep is an ongoing operator requirement: keep high-level C4
context with workstation/node/platform drill-down and a repeatable operating
procedure. The operator requested removal of planning and session clutter from
that viewer. `docs/architecture/` now contains architecture, reusable interactive
steps, protocol/access/lifecycle details and concise capability limits. Session
status, approvals, troubleshooting and implementation backlogs remain outside it
in the existing handoff/journal/history. Do not add per-worker checkpoint views
or planning proposals back into C4. Preserve evidence-producing source/tests and
private evidence. The source-link allowlist contains14 implementation files;
obsolete generated copies were held in ignored shared local custody, not deleted.

**Authority and boundaries:** operator separately approved worker discovery,
network boot, installer inspection, selected sole-disk data loss/interactive RHEL
installation, root-disabled named administrator and worker-only SSH handoff for
corey. Those steps reached the OS/access checkpoint above. No general security,
other-node, RKE2/Rancher/Flux or cloud changes are authorized. Operator explicitly
approved workstation
PXE shutdown and the reviewed local `discovery/stop.sh approved` completed with
private logs and the existing transaction/unit/guard checks. No worker-2 service
retarget/start or installation is approved by that shutdown. The automated Kickstart
candidate remains BLOCKED; do not reinterpret interactive evidence as unattended
validation or weaken its persistent-disk guards. Repeat architecture/procedure
lives in `docs/architecture/`; implementation planning remains separate.

**Execution capability:** sandbox system-bus access remains denied; explicitly
approved native commands can inspect units. Native sudo requires operator input;
the successful run used a visible local terminal with direct password entry,
Ansible no_log and private automatic logging. Do not bypass denials or mistake
projected ownership for native ownership.
Future approved runs must automatically save private operational logs and bounded
exit-status summaries under `pxe/local/worker-1/discovery/`, honor Ansible no_log,
and never record terminal/password input. No more pasted output is expected.

`pxe/local/worker-1/` is the canonical ignored protected worker workspace; shared
local files live under `pxe/local/`. Preserve `.secrets` recovery inputs and all
held native evidence. Only metadata/public-key references belong in inputs; actual
credentials stay in protected custody. The retired console helpers and unfinished
VM runner are explicitly historical under `pxe/pilot/history/`; retain tests and
proven activation/shutdown code. Finish worker OS plus verified SSH/sudo first;
post-worker directory refactor is deferred. For eventual publication, review the
local private path-only audit manifest; no local inputs/logs/tools/build output
belong in Git.


Big Bang/Flux is the chosen platform. Start with [bootstrap tasks](big-bang-bootstrap/README.md). The previous Fleet handoff is [historical only](archive/fleet/HANDOFF.md).

Local audit results:8 activation tests and6 architecture documentation checks
passed; diff whitespace checks passed. The path-only publication inventory is
`pxe/local/publication-audit.txt` (ignored,0600). Pattern-scan matches were only
explicit rejection-test fixtures, not credential material. Recoverable disposal
of five confirmed Python cache directories failed because desktop Trash metadata
is read-only in this environment; caches remain. Do not substitute permanent
delete or empty Trash. Dependencies, generated viewer output, private tools,
inputs and unique evidence were intentionally retained.

## Earlier physical preparation checkpoint (historical)

Current agreed path: [one controlled worker-1 pilot](infrastructure/TOMORROW-READINESS.md)
using standard Kickstart, proven PXE and short access handoff. Full VM rehearsal
and the unfinished custom runner are deferred, not prerequisites. No live install
approval follows; exact worker disk/service/credential scope must be reviewed.


The physical pilot completed RHEL10.2 installation and operator-verified key-only
SSH plus password-authenticated sudo at2026-10-31 02:13:22UTC. Operator reports workstation PXE
shutdown successful at02:14:52; no exact recap/independent probes supplied. Read the
[physical handoff](pxe/pilot/HANDOFF.md) and
[chronological journal](infrastructure/EXECUTION-JOURNAL.md) before any action.
At that earlier checkpoint worker OS disks and platform provisioning were untouched.
The current worker OS/access result is above; RKE2/platform work remains
untouched. Working SSH does not
establish host readiness. Before workers, review the [provisioning redesign](infrastructure/PROVISIONING-REDESIGN.md)
and [retrospective](infrastructure/PROVISIONING-RETRO-2026-10-31.md), then
[tomorrow readiness](infrastructure/TOMORROW-READINESS.md). No deployable replacement is implemented. Preserve retained runtime/log/media evidence.

## Existing local trial

Historical running trial, outside the supported source workflows: two RHEL/RKE2 VMs: cks-control (192.168.122.201, 2 CPU/4 GiB, 30 GiB disk), cks-worker (.202, 2 CPU/4 GiB, 100 GiB disk). The unused AWS EC2 harness is removed from tracked source. Preserve workstation `.secrets`, backups and ignored evidence. Provisioning or teardown requires action-time approval; a merge is not live approval.

The released trial chain before restructuring is platform v0.7.0 → enrollment v0.4.0 → tenant-app v0.3.0 → portal image v0.3.0. Operator-only Keycloak compatibility fixes are in enrollment v0.4.4. Headlamp and Keycloak/PostgreSQL were working; portal admin SSO and denial tests passed, but the 600-second observation failed at 588 seconds from host memory pressure. The user subsequently restored one portal replica. Recheck live state before operations; this document is not a health probe.

Paths in already published tags remain historical. This refactor does not update live source paths or tags. Advance to the new released path only in a separately reviewed activation; a root still pointing to an old path cannot consume this layout automatically. Do not replace an already watched tag.

## Boundaries

- Platform bootstrap knows the enrollment repository, selected cluster context and path, not individual tenants.
- Enrollment owns tenant namespaces, registration, deployment identities and security foundations. App repositories own applications.
- Platform-admin means full cluster-admin for the explicit platform admin group; that does not grant tenant deployers or workloads cluster-admin.
- Keep existing release pins, scoped installers, external credential inputs and live-approval gates. No auth redesign is part of this move.
- Rancher installation/platform-only OIDC configuration is active infrastructure Ansible, default off. It needs its own capacity budget and live approval; it remains absent from the historical tiny trial.

Private trial evidence is retained under the existing ignored operational checkout and `/tmp/portal-live-20261029/`; it must not be copied into Git. Memory headroom and runtime stability remain unresolved.

For source configuration, local now means a PE-owned physical cluster. The running VM trial has not been changed or removed; its provisioning workflow source is intentionally absent. Do not interpret the new local template as matching that running cluster.
