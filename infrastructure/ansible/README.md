# Physical infrastructure Ansible

The operator uses PXE and interactive Anaconda to install RHEL. Infrastructure Ansible owns OS prerequisites and RKE2; platform Ansible owns gated Rancher API configuration. Big Bang/Flux owns optional Rancher and Longhorn Helm deployment. Big Bang bootstrap Ansible installs pinned Flux prerequisites and seeds Git configuration; Flux then reconciles Big Bang packages.

| Entrypoint | Purpose | Default |
|---|---|---|
| `playbooks/label-longhorn-workers.yml` | separately approved worker-only storage labels | no cluster access |
| `playbooks/prepare-longhorn-hosts.yml` | separately approved worker-only V1 storage prerequisites | no connections |
| `playbooks/mount-longhorn-disks.yml` | reviewed existing XFS disks, UUID mounts and root-directory guard | no connections |
| `tests/longhorn-preflight.yml` | read-only worker storage prerequisite audit | no connections |
| `tests/longhorn-unused-ssd.yml` | reviewed unused-SSD unmount, guard proof and remount | no connections |
| `playbooks/configure-workstation-dns.yml` | approved first-time workstation split DNS using its existing resolver | no changes |
| `playbooks/configure-node-dns.yml` | reviewed worker-first node resolver migration with rollback | no connections |
| `tests/coredns-resolution.yml` | read-only lab/internal/public DNS queries through CoreDNS from control-1 | no cluster access |
| `playbooks/refresh-coredns.yml` | separately approved CoreDNS rolling resolver refresh | no cluster access |
| `playbooks/configure-lab-dns.yml` | separately approved DNS-only first installation on control-1 | no connections |
| `playbooks/install-lab-ca-trust.yml` | approved public CA installation on workstation/nodes and Firefox certificate policy | no connections/changes |
| `playbooks/create-lab-pki.yml` | approved local encrypted CA and four hostname certificate bundles | no prompts or key creation |
| `playbooks/configure-hosts.yml` | reviewed RHEL/Canal prerequisites | no connections |
| `playbooks/install-rke2.yml` | pinned single-server RKE2 installation/join/readiness | no connections |
| `tests/reboot-verification.yml` | bootstrap-only worker-first reboots and persistence/Ready checks | no connections |
| `tests/etcd-backup.yml` | named snapshot, protected off-node token/datastore copy and integrity checks | no connections |
| `tests/workload-smoke.yml` | disposable two-worker DNS/pod/ClusterIP verification and cleanup | no cluster access |
| `playbooks/export-rke2-tokens.yml` | protected, nonoverwriting server/agent token export | no connections |

See [RKE2 inputs and safety](RKE2.md) and [platform Rancher management](../../big-bang-bootstrap/configuration/packages/rancher/README.md). The public hosts.yml is an empty skeleton. The ignored .topology.yml beside it contains the physical IP/MAC map and SSH identity references; use it explicitly with -i for approved local operations. Its ignored known_hosts.local file retains existing verified host trust. A fresh checkout must establish trust physically before connecting.

All apply flags default false; check mode never contacts nodes/clusters. Source restoration is not physical-readiness or live-execution approval. RHEL, repositories, SSH/become, network/CNI/firewall, storage, TLS and capacity must be reviewed first. No VM or AWS provisioning workflow is reintroduced.

See [physical home-lab backup and recovery](BACKUP-RECOVERY.md) for the separate backup target and activation hold.

## Dedicated Longhorn filesystem mounts

This separate host step mounts already-prepared XFS partitions on reviewed RHEL
10.2 x86_64 workers with enforcing SELinux. It does not partition, format, register
Longhorn disks, change replica policy, move replicas or restart RKE2. Keep physical
filesystem UUIDs, USB descriptor serials, labels and raw byte sizes in ignored
`inventory/.longhorn-mounts.yml`, mode 0600, using
`longhorn-mounts.example.yml`. Keep network/SSH inventory in `.topology.yml`.
USB descriptor serials are used because some SCSI bridges display reversed serials.

Before apply, review the exact identities, mount path and all changes, and confirm
that preserved data copies remain available. An unexpected mount, nonempty mount
directory, symlink, identity mismatch or conflicting fstab entry stops the run.
Required host tools are Python 3, util-linux and e2fsprogs (`chattr`/`lsattr`);
the playbook installs no packages. Apply requires sudo on the selected workers.
The current root must be an XFS block filesystem with a readable filesystem UUID;
the UUID is probed from the mounted root device rather than supplied by the operator.

From the repository root, offline checks are:

```bash
python3 -m unittest discover -s infrastructure/ansible/tests -p test_longhorn_mounts.py -v
ansible-playbook -i infrastructure/ansible/inventory/hosts.yml infrastructure/ansible/playbooks/mount-longhorn-disks.yml --syntax-check
ansible-playbook -i infrastructure/ansible/inventory/hosts.yml infrastructure/ansible/playbooks/mount-longhorn-disks.yml --check
```

After review and explicit deployment authorization, use the private inventory and
disk plan. Enter the sudo password only at the local Ansible prompt:

```bash
ansible-playbook -i infrastructure/ansible/inventory/.topology.yml \
  infrastructure/ansible/playbooks/mount-longhorn-disks.yml \
  -e @infrastructure/ansible/inventory/.longhorn-mounts.yml \
  -e longhorn_mount_apply=true -e longhorn_mount_reviewed=true \
  -e longhorn_mount_guard_reviewed=true --ask-become-pass
```

The plan selects workers and applies serially, stopping on failure. Do not use
`--limit` to select a worker: it can exclude the localhost validation play. For
different sudo passwords, use a separately reviewed one-worker plan per invocation.
Default mode and check mode perform no worker connections; they are not host
readiness checks or a simulation of successful deployment.

The guard makes the **empty underlying root-filesystem directory** immutable and
proves that a root file creation fails with EPERM before writing fstab or mounting.
It records the underlying inode and root filesystem UUID in a protected root-owned marker under
`/etc/perkforge/longhorn-mounts/`. It never sets immutable on a mounted SSD. A rerun
on an already-mounted SSD verifies its identity and trusts the prior marker; the
hidden underlying inode cannot be rechecked without unmounting. Do not manually
replace mount directories or remove markers/immutable flags. This is an accidental
root-fallback write guard, not isolation against an administrator who clears it.
Device numbers are checked only within the current run; they are never persisted
as identity because device-mapper numbering can change across boots. A root
filesystem replacement, changed guard inode or unsupported marker version stops
the run for review. No version-1 markers have been deployed by this work; automatic
marker migration is deliberately absent.

The mount stage does not relabel files or change SELinux policy. A newly formatted
XFS root can show `unlabeled_t`; that label alone does not establish an access
failure. Check `ls -Zd`, `matchpathcon` and the no-change `restorecon -nv` preview,
the actual Longhorn process domains (`ps -eZ`), applicable `sesearch` rules and AVCs.
Privileged Longhorn components should run as `spc_t`, while nonprivileged components
use `container_t`, as described by
[Longhorn's SELinux guidance](https://longhorn.io/kb/selinux-and-longhorn/).
Policy queries and an absence of visible kernel AVCs do not prove runtime I/O
access or replace an owner-authorized audit-log check. Any relabel or policy change
needs its own reviewed scope; do not infer a need for a new type or permissive mode.

Immediately after apply, read-only checks on each worker are:

```bash
findmnt --mountpoint /mnt/longhorn-t7 --output TARGET,SOURCE,UUID,FSTYPE,OPTIONS,PROPAGATION
df -B1 --output=source,size,used,avail,target /mnt/longhorn-t7
```

For a different reviewed plan, substitute its exact path. Require the planned UUID,
XFS, `rw,noatime,nosuid,nodev` and shared propagation. The apply stage verifies the
mounted identity again; these commands make current capacity and mount state easy
to inspect without another privileged operation.

Mounts use UUIDs, `rw,noatime,nosuid,nodev,nofail`, a 15-second systemd device timeout
and `x-systemd.device-bound`. An absent drive does not block boot; after unmount,
the protected empty directory refuses fallback writes. A disconnected but still
mounted device can instead produce I/O errors. The playbook does not restart
workloads to recover a disconnected disk. Systemd device binding is documented in
[systemd.mount](https://www.freedesktop.org/software/systemd/man/latest/systemd.mount.html);
immutable behavior is documented in [chattr](https://www.man7.org/linux/man-pages/man1/chattr.1.html).

Before **any Longhorn registration**, separately approve and perform a controlled
missing-drive acceptance check on each unused SSD: confirm the expected mounted
UUID/XFS and reported formatted capacity; unmount that exact unused path; confirm
the underlying inode matches its marker, immutable remains set, and a root write
is refused; then remount the exact path and reverify. Boot-with-drive-absent behavior
also needs a separately approved maintenance check. These physical checks have not
been performed by the offline tests. Never unmount an active Longhorn disk for this
check. Calculate Longhorn reserves from the measured formatted capacity afterward.

On partial failure, inspect first and rerun only after resolving the reported
cause; the guarded directory and marker may already exist. Do not clear immutable,
delete the marker or run `mount -a` as a shortcut. Removal/rollback after Longhorn
registration requires a separate replica evacuation plan and approval.

### Unused-SSD acceptance before Longhorn registration

Freshly confirm that neither proposed path is registered in `nodes.longhorn.io`;
keep other storage changes paused. The two acceptance stages require their own
explicit approval. They operate only on empty, unregistered filesystems.

`files/verify-longhorn-runtime-io.py` runs from stdin inside the existing privileged
`longhorn-manager` container, using its actual `spc_t` domain. It checks the UUID,
label, XFS type and host-path device number against the block device. It refuses
the host root filesystem or any nonempty target. Default mode only inspects;
`--apply --reviewed` creates a fresh private directory with one 16 MiB random file,
fsyncs it, reopens and verifies its checksum, then removes only its owned entries.
Directory descriptors keep all writes/cleanup anchored to the verified filesystem.
It does not install scripts, relabel, change policies or write Longhorn metadata.
Do not replace the host procfs-root path with a userspace-resolved symlink.

Find the manager on each planned worker with
`kubectl -n longhorn-system get pods -l app=longhorn-manager -o wide`. Set
`SSD_MANAGER_POD`, `SSD_FILESYSTEM_UUID` and `SSD_FILESYSTEM_LABEL` from the reviewed
pod placement and private disk plan, then run the initial read-only inspection:

```bash
kubectl -n longhorn-system exec -i "$SSD_MANAGER_POD" -c longhorn-manager -- \
  python3 - --path /mnt/longhorn-t7 --uuid "$SSD_FILESYSTEM_UUID" \
  --label "$SSD_FILESYSTEM_LABEL" \
  < infrastructure/ansible/files/verify-longhorn-runtime-io.py
```

After explicit approval, repeat with `--apply --reviewed` before the input
redirection, one worker at a time. The image must provide Python 3.6+ and `blkid`;
the helper uses the standard library and supports the older interpreter observed
in the tested manager image. It reads `/proc/self/attr/current` directly because
`id -Z` can report SELinux unavailable inside that image despite its actual `spc_t`
domain. No local sudo is needed for this stage, but Kubernetes
exec authorization and explicit approval for the disposable writes are required.

Then the owner runs the guard/remount stage from the repository root:

```bash
ansible-playbook -i /ABSOLUTE/PRIVATE/INVENTORY/.topology.yml \
  infrastructure/ansible/tests/longhorn-unused-ssd.yml \
  -e @infrastructure/ansible/inventory/.longhorn-mounts.yml \
  -e ssd_acceptance_apply=true -e ssd_acceptance_reviewed=true \
  -e ssd_acceptance_unregistered=true --ask-become-pass
```

It works serially, verifies hostname and mounted identity, refuses occupied disks,
uses normal `umount` without force/lazy flags, proves the exposed recorded guard,
remounts the exact fstab entry and reports capacity. A failure stops before the
next worker and can leave the current unused SSD unmounted; inspect before any
recovery action. It changes no fstab entries or immutable flags. Do not use this
test after Longhorn registration. Retain localhost in ordinary mount playbook runs;
this separate acceptance playbook directly selects inventory `rke2_agents`.

The owner should inspect `sudo ausearch -m AVC,USER_AVC -ts recent -i` locally on
each worker for the test window; report relevant denials without posting raw audit
logs or credentials. Recheck mounts, node/PVC health and absence of new kernel I/O
errors afterward. This is a permission/basic-I/O and guard lifecycle test, not a
performance, cold-read, power-loss, reboot or unplug qualification. No reboot or
service restart is part of these stages.

Observed 2026-11-05 before registration: the helper passed on both SSDs from the
existing manager containers, each verifying 16,777,216 bytes and successful cleanup.
Independent read-only inspections then confirmed both filesystem roots were empty.
The owner guard/remount run completed on both workers with ok=11, changed=2,
unreachable=0 and failed=0. Both SSDs were subsequently registered scheduling-disabled;
these unused-disk tests must not be rerun against them now. Post-registration volume
acceptance belongs to the dedicated StorageClass/PVC workflow, not this helper.
The observed tests do not constitute exhaustive SELinux audit-log review or
application-data backup/restore acceptance.
