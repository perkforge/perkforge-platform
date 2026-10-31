# Platform handoff

## Codex CLI: resume here, provisioning paused

Use the **existing feature worktree** on `docs/physical-execution-journal`; do not
start a second checkout or discard its uncommitted work. Codex CLI can work in
this directory. Read AGENTS.md, this file and [the PXE entry](pxe/README.md) first.
The configured publication destination is `origin`:
`https://github.com/perkforge/perkforge-platform.git`. A separate legacy `source`
remote exists; it is not this task's publication destination. No commit/push is
part of the current handoff/audit. Never push main or merge.

**Current worker checkpoint:** worker-1 is user-reported in BIOS. Photo/user
observations identify a WDC PC SN520 SDAPNU-256G-1006, nominal256GB; disk serial,
exact bytes and Linux `/dev/disk/by-id` remain unknown. Primary Boot Sequence
reportedly puts disk first; Automatic Boot Sequence puts network first. Leave
both unchanged; which sequence governs next boot is not established. Control-1's
installed RHEL/key-only SSH/password-sudo checkpoint must be preserved. No RKE2
or Rancher work belongs in this session.

**Latest native evidence, available directly in ignored local files:**
`pxe/local/worker-1/discovery/activation-output-npUzGQKr.summary.txt` reports exit2,
3ok/0changed/1failed: both dedicated pilot units remained failed with MainPID0.
The preceding `activation-output-oVWLs4nh.log` records an immediate timeout caused
by incorrect `RuntimeMaxSec=0`, then successful bounded rollback assertions:
pilot processes/listeners gone and dedicated guard absent. These are captured
results, not a new live probe. The failed run's protected transaction/config path
and two prior invocation IDs are in that log; inspect them before any reset.

The source now maps the approved unlimited choice to explicit
`RuntimeMaxSec=infinity`, checks the reported runtime property, and retains the
30-minute default and approval gate. Eight offline activation tests pass. The
current local retry wrapper still rejects failed units; **do not run it blindly**.
Complete one consolidated, tested recovery: verify exact protected transaction,
unit invocation identities and PID0; clear only those matching failed unit states;
verify unloaded/stopped state; preserve the failed run in non-overwriting held
paths; then activate worker-only discovery. Never broad-reset services, weaken
read-only media checks or delete retained evidence. No recovery has run since the
latest failed preflight.

**Authority and boundaries:** the operator approved worker-only discovery service
activation/retry, unlimited until explicit shutdown, and only the known public
console directory0755→0555 correction (completed). This is not worker installer
selection, installation, disk wipe, new credential creation or general security
change authority. Provisioning is now paused for this handoff; confirm resumption
with the operator before native recovery. Worker disk identity and explicit
installation/data-loss approval remain necessary. Proposed workflow is standard
RHEL Kickstart plus proven PXE and a short Ansible access handoff; the generic
physical candidate remains BLOCKED. Full custom VM rehearsal is deferred, not a
gate. No node-command transcription is the intended normal workflow.

**Execution capability:** this delegated environment cannot access native netlink,
system bus or protected root transaction files. Do not bypass denials or mistake
projected ownership for native ownership. A locally launched Codex CLI may have
different permissions; inspect its actual capabilities and approval policy.
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

## Physical preparation checkpoint

Current agreed path: [one controlled worker-1 pilot](infrastructure/TOMORROW-READINESS.md)
using standard Kickstart, proven PXE and short access handoff. Full VM rehearsal
and the unfinished custom runner are deferred, not prerequisites. No live install
approval follows; exact worker disk/service/credential scope must be reviewed.


The physical pilot completed RHEL10.2 installation and operator-verified key-only
SSH plus password-authenticated sudo at2026-10-31 02:13:22UTC. Operator reports workstation PXE
shutdown successful at02:14:52; no exact recap/independent probes supplied. Read the
[physical handoff](pxe/pilot/HANDOFF.md) and
[chronological journal](infrastructure/EXECUTION-JOURNAL.md) before any action.
Worker OS disks and RKE2/platform provisioning remain untouched; worker-1 firmware inspection and failed workstation discovery starts are described above. Working SSH does not
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
