# Interactive provisioning architecture

LikeC41.60.0 is pinned locally in this documentation project; the lockfile pins its
dependencies. No global tool or system package is required. It is documentation,
not a deployment controller or the parked portal project.

## View tomorrow

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
| security_handoff | Public key versus protected secret delivery; credential choice pending |
| observed_pilot | Actual operator-reported interactive pilot checkpoint and limits |

Green elements are implemented preparation; blue are observed pilot roles (not
proof services are currently running); amber are proposed; red are unresolved
stop gates. Titles/descriptions preserve status even without color.

The human handles power/BIOS/network boot and a trusted identity/fingerprint check
when needed. Normal provisioning otherwise belongs on the workstation, without
node command transcription or interactive installer. Considering control-1 again
does not approve its wipe. Current automated installation remains **not ready**.

## Sources and validation

- [model.c4](model.c4) and [views.c4](views.c4) are the editable model.
- [Runbook HTML](public/runbook.html) is the actual linked source with anchors for
  steps1–7, operator boundary, credential gate and observed evidence.
- `scripts/prepare-sources.mjs` copies only seven explicit nonsecret source files
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
