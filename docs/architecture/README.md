# Physical provisioning architecture

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
