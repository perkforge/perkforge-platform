# Current operator handoff

Provisioning remains paused; the operator separately approved the disposable
workload smoke, off-node snapshot and sequential reboot checks described below. Use this existing feature
worktree; never push main or merge. Publish changes only when explicitly requested.

## Current state

- control-1, worker-1 and worker-2 run RHEL 10.2 and RKE2 v1.36.5+rke2r1.
  Installation completed without failures; the final API checks showed all three
  nodes Ready and all running kube-system pods ready. Completed bootstrap Jobs
  are expected. This records the last verification, not continuous live status.
- control-1 supplies the control plane and embedded etcd. Both workers are agents.
  This is a single-server cluster, not HA. Canal, CoreDNS, Traefik, metrics-server
  and the snapshot controller are installed. No Rancher, Flux, Big Bang or
  application activation was performed in this session.
- All nodes are registered with Red Hat; BaseOS/AppStream are enabled. Approved
  host preparation installed prerequisites, persisted modules/forwarding/bridge
  settings, excluded Canal interfaces from NetworkManager and stopped/disabled
  firewalld. SELinux remains enforcing; no active swap; time is synchronized.
- Key-only SSH and password-authenticated sudo are verified. Root/password SSH
  are disabled. Each OS disk has 600 MiB EFI, 2 GiB XFS /boot and remaining XFS
  root on LVM. All three completed connected sequential OS reboots and recovered
  SSH/RKE2. The test changed no firmware settings and did not verify every possible
  firmware boot path.
- Dedicated workstation PXE services/listeners/guard are stopped. Verified media
  and native runtime records remain outside this repository. Documentation work
  does not authorize changing those resources or any node.

## Local custody

Actual addresses/MACs and SSH references are only in ignored
`infrastructure/ansible/inventory/.topology.yml`; existing verified trust is in
ignored `known_hosts.local` beside it. Private SSH keys remain outside this tree.
Public C4 views show relationships without physical identifiers.

Ignored `.rke2-state/` beside the inventory holds protected installation inputs,
agent credential, cluster marker, bundled client, kubeconfig and complete separate
server/agent token exports. Directories are mode0700; credential files mode0600.
The requested `rke2-state.zip` beside it is also ignored and mode0600, but is not
encrypted. Do not publish either. Independent password-manager custody has not
been confirmed. The default workstation `~/.kube/config` was explicitly replaced
with the RKE2 configuration and verified; it is mode0600.

The server token must accompany matching etcd snapshots for recovery. The token
ZIP is not an etcd backup. A separate verified off-node snapshot/token bundle now
exists on the workstation as recorded below; no restore test or encrypted/off-site
copy has been performed. Keep local credentials until independent custody is confirmed.

## Repeat and resume

Use [PXE/RHEL procedure](pxe/README.md), [RKE2 procedure](infrastructure/ansible/RKE2.md)
and [C4 views](docs/architecture/README.md). Configuration belongs in Ansible/YAML;
private inputs and credentials remain ignored. Host preparation refuses an
existing RKE2 installation; do not rerun it on the installed cluster. Token export
refuses to overwrite existing exports.

The approved live workload smoke test passed with zero failures: two Ready pods on
separate workers, four DNS checks, two cross-worker direct HTTP checks and four
ClusterIP/service-DNS HTTP checks. Owned namespace cleanup completed. Private
summary/diagnostics are in ignored .rke2-state/workload-smoke-v3xg8pd0/. Offline
mock checks separately cover default/check refusal, wrong cluster, existing
namespace, failed probes and foreign-namespace cleanup refusal. The test source is
in infrastructure/ansible/tests/workload-smoke.yml and fixtures/workload-smoke.yaml.

The approved etcd backup check completed with zero failures. A fresh uncompressed
snapshot and its unchanged matching server token are in ignored
.rke2-state/etcd-backup-fryzm4_n/ (snapshot.db, server-token.secure, summary.yml).
Source/copy size and SHA256 matched; the embedded SHA256 trailer passed. Bundle
mode0700 and file modes0600 were verified. All three nodes remained Ready. This
proves snapshot capture, protected off-node transfer and byte integrity, not bbolt
consistency or restore success. No service restart, token rotation, cloud upload,
snapshot pruning or configuration change was performed. The earlier ZIP was not
refreshed and does not contain this new snapshot. Source and repeat commands are
in tests/etcd-backup.yml and RKE2.md under infrastructure/ansible. Offline tests
separately cover default/check refusal, wrong-cluster refusal, token change during
snapshot, protected exports and corrupt/missing/truncated integrity hashes.

Approved sequential reboot verification completed in order worker-1, worker-2,
control-1, with no task failures. Each returned over SSH with a changed boot ID,
its enabled RKE2 service started automatically, and the API reported the new boot
ID plus Ready before proceeding. API/datastore readiness, unchanged cluster UID,
SELinux, modules, forwarding/bridge settings and NetworkManager were verified.
Independent fresh SSH also confirmed firewalld inactive/disabled and RKE2
active/enabled on every host. Control-1's reboot caused expected temporary API
unavailability; its service startup completed without manual intervention.

Private per-node boot-ID evidence and progress are in ignored
.rke2-state/reboot-verification-opc6lkcp/. The post-reboot workload smoke check
passed all DNS/direct-pod/ClusterIP probes and verified owned namespace deletion;
its private evidence is .rke2-state/workload-smoke-0wz7xqpz/. Source and repeat
commands are in tests/reboot-verification.yml, tests/reboot-node.yml and RKE2.md
under infrastructure/ansible. Offline mocks separately verify default/check mode,
wrong-target refusal, worker-first ordering and stopping after first-node failure
or a stale API boot ID. These are distinct from the successful live checks.

Read-only storage assessment: no StorageClasses, PVs or PVCs exist. Each node has
one roughly 256GB NVMe with XFS root shared by OS/RKE2; about 226–227GiB remains
free, six CPUs and about 15GiB RAM. Links report 1 Gbps; no NAS is available.
Worker storage prerequisites are installed as detailed below. Current selected packages are Headlamp
and Keycloak; the authored Keycloak database claim is 4GiB on a retained static
local-identity PV, with worker/path still placeholders. Its advertised capacity is
not a filesystem quota. No storage backend, directory, quota, package or disk was
changed. The later growth scope includes Harbor image retention, portal PostgreSQL,
Nextcloud personal files/photos and OpenBao. Proposed storage baseline is Longhorn
with two worker replicas and an initial 80–100GiB logical budget, with independent
backups and later dedicated worker SSDs as growth requires; see infrastructure/README.md.
Longhorn and Rancher are now prepared as optional unselected Big Bang packages.
Their child HelmReleases and the outer release/seed remain suspended. No bootstrap,
node labels or platform resources changed in that source-only preparation. Later approved worker host preparation is recorded below.
Longhorn is pinned 1.13.0 with worker-only placement, two hard-separated replicas,
Retain/nondefault StorageClass and disk headroom settings. Keycloak has an alternate
Longhorn PVC overlay and readiness dependency. Rancher is pinned 2.15.2, strictly
TLS, required external bootstrap-values Secret, no fabricated storage dependency.
Its old direct infrastructure installer is removed; gated API/OIDC administration
now lives under Big Bang bootstrap Ansible. Privileged installer RBAC and
namespace prerequisites are staged separately for review. Activation requires
read-only host compatibility checks, explicit host/disk/label preparation, DNS/TLS/
credentials and reviewed source selection/unpause. No live install is approved. Application PV
contents need their own backup; the verified etcd snapshot does not contain them.

The operator selected Longhorn for growth and requested this intermediate source
commit/push before any bootstrap. The approved read-only Longhorn host audit completed; protected evidence is in
.rke2-state/longhorn-preflight-jkilmqcb/. Both workers have matching hostnames,
XFS/shared propagation, six CPUs, about 15GiB RAM and 227GiB free. This initial audit identified missing host prerequisites; the completed maintenance
and post-preparation audit below supersede those gaps. Worker labels remain
absent and runtime contexts/I/O remain unverified. SELinux remains enforcing. This is not
installation readiness. The reusable command is in the Longhorn package README.
Node names, hostname labels and RKE2 hostname annotations match control-1,
worker-1 and worker-2; no custom test annotation keys were observed. Review
controller-owned metadata before any cleanup. No live metadata was changed. Actual PVC write/recreate/reattach/replica-health testing must
wait until later approved Longhorn bootstrap. Keep Rancher Helm separate from its
OIDC API step: DNS/TLS before Helm, ready Keycloak before SSO configuration.
Restore validation and independent encrypted/off-site custody also remain outstanding. Smoke success does not establish ingress, policy isolation, durable
storage or recovery. No further live action is authorized by this handoff. Keep architecture and human repeat instructions,
not session journals, planning archives or duplicate procedure documents.

Authored metadata review replaced the illustrative selection prefix with
platform.perkforge.io and package stage labels with standard component labels.
The seed/release verifier now require the same prefix. Downstream enrollment/app
metadata and release compatibility still require coordinated review before any
activation. Local example.test URLs and worker selectors remain unresolved inputs;
choose the actual DNS suffix and scheduling placement consistently across values,
identity/routing and RKE2 OIDC settings before bootstrap.

Approved worker-only Longhorn prerequisite maintenance completed sequentially,
with zero failures. Protected run evidence is in
.rke2-state/longhorn-host-preparation-bbomy7w9/ and the successful follow-up audit
is .rke2-state/longhorn-preflight-2mdne6_j/. Both workers now have pinned iSCSI
6.2.1.11 plus NFS/cryptsetup/setools tools, persistent loaded iscsi_tcp,
active/enabled iscsid and root-owned mode0700 /var/lib/longhorn. Both host audit
unmet-check lists are empty. SELinux remains enforcing and all three nodes remain
Ready. Separate read-only policy queries confirmed iscsid_t dac_override and
container_t-to-spc_t unix socket connectto permissions on both workers. A direct
iscsid_t-to-container_file_t directory query returned no rule; this is not by itself
a demonstrated runtime failure. Actual process contexts/AVCs and PVC I/O still
require later Longhorn validation. No policy workaround, node labels, control-plane
change, RKE2 restart or bootstrap was performed. Node labels require separate
approval. Maintenance source and repeat instructions are retained with the infrastructure procedure.

Rancher cleanup removed the direct infrastructure Helm installer, values and
installer-only tests. OIDC tasks/defaults/playbook and the retained safety tests/CLI
fixture moved under big-bang-bootstrap; platform-owned resources use the
platform-ansible ownership value. No Rancher resources have been installed or
configured, so no live ownership migration occurred. RKE2 vendor paths stay intact.
