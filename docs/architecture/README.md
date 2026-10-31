# Interactive provisioning architecture

## Step index

1. [Prepare offline draft](../../pxe/ansible/README.md) — Render the private plan and blocked Kickstart draft.
2. [Review exact plan; STOP before approval](../../infrastructure/TOMORROW-READINESS.md#pilot-approval) — Confirm the exact target, disk, access and exposure.
3. [Power / BIOS / select network boot](../../pxe/README.md#red-hat-solution-and-nginx) — Select the approved node and boot path.
4. [Kickstart installation](../../pxe/kickstart/README.md) — Install only after validation and approval gates pass.
5. [Reboot to local disk](../../infrastructure/TOMORROW-READINESS.md#installation-and-access) — Start the installed OS without repeating installation.
6. [Verify identity, key login, sudo, readiness](../../infrastructure/TOMORROW-READINESS.md#installation-and-access) — Confirm trusted access and OS readiness.
7. [Disarm / stop / report](../../infrastructure/TOMORROW-READINESS.md#finish) — Stop owned temporary resources and retain the result.

Active strategy: controlled physical worker pilot. Full VM rehearsal/custom
session runner is deferred, not a gate. Step1 produces the blocked draft; final
worker inputs, actual target-file validation and explicit live approval remain.
Keep one workstation host-fingerprint/private-password checkpoint.

LikeC41.60.0 is pinned locally in this documentation project; the lockfile pins its
dependencies. No global tool or system package is required. It is documentation,
not a deployment controller or the parked portal project.

## Open the walkthrough

Prerequisite: Node **22.22.3 or newer** and npm on PATH. Tested with Node24.22.2.
Dependencies are already present in this working directory; for a fresh checkout:

```sh
npm --prefix docs/architecture ci --ignore-scripts --no-audit --no-fund
```

From repository root, the one viewing command is:

```sh
npm --prefix docs/architecture start
```

Then open <http://127.0.0.1:5173>. This starts only a loopback documentation server;
it never invokes PXE/Ansible, contacts a node or changes provisioning state. Stop
it with Ctrl-C. The server has **not** been started during preparation. Syntax,
layout and static build have been tested; browser interaction has not been
manually exercised. No deployment or publishing is configured.

Start at context (`index`), click workstation/node to drill into their scoped
views, pan/zoom, and use the view selector to choose a flow. Click numbered step
notes/links for the matching local runbook section. Each stage explicitly states
**Operator**, **Automation** and **Evidence / stop** in both the step notes and
the linked runbook. Back navigation returns to
context. Links are local to this viewer or official public documentation; no
unpublished GitHub branch URL is required.

## Views

| View | Meaning |
|---|---|
| index | Small context: engineer, workstation, router, physical node, custody |
| workstation_detail | Implemented preparation, observed transport, proposed controller |
| node_detail | Firmware, installer, disk and installed OS |
| operations | **Ordered1–7 proposed journey**: prepare → review/approve → network boot → Kickstart install → first disk boot → verify → disarm/cleanup |
| boot_protocol | Client-initiated DHCP/proxy/TFTP/HTTP **sequence**, reference flow rather than a packet capture |
| installation | Proposed install gates; candidate currently always aborts |
| security_handoff | Actual Ansible bootstrap task order, controller/target execution, evidence and revocation; integration blocked |
| observed_pilot | Actual operator-reported interactive pilot checkpoint and limits |

Green elements are implemented preparation/bootstrap component code; blue are observed pilot roles (not
proof services are currently running); amber are proposed; red are unresolved
stop gates. Titles/descriptions preserve status even without color.

The human handles power/BIOS/network boot and a trusted identity/fingerprint check
when needed. Normal provisioning otherwise belongs on the workstation, without
node command transcription or interactive installer. Considering control-1 again
does not approve its wipe. The exact worker install remains **blocked pending inputs/review/approval**; native
Kickstart/PAM/package behavior will be learned in the controlled physical pilot.

## Sources and validation

- [model.c4](model.c4) and [views.c4](views.c4) are the editable model.
- [Runbook HTML](public/runbook.html) is the actual linked source with anchors for
  steps1–7, operator boundary, credential gate and observed evidence.
- `scripts/prepare-sources.mjs` copies only eighteen explicit nonsecret source files
  into ignored `public/sources/`, so links open the actual current runbook/code
  without depending on GitHub publication. It never recursively copies the repo,
  private inventory, raw journal, credentials or evidence.
- `node_modules/`, generated source copies and `dist/` are ignored; keep model,
  runbook, tool manifest/lockfile and checks in the feature branch.

```sh
npm --prefix docs/architecture run validate
npm --prefix docs/architecture run build
python3 -m unittest discover -s docs/architecture -p 'test_*.py'
```

Validation uses bundled layout tooling; build produces an ignored static site.
No PNG export/browser capture was run because those can start a server. Links use
root-relative paths for the local viewer; deployment under a different base path
would need its own link review and is outside this deliverable.

Follow [vendor guidance](../../infrastructure/RHEL-PROVISIONING-GUIDANCE.md),
[readiness](../../infrastructure/TOMORROW-READINESS.md) and
[PXE preparation](../../pxe/README.md). [LikeC4 CLI](https://likec4.dev/tooling/cli/)
and [dynamic-view syntax](https://likec4.dev/dsl/views/dynamic/) are upstream
references, not provisioning instructions.

## Final documentation direction

During work, keep planned versus implemented versus observed explicit. After
proven rehearsal/installation, consolidate to the tested operator runbook and
matching current-state C4, retiring superseded planning while preserving useful
execution evidence separately. No planning is deleted or marked completed now.
