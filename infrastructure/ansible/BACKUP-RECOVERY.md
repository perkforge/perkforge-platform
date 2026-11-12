# Physical home-lab backup and recovery

This is the home-lab procedure, not the recovery architecture required of platform adopters.

## Current state

The Toshiba disk (`PF-BACKUP`) is UUID-mounted on `worker-2` at
`/srv/perkforge-backup`. The guarded NFSv4 target and Longhorn's `default` target
are active with the approved backup-host pod-subnet exception; NFS is enabled
at startup. No reboot test has been performed. A disposable volume was backed up and restored into a separate volume;
its 8 MiB random payload passed SHA256 comparison on 2026-11-12. This is storage
round-trip evidence, not application or whole-cluster recovery acceptance.
Workload backups, retention and recovery exercises still need review.

## Prepare, then activate

1. Keep disk UUID and exact client addresses in private operator inventory. Mount
   the reviewed UUID at `/srv/perkforge-backup`; never select a disk by `/dev/sdX`.
   This is a backup destination, not a Longhorn replica disk.
2. After explicit host/network approval, configure host-managed NFSv4 independently
   of Kubernetes. Export only `/srv/perkforge-backup/longhorn` to the exact approved
   cluster-node addresses. Review `no_root_squash`: those clients obtain root-level
   write access to that export. Keep other recovery material outside that export.
   Same-host Longhorn traffic can retain its pod IP rather than the node IP. If
   needed, separately approve only the backup host's pod /24 via private
   `backup_local_pod_cidr` and `backup_local_pod_cidr_reviewed: true`. This grants
   root-capable access to reachable pods in that subnet, not just Longhorn.
   Do not permit the entire cluster CIDR or assume Kubernetes NetworkPolicy
   protects a pod's access to its own host. Target discovery alone is not a test
   of the backup engine's access.
3. Fail closed if the drive is absent: verify its expected UUID before serving,
   bind the service to the mount/device, and use the NFS `mountpoint=` export guard.
   Never fall back to writing backups into the host root filesystem. Test the
   missing-drive behavior before relying on the destination; do not disturb live
   Longhorn disks or Nextcloud to perform that check.
4. Only after sync completion, approve activation, select this target in reviewed
   Longhorn configuration, and test one disposable volume backup and restore before
   enabling workload schedules. Record successful restore evidence and retention.

Staging is captured in `playbooks/prepare-backup-target.yml`: default/check mode
makes no host connection. Initial apply requires reviewed private disk/client
inputs and an explicitly authorized sudo credential supplied only in the process
environment; no password is written to source or a vars file. It refuses an
already-mounted target rather than repeating partial setup blindly. The local
NFS service override removes optional rpcbind/statd startup; review it after
`nfs-utils` upgrades. Loaded mount dependencies and effective protocol/listener restrictions were checked. The live disposable backup/restore passed;
actual reboot/unplug and application recovery tests remain outstanding. Do not
rerun this initial-staging playbook against the active target. Keep activation and
startup enablement separate, explicitly approved operations.

## Recover

Retain the backup disk without formatting it. Restore host access to the same UUID
and export first, then restore cluster identity/control-plane state and GitOps
configuration using their own procedures. Restore Longhorn volumes and verify the
applications against the captured backup point. A volume backup alone does not
capture the RKE2 datastore/token, independent credentials, or application-consistent
database recovery. Keep those protected recovery copies separately recoverable.

Worker-2 and its USB controller are shared with live workloads, so this is a local
recovery copy, not protection from host/site loss. Keep an independent off-host copy.

References: [Longhorn backup targets](https://longhorn.io/docs/1.13.0/snapshots-and-backups/backup-and-restore/set-backup-target/),
[NFS access requirements](https://longhorn.io/kb/troubleshooting-unable-to-mount-an-nfs-backup-target/),
[exports mountpoint guard](https://www.man7.org/linux/man-pages/man5/exports.5.html).
