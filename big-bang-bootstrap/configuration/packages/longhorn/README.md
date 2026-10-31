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
