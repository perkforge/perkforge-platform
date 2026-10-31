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
and post-preparation audit below supersede those gaps. Worker label completion is recorded below; runtime contexts/I/O remain unverified. SELinux remains enforcing. This is not
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
activation. The local DNS suffix is now perkforge.home.arpa; Headlamp, Keycloak,
Rancher and OpenBao use their short application names under it. Authored values,
identity/routing and RKE2 OIDC issuer agree. Worker placement remains unresolved.
DNS records/ingress endpoint, TLS issuance and trust are not configured by these
source changes and must precede bootstrap.

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

The approved worker-label operation completed with zero failures using
infrastructure/ansible/playbooks/label-longhorn-workers.yml. Read-back confirmed
storage.perkforge.io/worker=true and node.longhorn.io/create-default-disk=true on
worker-1/worker-2 only; both labels remain absent on control-1. All three nodes
remain Ready. No Longhorn installation, disk creation, PVC or bootstrap occurred.
The operation remains default-off and identity/readiness/conflict guarded.

Read-only DNS/ingress review: workstation DNS is supplied by the router. The
RKE2-managed rke2-traefik DaemonSet is ready on all three nodes and binds host ports
80/443; its service is ClusterIP. Router model/custom DNS capabilities and the
selected LAN ingress endpoint remain undecided. No records, forwarding, CA/trust,
service configuration or application routes were applied.

Approved DNS-only host installation on control-1 completed with zero failures.
The dedicated perkforge-lab-dns service is active/running, enabled for boot and
configured Restart=on-failure. DNS binds only the server LAN IPv4 on TCP/UDP53;
no wildcard/IPv6 listener was observed. The four application names under
perkforge.home.arpa resolve to worker-1's Traefik endpoint. Workstation direct
queries passed all eight application/transport checks, unknown-local NXDOMAIN,
local AAAA NODATA and ordinary gateway forwarding. SELinux remains enforcing and
all three Kubernetes nodes remain Ready. Boot enablement was verified; an actual
DNS-service reboot recovery test has not been run.

Protected installation evidence and LAN verification are in
.rke2-state/lab-dns-install-gnnx3hvx/. The earlier attempt stopped at rejected sudo
without host changes; its evidence is preserved. The first-install playbook refuses
existing managed files, so do not rerun it for maintenance. Router DHCP and node DNS settings remain unchanged; approved workstation
resolver completion is recorded below. Client resolver migration (workstation and
three nodes), cluster/host-network lookups and private-CA/TLS remain separate
reviewed actions. No Big Bang/Flux or application activation was performed.

Approved workstation DNS migration completed. The existing standalone dnsmasq
service, already enabled for boot, now routes only perkforge.home.arpa to control-1
and other queries to the explicit gateway. The wired NetworkManager profile uses
loopback DNS with negative IPv4 DNS priority and ignores automatic DNS from both
address families. A lingering RA-supplied IPv6 gateway resolver after reapply was
excluded by the priority correction; IPv6 networking remains enabled. Final active
resolv.conf contains only 127.0.0.1. All four application names passed normal DNS
and OS lookup; ordinary internet lookup passed. Protected inputs/logs/verification
are in .rke2-state/workstation-dns-doxbigdu/. No node/router resolver, DHCP or
libvirt change was made. Workstation reboot recovery/browser DoH are untested.
Repeat/rollback source is configure-workstation-dns.yml under infrastructure/ansible/playbooks.

Approved node DNS migration completed worker-1, worker-2, control-1 with no failures.
Each node now has only control-1's LAN address in resolv.conf, with persistent
NetworkManager DNS properties, automatic DNS ignored and priority -50. All four lab
names and public lookup passed on every host, RKE2 stayed active and all nodes
remained Ready. Protected original properties and run evidence are in
.rke2-state/node-dns-vj1_v5ix/. IPv6 networking, router and workstation settings were
not changed in this operation. Node reboot recovery has not been tested for DNS.

The separately approved CoreDNS rolling refresh completed using
infrastructure/ansible/playbooks/refresh-coredns.yml. Both replacement replicas are
updated, Ready and available, and all three nodes remain Ready. Read-only
infrastructure/ansible/tests/coredns-resolution.yml passed eight lab UDP/TCP
queries, internal Kubernetes service discovery and public forwarding through the
CoreDNS service from control-1. Private results are in
.rke2-state/node-dns-vj1_v5ix/coredns-after-refresh.yml. Protected repeat inputs
remain .rke2-state/coredns-refresh.yml. No disposable pod, static/API pod restart,
RKE2 restart or API-authentication change was performed. Workload-specific and
host-network DNS policies, API OIDC, node reboot persistence and TLS remain
separate validation. Source and repeat verification commands are retained in the repository.

Approved local CA/certificate issuance completed with zero failures using
infrastructure/ansible/playbooks/create-lab-pki.yml. The protected bundle is
.rke2-state/lab-pki-issuance-zvxj1r56/lab-pki-995bzln4/ with encrypted RSA4096
root key, public root certificate and four RSA3072 exact-hostname one-year service
certificate/key pairs. Passphrase entry was local/hidden and not saved. Independent
verification passed root-key encryption, mode0700 directories/mode0600 keys,
unique leaf serials, hostname/chain/server-purpose checks, expiry and matching keys.
Synthetic offline tests separately covered issuance/default refusal and wrong-host
rejection. Public summary/fingerprint and private verification are in the bundle;
no credential contents belong in tracked configuration. The root remains encrypted
on the workstation; independent/offline backup and passphrase custody are not
confirmed. The earlier RKE2 ZIP has not been refreshed and contains no PKI assets.

Local issuance itself installed no trust or Secrets. The later approved OS trust
installation is recorded below; no API authentication or application was activated. Rancher source selects privateCA:true and
additionalTrustedCAs:true; required public CA Secrets are documented but absent.
Headlamp/API trust and OpenBao internal/localhost TLS remain separate delivery and
validation steps. Public CA OS trust has since been installed as recorded below;
leaf/key Secret delivery still requires its own concrete approval. CA issuance approval
does not authorize further security changes. Source and repeat procedures are retained in the repository.

Approved public CA trust installation completed on the workstation and all three
nodes. The recorded issuance fingerprint matched every installed anchor; all four
service certificates verified through each default OS trust store (16 checks).
The first node run stopped on missing OpenSSL CLI after copying worker-1's public
anchor; the corrected resume installed verification tooling, required its matching
fingerprint and completed all three nodes without failures. Protected inputs/logs
and verification are in .rke2-state/lab-ca-trust-buz_1qnr/.

Firefox ESR has a public-certificate Install policy at
/etc/firefox/policies/policies.json; the user reopened Firefox and confirmed the
Certificates Install entry under active policies. Live browser HTTPS is not yet verified. All three nodes remain
Ready. No signing/service private key was distributed, no cluster Secret or API
OIDC change was made, and no RKE2/browser restart was performed. OS trust does not
populate application/container CA stores. Next is reviewed leaf/key Secret and
application CA delivery, preserving paused bootstrap. Independent CA backup and
passphrase custody remain unconfirmed. Source and repeat procedures are retained in the repository.

TLS resource delivery is prepared, not applied, in
big-bang-bootstrap/configuration/ansible/platform-tls.yaml. Explicit independent
flags gate namespace-only preparation and credential delivery, with the normal
published-release/clean-checkout/exact-cluster guards. Supported delivery is three
TLS Secrets (Headlamp/Keycloak/Rancher), Headlamp identity-ca ConfigMap and Rancher
tls-ca/tls-ca-additional public CA Secrets. No application namespace currently exists;
Rancher's Namespace manifest was split from installer RBAC so TLS preparation grants
no installer authority. OpenBao is excluded pending listener/internal TLS review.
All selected certificates/keys are validated before writes; existing objects are
refused and runtime payloads are redacted/in-memory. Synthetic delivery, key mismatch
and overwrite-refusal tests passed. No namespace, Secret, ConfigMap, route, storage
or bootstrap change occurred. Next prerequisites are committing/reviewing/publishing
compatible release inputs, then explicit namespace/TLS delivery approval. Do not
bypass the release guards with dirty source or older incompatible context metadata.

Tenant enrollment is now explicitly excluded from the local cluster root until
core platform readiness. The retained enrollment source/reconciler stay suspended;
its prerequisite playbook refuses an unselected root before release/API access.
No tenant bootstrap source, reconciler or root authority is in the rendered local
root. Tests retain explicit optional-chain fixtures without enabling operator
selection. Re-enable only after core services and identity acceptance with reviewed
compatible downstream context/pins and separate activation approval. No live
resource was changed by this source containment adjustment.
