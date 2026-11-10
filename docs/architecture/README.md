# Architecture by audience

- **Tenants:** [onboarding and boundaries](../tenant-architecture/README.md), three terse views.
- **Security reviewers:** [architecture and rationale](../security-architecture/README.md), six views and a [control evidence/gap map](../security-architecture/controls.md).
- **Operators:** the physical provisioning and application procedures below.

Reviewed 2026-11-09 against source commit `ae3b74b94c83f0bf909a798ea797e049c269fe8c`.
The [audience manifest](audiences.json) records source roots, status semantics,
proposed owners and pending disclosure approval. No live assessment ran.

## Operator provisioning views

Use context first, then narrow into components or an operating flow. The single
[human-operated procedure](../../pxe/README.md) contains full commands; the linked
[viewer notes](public/runbook.html) explain roles and completion boundaries.
[HANDOFF.md](../../HANDOFF.md) holds current readiness.

## Step index

1. [Prepare reviewed PXE configuration](public/runbook.html#prepare) — Review target, network, media and fresh private configuration.
2. [Review target, disk and action scope](public/runbook.html#approve) — Confirm selected node, disk, data loss and access scope.
3. [Activate PXE and select network boot](public/runbook.html#boot) — Start reviewed services and reach the indefinite GRUB menu.
4. [Install RHEL with reviewed settings](public/runbook.html#install) — Review layout and accounts before committing the installation.
5. [Restore disk-first and boot installed OS](public/runbook.html#firstboot) — Restore firmware order and verify the installed disk boots.
6. [Verify identity, key login and sudo](public/runbook.html#verify) — Establish trusted access and verify fresh login and sudo.
7. [Stop owned services and retain evidence](public/runbook.html#cleanup) — Verify scoped shutdown and preserve original services and evidence.

## Navigate

| View | Purpose |
|---|---|
| queued_app_identity | Proposed app clients, native tenant boundaries, machine identities and recovery |
| production_tls_lifecycle | Proposed PKI ownership, client trust, scoped leaf delivery and lifecycle acceptance |
| index | Operator, workstation, router, selected node, custody and platform |
| topology | Workstation/control-1/worker-1/worker-2 on the shared wired LAN |
| workstation_detail | Inputs, dedicated services, ingress, SSH and state ownership |
| workspace_detail / workspace_construction | Human input → fresh offline working files |
| node_detail | Firmware, menu, interactive installer, disk and OS |
| operations | Ordered operator process and completion checks |
| boot_protocol | DHCP/proxy/TFTP/HTTP reference sequence |
| installation | Manual layout/account review and disk commitment |
| security_handoff | Physical trust, public-key enrollment and fresh access checks |
| service_lifecycle | Preflight, identity, exposure and scoped stop |
| storage_acceptance | Ordered approved PVC write/recreation/reattachment/replica test and retention gate |
| storage_detail | Optional Longhorn claims, worker replicas, independent backups and activation boundaries |
| rke2_detail | Server/workers, Canal/DNS/Traefik, administrator access and recovery |
| bootstrap_installer_flow | Release → shared/package prerequisites → Flux/Big Bang → delegated installer → runtime and acceptance |
| rancher_local_admin | Planned release/inputs/delegation → Big Bang/Flux → trusted HTTPS/local admin; no SSO |
| external_secrets_boundary | Inactive native ESO trust, scoped Stores, exact auth and stronger-isolation alternative |
| platform_detail | Separate readiness and RKE2/Rancher/Flux/Big Bang ownership |

Actual IP/MAC values and SSH identity references remain in ignored
`infrastructure/ansible/inventory/.topology.yml` beside the public inventory skeleton.
The private file is never copied into viewer assets or public source links.
These views are architecture, not a live status dashboard or approval.

The existing platform view links [installer ownership and release promotion](public/runbook.html#bootstrap-ownership): current Ansible-applied Kubernetes prerequisites versus the deferred scoped Flux foundation in [#95](https://github.com/perkforge/perkforge-platform/issues/95), coordinated with [#14](https://github.com/perkforge/perkforge-platform/issues/14). These notes do not add a rollout gate.

## View and validate

Requires Node >=22.22.3/npm. LikeC4 1.60.0 is locked locally; install dependencies when
needed; dependencies and generated build folders remain local and untracked.

```sh
npm --prefix docs/architecture ci --ignore-scripts --no-audit --no-fund
npm --prefix docs/architecture start
```

Open <http://127.0.0.1:5173>; stop with Ctrl-C. This is a loopback documentation
viewer and never invokes provisioning or contacts a node. Source links use an
explicit implementation/runbook allowlist, not private working directories.

```sh
npm --prefix docs/architecture run validate
npm --prefix docs/architecture run build
python3 -m unittest discover -s docs/architecture -p 'test_*.py'
```

Keep model.c4, views.c4, the HTML notes, source-copy helper, package lock and focused
checks. Generated sources/dist/dependencies are disposable. Do not add planning,
session journals, historical copies or archive folders here.

## Authorization review navigation

Start with `authorization_roles`, then the smaller `authorization_core_apps`,
`authorization_observability`, `authorization_collaboration` and
`authorization_tenant_apps` views. `authorization_review` gives ordered ownership
and acceptance gates. The [role/app matrix](../../big-bang-bootstrap/configuration/authorization/MATRIX.md)
separates confirmed intent, offline examples, existing code evidence and unimplemented
app/edition/enforcement decisions. These views create no identities or permissions.

## Audience builds

The operator root (`docs/architecture`), tenant root (`docs/tenant-architecture`)
and security root (`docs/security-architecture`) are independent LikeC4 inputs.
The pinned package above validates/builds all three; outputs are local and ignored:
`dist` (operator), `dist-tenant` and `dist-security`. Audience builds first clear
their own ignored output directories to prevent stale assets; never store hand-authored
files there. No build deploys a site.
Tenant/security builds do not copy the operator `public` directory or its source
allowlist. The build inspects all emitted files for expected views, other-audience
markers, copied operator assets and private-path/key markers; this is a focused
regression check, not a substitute for disclosure review. Do not combine these outputs into a public or tenant download.

```sh
npm --prefix docs/architecture run validate:audiences
npm --prefix docs/architecture run build:audiences
```

For a local tenant-only viewer, after installing the pinned dependencies:

```sh
docs/architecture/node_modules/.bin/likec4 serve docs/tenant-architecture --listen 127.0.0.1 --port 5174
```

Serve the security root separately on a different loopback port when needed.
Do not host the common parent directory. All checked-in audience models are
sanitized candidates; separate builds are a disclosure boundary, **not an access
control system**. Restricted evidence/private operational models must stay out
of all three browser payloads. Future restricted delivery requires authorized
storage and server-side access checks before bytes are sent, not role-based UI hiding.

### Review and publication contract

1. Change a model with its owner source: update status, source links, review date,
   reviewed commit, README and evidence gaps in the same MR. Unverified stays
   unverified until a target/revision/time-bound result exists.
2. Platform/package owners verify accuracy; identity/network owners review their
   boundaries; the security owner reviews control claims; system/data owners approve
   disclosure. These are proposed responsibilities, **not completed owner sign-off**.
3. Review the exact exported payload, including scripts, source maps and static
   assets. Tenant assets must contain neither security nor operator models. Do not
   attach inventories, raw logs, credentials, physical addresses or private paths.
4. Build and test each audience independently. After approved publication, record
   the release/commit and authorized destination. A successful local build is not
   publication approval and does not close [#81](https://github.com/perkforge/perkforge-platform/issues/81).

[Portal Explorer #10](https://github.com/perkforge/perkforge-portal/issues/10) and
[draft #11](https://github.com/perkforge/perkforge-portal/pull/11) can reuse the tenant
model and status/metadata contract. They must not import the security/operator
model into tenant bundles or treat client-side workspace visibility as authorization.
No portal files or access policies change here.

### Documentation inventory and ownership

| Source | Audience / authoritative scope | Review result and next owner action |
|---|---|---|
| Root README and this index | Everyone: find the right audience, not current health | Updated to separate audience entrypoints. |
| Tenant README and model | Sanitized tenant onboarding, responsibilities and isolation limits | Source-reviewed; full tenant acceptance and disclosure sign-off remain open. |
| Security README, control map and model | Sanitized security rationale, authority, intake/maintenance/promotion journeys | Source-reviewed; no ATO or live-control claim. Assign owners and resolve linked gaps. |
| Existing operator model/views/runbook | Physical provisioning, scoped operations and historical acceptance | Retained source links and focused regressions. Historical observations must not be generalized to current state. |
| HANDOFF and package/SSO runbooks | Operators: bounded observations and supported procedures | Evidence is revision/time-specific and contains historical sections; not a live status dashboard. Do not copy these wholesale into tenant assets. |
| Platform maintenance, targets, profiles and TLS docs | Maintainers: authoritative change procedures and proposed TLS contract | Reused, not duplicated; coordinate #77/#44/#45. |
| CI documentation and workflow source | Maintainers: validation behavior | Added explicit current pause; retained historical measurements. Gates unchanged. |
| Role matrix, tests and evidence tooling | Boundary owners / reviewers | Distinguish source fixtures, bounded historical acceptance and missing live denial/restore evidence. |
| Portal draft Explorer | Separate application-owned delivery | Existing sanitized draft retained; model ownership/disclosure and restricted-delivery design still pending. |

Coordination stays with [#21](https://github.com/perkforge/perkforge-platform/issues/21),
[#43](https://github.com/perkforge/perkforge-platform/issues/43),
[#44](https://github.com/perkforge/perkforge-platform/issues/44),
[#45](https://github.com/perkforge/perkforge-platform/issues/45),
[#77](https://github.com/perkforge/perkforge-platform/issues/77),
[#79](https://github.com/perkforge/perkforge-platform/issues/79) and
[#80](https://github.com/perkforge/perkforge-platform/issues/80). This does not expand
#75 or implement the CLI, intake, promotion, networking, mesh or live integrations.
