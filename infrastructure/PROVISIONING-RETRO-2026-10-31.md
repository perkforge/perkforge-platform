# Retrospective: first physical RHEL installation

2026-10-31. Evidence: the [chronological journal](EXECUTION-JOURNAL.md),
[current handoff](../pxe/pilot/HANDOFF.md), and linked source below. This is analysis
and a proposal, not permission for another live operation. Recommended changes
are in [the provisioning design](PROVISIONING-REDESIGN.md).

## Outcome and honest scope

One physical node now boots RHEL10.2 Minimal Install from its NVMe disk with
operator-verified public-key SSH, password-authenticated sudo, root disabled and
validated key-only SSH policy. The operator reports temporary PXE shutdown
successful at02:14:52; no exact final recap or independent probes were supplied.
Workers and RKE2/Rancher/Flux were not installed. Node power-off was suggested,
not confirmed; do not claim current power state.

The boot/media/packet controls worked well enough to reach the graphical installer
with previously reported Secure Boot enabled. Private keys were not served. The
operator established encrypted key backup and independent recovery arrangements.
Those are useful outcomes, but do not justify the delivery burden. The user
reports about eight hours of command copying/typing. The journal's20:07 media
checksum to02:14 shutdown interval is only one captured portion; it does not
measure eight hours of installer runtime or isolate each source of delay.

## Why it was difficult

We selected an **interactive first installation** and then built workstation
staging, coexistence controls, lifecycle recovery and SSH enrollment while the
operator waited. The [menu](../pxe/pilot/templates/grub.cfg.j2) explicitly omits
`inst.ks`; manual partitioning/account/network screens were the intended result.
RHEL supports a standard unattended Kickstart path. PXE was not the wrong choice;
a development/debug session was presented as provisioning before that path existed.

The assistant environment could edit the worktree but could not perform native
privileged workstation actions. That constraint should have produced one tested,
reviewable entrypoint for a native operator, with clear execution ownership.
Instead, repeated short approvals, long pastes and subsequent diagnostic commands
made the operator the remote executor and log transport. The assistant owned
those workflow defects; they were not failures of the person typing commands.

A first hardware pilot reasonably needs a firmware/disk review. It does not need
separate conversational permission for every already-authorized mkdir, parser,
read-only observation or installer field. Conservatively blocking a destructive
unknown disk was appropriate; repeatedly stopping bounded implementation details
was not necessary to preserve that boundary. Some real new scopes arose during
troubleshooting and did warrant explicit approval. The remedy is a complete plan
before execution, not removal of consequential approval or safety checks.

## Recorded failures and what we can actually conclude

| Event and journal evidence | Defect or limit | Required change |
|---|---|---|
| Before22:15:02, BatchA closed Konsole; later four paths absent | Uncontained strict shell options could exit the interactive shell; ISO variable was unassigned and checksum output suppressed. Exact failing command remains unknown. | Standalone invocation from the start; explicit inputs, named errors, caller-survival tests. |
| BatchB did not fully paste;22:28 destinations empty; standalone script later succeeded22:33 | Long heredoc was unsuitable terminal delivery. Initial partial execution was uncertain, not automatically safe to rerun. | Short command to a reviewed file; automatic, scoped state report. |
|23:37 activation failed;23:42 rollback resources checked absent | Over-escaped Jinja replacement yielded literal backreferences instead of numeric PIDs; reproduced against synthetic ps. Broad no_log concealed the useful failure. | Test exact rendered expression and real success contract; expose safe checkpoint/status while protecting argv. |
|23:48–23:53 quarantine/retry and later resume | Refusing unknown state protected evidence, but the normal recovery path required manual directory inspection, hashes and renaming. | Own resumable session state and per-attempt evidence; tests must prove safe repeat/resume, not just refusal. |
|00:45–00:54 service rearm | Original30minute cutoff could expire during installation. A running systemd transient service could not be extended via the assumed property path; controlled replacement was implemented while the user waited. | Choose full-session lifetime up front, no mid-transfer cutoff; tested session stop/resume. |
| F12 led to Windows; approved temporary Network1-first eventually reached GRUB | One-time firmware path did not behave as hoped; exact cause was not established. No Secure Boot bypass was needed. | Record device-specific boot recipe once; disk-first after install, no unarmed automatic reinstall. |
|01:52 first HTTP enrollment stopped after fingerprint | Filtered systemctl list-unit-files can return nonzero on no matches; unguarded set-e assignment exited before mutation. Source-based explanation fits symptoms but native exit location was not independently captured. | Test empty successful data and every preflight return status; named diagnostic for all exits. |
|01:58 corrected enrollment rejected active/enabled SSH socket | Broad search of socket descriptions/names is demonstrably overbroad. Exact native unit/endpoint was never obtained; a real enabled TCP socket cannot be ruled out. | Do not claim resolved or disable all sockets. Remove this path from normal provisioning; classify actual endpoint/activation if retained for recovery. |
| Temporary password SSH finally succeeded; key-only completion02:13 | Standard ssh-copy-id plus a small reviewed drop-in was simpler than the bespoke HTTP enrollment path. First connection close remains unexplained; retry authenticated. | Enroll keys/policy in Kickstart so no worker password bridge is needed. Preserve the successful standard recovery recipe. |
| One sshd start command ran on Debian workstation and failed | Target labeling/context was easy to confuse; no successful workstation service change shown. | One controller entrypoint; no routine node commands; print execution target on every action. |

The systemd empty-list behavior is in
[version-tagged source](https://github.com/systemd/systemd/blob/v257/src/systemctl/systemctl-list-unit-files.c).
Read-only ISO inspection found packaged sshd.socket ListenStream=22 and
Conflicts=sshd.service. Red Hat presets enable sshd.service, then disable unmatched
units. These facts do not identify the installed node's enabled/active socket;
no native socket root cause should be invented after the fact.

## Testing gaps

Earlier syntax/static checks, namespace packet tests and mocked rollback tests
were useful. They did not exercise a complete install/reboot/key enrollment or
every activation success path. A large passing test count was therefore the wrong
readiness signal. The initial SSH tests mostly rejected malformed inputs and
could not reveal the silent exit on valid empty systemctl output.

After failure,12 enrollment tests included actual Bash execution against temporary
paths/mocked commands, positive success, policy failure and socket cases. Four
hardening tests added successful reload, effective-policy/syntax rejection and
existing-file preservation. Root gates/paths and OS commands were adapted/mocked;
these16 tests are not a real RHEL/OpenSSH/PAM/SELinux install test. They must not be
reported as one. The later fixtures do not retroactively validate the earlier
published script. Success is now evidenced on the physical node only for the
standard ssh-copy-id/hardening route.

Required next evidence: exact RHEL10.2 Kickstart install to disposable disks,
reboot, verified host identity, working key/sudo, bootstrap removal, realistic
service restarts and repeated cleanup. Include wrong disk/MAC, missing package,
failed post-script, unavailable media, controller disconnect, expired/stale plan,
second boot and partial state. Prove failures stop **before** erase where possible;
a failure after partitioning must report partial installation, never claim rollback.
`ksvalidator` is only syntax coverage and does not validate scripts/packages.
[Red Hat validation limits](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/creating-kickstart-files).

A disposable UEFI VM may rehearse the installer with separate action approval.
It is a test fixture, not resurrection of removed VM-cluster support or permission
to touch the preserved historical trial. Real Lenovo firmware/router acceptance
still needs physical evidence.

## Keep, consolidate, retire

**Keep:** verified DVD manifest/read-only media, useful vendor-loader evidence,
shared dnsmasq/nginx/ingress templates, namespace protocol/negative controls,
identity-scoped shutdown principles, sanitized chronological evidence and ignored
private backups/logs. Public-key storage/recovery work is a prerequisite paid once,
not a sequence to repeat for each worker.

**Consolidate:** staging/package preflight/activation/resume/shutdown into an
Ansible-owned controller workflow with one compact result. Present package facts
and safe errors instead of full recaps; avoid both secret-bearing logs and opaque
blanket no_log. Keep staged-file readability, PID parsing and socket behavior as
regression fixtures. Do not preserve every historical mechanism as a required
operator step.

**Retire from the active path after replacement passes:** manual installer GUI
runbook, long BatchA/B heredocs, repeated quarantine instructions and rearm dance,
HTTP publish/update/enroll helpers and their manual checksum choreography.
`harden-ssh.sh` remains a documented recovery tool until installation-time policy
is proven. Existing console-script fixtures can become regression cases when
production helpers are removed; preserve evidence-producing coverage rather than
delete tests merely to make a replacement pass. This retrospective deletes nothing.

**Ownership:** one engineer delivers and rehearses the complete supported path;
operator approves hardware/data loss, exposure, credential custody and stage
transitions. The supported next user experience is plan → approve → network boot
→ progress → verified installed host. Host preparation/RKE2 is a subsequent explicit
stage, not a claim hidden inside “done.” Detailed decisions and acceptance criteria
are in the [design](PROVISIONING-REDESIGN.md).
