# Physical RHEL architecture and repeat procedure

Start at the C4 context, narrow into workstation/node/platform, then follow the
ordered operating procedure. This viewer contains architecture, responsibilities,
repeat settings and completion checks. Session state and execution history belong
in [HANDOFF.md](../../HANDOFF.md) and the
[execution journal](../../infrastructure/EXECUTION-JOURNAL.md).

## Step index

1. [Prepare reviewed PXE configuration](public/runbook.html#prepare) — Review target, network, media and fresh private configuration.
2. [Review target, disk and action scope](public/runbook.html#approve) — Confirm selected node, disk, data loss and access scope.
3. [Activate PXE and select network boot](public/runbook.html#boot) — Start reviewed services and reach the indefinite GRUB menu.
4. [Install RHEL with reviewed settings](public/runbook.html#install) — Review layout and accounts before committing the installation.
5. [Restore disk-first and boot installed OS](public/runbook.html#firstboot) — Restore firmware order and verify the installed disk boots.
6. [Verify identity, key login and sudo](public/runbook.html#verify) — Establish trusted access and verify fresh login and sudo.
7. [Stop owned services and retain evidence](public/runbook.html#cleanup) — Verify scoped shutdown and preserve original services and evidence.

## Navigate the architecture

| View | Purpose |
|---|---|
| index | System context: operator, workstation, router, node, custody and platform |
| workstation_detail | Configuration, dedicated PXE/HTTP services, ingress, SSH and evidence |
| node_detail | Firmware, menu, installer, disk and installed OS |
| operations | Ordered repeat process with operator, automation and completion checks |
| boot_protocol | DHCP/proxy/TFTP/HTTP sequence and menu/installer boundary |
| installation | Interactive disk, layout, account and installation review |
| security_handoff | Host trust, public-key enrollment, policy validation and fresh access |
| service_lifecycle | Preflight, identity, exposure, recovery, shutdown and retained evidence |
| platform_detail | Separate readiness and RKE2/Rancher/Flux/Big Bang/repository ownership |

Click workstation, node or platform from context to drill down; use the view
selector for focused flows. Numbered notes link to the matching
[runbook sections](public/runbook.html); return to context with back navigation.
Diagrams are an operating contract, not a live health/approval dashboard.

The active repeat procedure is interactive Anaconda over the existing PXE
transport. The separate offline Kickstart candidate is intentionally blocked;
fixture-tested access components are not an unattended deployment path. Keep this
capability boundary without expanding the viewer into implementation proposals.
The runbook states what still requires manual action or separate approval.

## Open locally

Node22.22.3 or newer and npm are required; validated with Node24.22.2.
LikeC41.60.0 and dependencies are pinned in the project lockfile. On a fresh checkout:

```sh
npm --prefix docs/architecture ci --ignore-scripts --no-audit --no-fund
```

Start the documentation viewer:

```sh
npm --prefix docs/architecture start
```

Open <http://127.0.0.1:5173>; stop with Ctrl-C. The viewer binds loopback only and
never invokes provisioning, contacts a physical node or changes cluster state.
No hosting/publishing is configured. Static layout/build is checked; browser
interaction has not been manually verified.

## Source and validation

[model.c4](model.c4), [views.c4](views.c4) and
[runbook.html](public/runbook.html) are the editable architecture and procedure.
The source-copy script uses an explicit allowlist of implementation files;
no recursive repository copy, inventories, session logs, credentials or planning
papers are exposed. Generated source copies, dependencies and dist are ignored.
The existing implementation and evidence-producing tests remain in their original
locations; this cleanup changes documentation only.

```sh
npm --prefix docs/architecture run validate
npm --prefix docs/architecture run build
python3 -m unittest discover -s docs/architecture -p 'test_*.py'
```

Keep new architecture concerns at the appropriate level and link down to precise
operating details. Keep chronological checkpoints, approval transcripts, failed
experiments and implementation backlogs outside this viewer. Preserve those
records in their existing handoff, journal or historical locations.
