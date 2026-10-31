# Optional Longhorn storage package

Prepared, not selected or installed. clusters/local still omits this directory;
the outer Big Bang release/seed and this package's Flux HelmRelease stay paused.
Big Bang 3.35.1 generates the single child release/source from the official charts
Git tag longhorn-1.13.0 (charts/longhorn). The checksummed official chart artifact
is a test fixture, never vendored deployment source. Git sourcing avoids the shared
helmRepositories list replacement problem when other custom packages are selected.

The authored V1 configuration has two replicas with hard node/disk anti-affinity,
Retain, expansion and WaitForFirstConsumer; it does not make Longhorn the default
StorageClass. V2 is off (no raw disk/hugepage changes). Components select only nodes
labeled storage.perkforge.io/worker=true. Only the two reviewed workers may get that
label and node.longhorn.io/create-default-disk=true; leave control-1 unlabeled and
without a Longhorn data disk. Host prerequisites and label changes require separate
infrastructure approval. No worker labels or directories have been created here.

The data path /var/lib/longhorn initially shares each worker's OS filesystem.
Reserve 30% for the default disk, keep 25% minimum available, and use 100% scheduling
without overprovisioning. These scheduling settings are not filesystem quotas.
Budget 80–100Gi total logical claims initially, measured against actual photo import;
replicas, snapshots and rebuilds consume additional space. Keep bounded snapshots,
Harbor image retention and independent application backups. A worker outage leaves
one surviving copy until the second worker returns/rebuilds. The control plane is
still single-server. Add dedicated worker SSDs as actual growth requires.

## Before later activation

1. Run a read-only RHEL/Longhorn preflight: pinned RKE2/Longhorn compatibility,
   SELinux policy, iSCSI package/version/module/service, mount propagation, free
   disk/RAM, networking and worker selection. Existing nodes currently lack iSCSI
   and NFS client packages. Do not install open-iscsi 2.1.12; check upstream guidance.
2. Separately approve host prerequisites and directory/label preparation. Longhorn
   needs privileged root/host access; prerequisites/ contains a privileged namespace,
   installer RBAC and named bind/escalate permissions derived from the pinned chart.
   Kubernetes create permissions cannot be resource-name scoped. Review actual
   rendered upstream runtime RBAC as well as the installer before granting it.
3. Select ../../configuration/packages/longhorn in the authoritative local root,
   review source/version/values and prerequisites, and explicitly clear the child
   suspend flag only as part of the later reviewed activation. No standalone Helm
   install, Rancher Marketplace or competing Longhorn release is permitted.
4. Separately approved longhorn-prerequisites.yaml applies common Big Bang then
   this package's namespace/RBAC from a clean published release, with expected
   kubeconfig/context/UID. It never unpauses bootstrap or installs Longhorn itself.
5. Once bootstrapped, readiness.yaml phase storage observes the release, manager
   and CSI DaemonSets. Then test a small PVC: write/checksum data, recreate its pod,
   reattach on the other worker and verify persistence plus two healthy replicas.
   Failover/rebuild, backup/restore and real data import remain separate tests.
6. Keycloak's package dependency waits for Longhorn. Its default prerequisite
   backend is now longhorn; the alternate keycloak/prerequisites-longhorn overlay
   removes the static PV/class and replaces the claim's class without prebinding.
   The old base is not a migration mechanism. Never patch a bound PVC to switch
   backends; existing data would need a separately approved backup/migration.

A replica is not a backup. Personal Nextcloud data must have an independent,
protected copy and tested restore before becoming its only home.

Sources: https://longhorn.io/docs/1.13.0/deploy/install/ and
https://longhorn.io/docs/1.13.0/best-practices/.

## Repeat the read-only host audit

From the repository root, using the private inventory and protected output directory:

```sh
ansible-playbook -i infrastructure/ansible/inventory/.topology.yml \
  infrastructure/ansible/tests/longhorn-preflight.yml \
  -e longhorn_preflight_verify=true \
  -e longhorn_preflight_output_parent=/ABSOLUTE/PATH/TO/inventory/.rke2-state
```

The output parent must already be operator-owned, mode0700 and not a symlink.
Default/check mode contacts no hosts. Explicit verification reads worker state over
SSH without sudo and writes a fresh local mode0600 summary; it never prepares hosts.
Missing probes are recorded rather than treated as installation readiness.

The current audit found matching worker hostnames, XFS/shared mount propagation,
six CPUs, about 15GiB RAM and 227GiB free per worker. Both lack iSCSI tools/service;
iscsi_tcp exists on disk but is not loaded. The data directory and storage labels
remain deliberately absent. NFS tools are needed for RWX/NFS backup and cryptsetup
for encrypted volumes. Enforcing SELinux has RKE2/container policies, but active
policy permissions and later runtime behavior remain unverified. No installation
is ready merely because the audit completed. Chart network policies explicitly
select the RKE2 distribution; this authored correction has not been applied.

When reviewing cluster metadata, compare node names, hostname labels and RKE2
hostname annotations with the inventory. Investigate unexpected test values;
controller-owned annotations require understanding before removal. Keep full
metadata and physical identifiers out of tracked evidence.
