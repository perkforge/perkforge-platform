# Physical infrastructure

Use the [human-operated RHEL procedure](../pxe/README.md) for installation and SSH.
[Current state](../HANDOFF.md) records readiness; the [C4 views](../docs/architecture/README.md)
show architecture, the local topology and operating boundaries.

[Ansible entrypoints](ansible/README.md) own explicit host/RKE2 operations; optional Rancher/Longhorn Helm deployment belongs to Big Bang/Flux.
The [public inventory skeleton](ansible/inventory/hosts.yml) contains no physical identifiers.
The ignored `ansible/inventory/.topology.yml` holds the actual IP/MAC map and SSH references. Private key bytes/passwords are not in the repository.
The ignored `ansible/inventory/known_hosts.local` retains current verified host trust;
re-establish it through a physical fingerprint check on a new workstation.

Before installing RKE2, review repositories/entitlement, SELinux, NetworkManager/CNI,
firewall/forwarding, time, swap, storage/capacity and [credential custody](CREDENTIALS.md).
Working SSH alone is insufficient. Host and cluster changes require a concrete,
reviewed action and separate operator authorization.

Rancher is platform-admin cluster lifecycle management. Flux owns GitOps; Big Bang
supplies curated platform packages. No repository maintenance command changes nodes,
workstation services or a running cluster.

[RKE2 operator procedure](ansible/RKE2.md) covers reviewed host preparation, pinned
installation, token export and private local custody. Before platform activation, verify
workload networking, off-node recovery material, reboot behavior and a persistent-
storage decision; see the current handoff for completed checks and remaining scope.

## Home-lab storage design

Growth targets are Harbor with scanned-image retention, a small portal PostgreSQL
DB, Nextcloud personal photos/files and OpenBao secrets. Selected design is
Longhorn with two replicas on different workers, no application-data replicas on
control-1, using existing filesystems initially. Keep the single control plane and
etcd capacity independent; replicated storage does not make this cluster HA.
Start with an approximate 80–100GiB total logical-volume budget, not a claimed quota
or guaranteed usable capacity; replicas double data footprint before snapshots and
other overhead. Size actual claims after measuring the existing photo/file import.
Avoid overprovisioning, retain at least 25% root-disk free space, and review capacity
around 30% free rather than waiting for disk pressure. Add larger dedicated worker
SSDs when measured growth requires them; no immediate NAS/network upgrade is chosen.
Use bounded image/snapshot retention and an independent protected backup destination
for personal files, databases and secret-service recovery, with restore checks.

Pinned Big Bang 3.35.1 has no built-in Longhorn package. Its custom-package mechanism
can declare an upstream pinned Longhorn chart, reconciled by Flux, ordered before
stateful applications. Infrastructure Ansible owns host prerequisites. Optional Longhorn 1.13.0 and Rancher 2.15.2 inputs and prerequisites are prepared
under big-bang-bootstrap/configuration/packages; both remain unselected/suspended.
Host compatibility, actual scheduling/labels and backup details still need review
before any installation. The existing static Keycloak PV remains an unconfigured
specimen until deliberately replaced; no storage implementation has been applied.
See [Big Bang storage guidance](https://docs-bigbang.dso.mil/latest/docs/community/development/bigbang-storage-options/),
[custom packages](https://docs-bigbang.dso.mil/latest/docs/installation/environments/extra-package-deployment/)
and [Longhorn recommendations](https://longhorn.io/docs/1.13.0/best-practices/).
