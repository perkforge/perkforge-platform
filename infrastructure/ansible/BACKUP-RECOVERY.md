# Physical home-lab backup and recovery

This is the home-lab procedure, not the recovery architecture required of platform adopters.

## Current state and hold

The dedicated Toshiba disk is formatted ext4 (`PF-BACKUP`) and attached to `worker-2`.
The inspected state has no mount or active NFS export. Backup-target configuration,
schedules and restore acceptance are **not complete**. Keep all backup execution on
hold until the native Nextcloud sync finishes; its workstation source copies remain intact.

## Prepare, then activate

1. Keep disk UUID and exact client addresses in private operator inventory. Mount
   the reviewed UUID at `/srv/perkforge-backup`; never select a disk by `/dev/sdX`.
   This is a backup destination, not a Longhorn replica disk.
2. After explicit host/network approval, configure host-managed NFSv4 independently
   of Kubernetes. Export only `/srv/perkforge-backup/longhorn` to the exact approved
   cluster-node addresses. Review `no_root_squash`: those clients obtain root-level
   write access to that export. Keep other recovery material outside that export.
3. Fail closed if the drive is absent: verify its expected UUID before serving,
   bind the service to the mount/device, and use the NFS `mountpoint=` export guard.
   Never fall back to writing backups into the host root filesystem. Test the
   missing-drive behavior before relying on the destination; do not disturb live
   Longhorn disks or Nextcloud to perform that check.
4. Only after sync completion, approve activation, select this target in reviewed
   Longhorn configuration, and test one disposable volume backup and restore before
   enabling workload schedules. Record successful restore evidence and retention.

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
