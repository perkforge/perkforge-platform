# PerkForge Platform handoff

Last updated: 2026-10-26 (America/Chicago; private evidence uses UTC timestamps).

## Start here

Use `/home/corey/src/perkforge-platform`. Read `AGENTS.md`, this handoff and
[the Nextcloud integration runbook](docs/NEXTCLOUD-INTEGRATION.md) before changes.
The separate application checkout is `/home/corey/src/perkforge-tenant-nextcloud`;
its `HANDOFF.md`, `docs/operations.md` and `docs/recovery.md` cover application work.

The initial Nextcloud trial is working and the user confirmed interactive login.
Both repos' changes are published. The earlier activation, secret-bootstrap and
disk-capacity gates are completed for this trial. Do not act on superseded
checkpoints in [the archived session history](docs/handoffs/2026-10-26-session-history.md).

The project is a protected multi-tenant PaaS reference implementation, connecting
working platform capabilities to security controls and evidence. It is not a
formal authorization. Continue using synthetic/replaceable data while physical
ThinkCentre hardware and a verified backup/restore path are pending.

## Current local environment

| Item | State |
|---|---|
| Control VM | `cks-control`, `192.168.122.201`, 2 vCPU, 4 GiB RAM, 30 GiB disk |
| Worker VM | `cks-worker`, `192.168.122.202`, 2 vCPU, 4 GiB RAM, 100 GiB disk |
| Guest platform | RHEL 10.2, SELinux enforcing, RKE2 `v1.36.5+rke2r1` |
| Cluster | Both nodes Ready; repository kubeconfig context `default`, workstation context `rke2-lab` |
| Rancher | `2.15.2`, `https://rancher.local-lab.test`; local admin auth retained |
| Platform Fleet | `fleet-local/local-lab` 5/5; `fleet-local/platform-apps` 4/4 Ready |
| Nextcloud Fleet | `fleet-home-nextcloud/tenant-home-nextcloud` 2/2 Ready |
| Keycloak | Application paused at 0/0; database retained and healthy |
| Observability | Prometheus/Grafana and OpenCost paths disabled after earlier OOM |
| Other active dependencies | Existing GitLab PostgreSQL and Valkey; app itself opt-in |

Host has about 14 GiB RAM; do not increase VM RAM. The earlier OOM killed the
control API server. More recent observed post-trial headroom was about 0.75 GiB
control and 1.1 GiB worker; these are snapshots, not reserved capacity. Review
fresh usage before adding workloads, resuming Keycloak or enabling observability.

The worker was expanded online from 30 to 100 GiB with GPT partition 3, its LVM PV,
root LV and XFS grown. Root is about 95 GiB with about 74 GiB free after expansion;
local-path storage was verified on that filesystem. No physical drive was
repartitioned/formatted and no image cleanup was performed. Metadata backup:
`/var/tmp/perkforge-worker-storage-before.mfc8cD/` on the worker; not a data backup.
`provision-vms.sh` now creates future workers at 100 GiB, with remaining capacity
allocated to root rather than a separate /home. Control stays 30 GiB. Existing-VM
provisioning still leaves disks untouched. A new full rebuild was not exercised.

## Nextcloud identity, ownership and source wiring

| Item | Value |
|---|---|
| Tenant / environment | `home` / `local-vm`, classification `protected` |
| Namespace / Rancher Project | `tenant-home-nextcloud` / `local:p-home-local` |
| URL / application username | `https://nextcloud.local-lab.test` / `home-admin` |
| Tested workload pin | `3feb9b09686d5e1e08e9bf6616f6126335a1653f` |
| Chart / app / DB | Nextcloud chart 9.4.1, image 35.0.2-apache, PostgreSQL 17.6 |
| PVCs | `nextcloud-nextcloud` 4 GiB; `nextcloud-db-1` 2 GiB; both Bound |
| Placement | App, DB and cron on `cks-worker` |

The platform owns namespaces, Projects, quotas, LimitRanges, restricted Pod
Security, NetworkPolicies, deployment RBAC and Fleet registration. Source paths:

- `local-lab/tenant-config/tenants.yaml`: small index with explicit file references.
- `local-lab/tenant-config/tenants/{tenant-alpha,tenant-bravo,home}.yaml`: records.
- `local-lab/fleet/bundles/tenant-foundation/shared/roletemplates.yaml`: shared roles.
- `local-lab/fleet/bundles/tenant-foundation/tenants/<id>/`: generated resources.
- `local-lab/fleet/bundles/nextcloud-support/`: scoped permissions, policies and
  dedicated Rancher FleetWorkspace/Policy/BundleNamespaceMapping.
- `local-lab/fleet/bundles/nextcloud-registration/gitrepo.yaml`: workload SHA pin.

One loader assembles catalog records; the legacy renderer validates them globally. The
split retained the same parent Fleet bundle and all 20 generated resource
identities/content at refactoring time. Do not edit generated tenant files;
regenerate with `python3 local-lab/scripts/render-tenant-foundation.py --write`.
The check-only variant is `--check`. Removing a tenant can delete live resources
after publication and requires the protected lifecycle review.

The application repo owns only `bundles/database` and `bundles/nextcloud`. Fleet
requires `home-nextcloud-deployer` in agent namespace `cattle-fleet-local-system`,
confines it to Home, and disables namespace creation through its dedicated
workspace Policy. Home-labeled bundles map only to existing fleet-local/local.
Rancher owns the workspace namespace; do not declare it again in a competing
bundle. The deployer has no namespace-patch, policy/quota/RBAC mutation or direct
PVC/CNPG deletion authority. It still has significant tenant-local deployment
and Secret authority. Home receives no synthetic tenant dashboard-role bindings.

GitRepo keepResources, namespace-deletion defaults and Helm keep annotations
reduce accidental deletion; they do not protect against all controller actions,
cluster admins, disk loss or a VM rebuild. Later docs-only app commits do not
require advancing the tested workload pin. Use GitOps for declarative changes.

## Application operation and access

Current limits: app 512 MiB, DB 320 MiB, cron 128 MiB; PHP 192M and 64-MiB opcode cache.
One Apache worker uses KeepAlive Off to avoid idle backend connections starving
browser assets/probes. The non-root init container prepares PVC subdirectories as
UID33/mode0770. A scoped one-time repair corrected initial root-owned directories
without deleting their contents. The trusted hostname is explicit and a startup
hook sets Cron mode. CronJobs run every 5 minutes, Forbid concurrency, 900-second
deadline. Single-instance CNPG requires unsupervised update strategy; reviewed
Git pins control upgrades. This is a low-concurrency VM trial, not a load-tested
or highly available service.

Credentials are only in ignored owner-only platform files:
`.secrets/nextcloud/nextcloud-admin-password` and
`.secrets/nextcloud/nextcloud-db-app-password`. Kubernetes Secrets are immutable.
Never print or commit values, rotate them during a retry, or use the DB password
as an application password. The account is `home-admin`, not `admin`.
Public self-signed certificate export: `.secrets/nextcloud/public-tls.crt`.
Verify/import it for normal client trust; re-export after certificate rotation.

User confirmed login is working. Last observed workstation resolution for
`nextcloud.local-lab.test` is 192.168.122.201; authenticated WebDAV passed through
both .201 and .202. Automated browser tests used a temporary .202 override. The
assistant did not alter hostname resolution, router, firewall or bridge settings.
There is no pending hosts change needed for the user's now-working access.
An independently verified second LAN-client route remains untested: workstation
LAN was 192.168.1.183/24, VMs use libvirt NAT 192.168.122.0/24. Do not infer public
or LAN-wide reachability from local access; separately approve new network paths.

## Verified evidence and remaining work

Passed: app 1/1, CNPG healthy 1/1, both PVCs Bound, certificate Ready, Fleet 2/2,
verified-certificate HTTPS/WebDAV upload/download, matching checksum after an
app-only pod restart with identical PVC/volume IDs, ephemeral browser login to
the dashboard, user-confirmed login, successful scheduled CronJobs, UID33/no API
token, selected cross-tenant authorization denials and deployer permission denials.
Both ingress IPs accepted the same credentials during the login recheck.
Browser automation used a local-only TLS bypass; HTTPS/WebDAV verified the public
certificate. No browser state, screenshots, traces or credentials were published.

Private evidence is in the application repo's ignored `.evidence/`, notably
`smoke-20261027T011531Z/summary.json` and
`browser-20261027T012251Z/summary.json`. Initial failed attempts and the first
failed CronJob remain historical evidence; subsequent runs succeeded. Preserve
existing platform `local-lab/evidence/`, `.orig` files and untracked caches.
The offline unit suite was not rerun for this change; authorized live trial
checks, rendering, compilation and syntax/whitespace checks were performed.

Next priority: approve a backup destination outside both VM disks, take matching
PostgreSQL/application-volume/credential backups and verify an isolated restore.
No destination, schedule, retention or successful restore exists. Until then use
replaceable data. Also pending: broader network-denial enforcement, independent
LAN-client access, database-pod/node-failure recovery, multi-user load and full
protected lifecycle enforcement. Selected earlier platform tenant checks passed
(RBAC 94/94, admission 9/9, quota 4/4, network 7/7); these do not establish the new
Home tenant's entire runtime boundary or formal authorization.

The broader platform's Phase 6 work includes candidate findings, the private local
findings register and catalog access lifecycle states. Those are not a scheduler,
alerting service, full session revocation, paused tenant GitOps or data-safe
decommission. Offboarding retains workloads/data. See security workflow, tenant
boundary, Phase 6 review and control-evidence docs; historical detail is archived.

## Safe resume and boundaries

Start read-only:

```sh
kubectl get nodes
kubectl get gitrepos -A
kubectl get deployments,clusters.postgresql.cnpg.io,pvc,certificates,jobs -n tenant-home-nextcloud
kubectl get statefulset -n keycloak
python3 local-lab/scripts/render-tenant-foundation.py --check
```

Read the app handoff before changes. Do not use the existing full platform
profile/rebuild scripts as a Nextcloud health check: they still assume Keycloak
is running. A rebuild deletes both VM disks, including protected Home data.
Future destructive operations need action-specific approval and the applicable
backup/disposability decision; the completed deployment authorization is not a
blanket wipe permission. Worker-size settings are persisted for a future approved
rebuild, not a request to run one now.

Never print/commit `.secrets/` values or kubeconfigs. Direct `.secrets/rke2.yaml`
is the source and uses context `default`; `~/.kube/config` has verified
`rke2-lab`, not the earlier broken Rancher proxy contexts. Context names belong
to their respective files; use `--context default` with `.secrets/rke2.yaml`. Rancher local admin remains the recovery identity while
Keycloak is paused. Mattermost has no seeded admin password; first registration
creates its admin, and its DB password is not a UI login.

The old checkout `/home/corey/src/homelab` was removed. `origin` is public
perkforge/perkforge-platform; `source` retains archived coreyperkins/homelab.
Do not delete the archived repo or physical/external disks. Root `ansible/` is
for future physical hosts; `ansible/aws-lab/` is separate and has no applicable
provision/start/teardown/budget authorization. Do not mix its inventory with the
VM or physical environment. Follow AGENTS.md commit/push and test permissions.

## Portal draft — native Fleet configuration

Portal uses `local-lab/tenant-config/enrollments/home.yaml`, shared values and the existing
Home `foundation` overrides plus separate `applications.portal` restrictions, rendered directly by Fleet from `templates/`.
There is no Python portal generator or authored chart. The legacy foundation renderer
and its 16 outputs are unchanged; wider Python cleanup follows successful integration.
Portal is disabled, without an image/allocation, and its bundle is not in the live
GitRepo paths. `KUBECONFIG=/dev/null fleet test -f enrollments/home.yaml -N local local-lab/tenant-config`
with pinned Fleet0.16 renders nothing. Python remains useful for offline tests.
See `docs/PORTAL-INTEGRATION.md` for lifecycle review gates and activation blockers.
No live portal/identity/security resource was changed or activated by this draft.

Portal preparation: installed Fleet agent v0.16.2 is now the offline CLI/schema target.
Release-storage create/update/delete plus portal envelope admission are prepared only.
See docs/PORTAL-RELEASE-STORAGE.md for activation order and the conditional cleanup finding. The local
portal image is preloaded on both nodes, but the catalog remains disabled/unselected,
with no image/allocation activation. No live security change accompanies this review.
