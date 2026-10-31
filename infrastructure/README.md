# Physical infrastructure

Use the [human-operated RHEL procedure](../pxe/README.md) for installation and SSH.
[Current state](../HANDOFF.md) records readiness; the [C4 views](../docs/architecture/README.md)
show architecture, the local topology and operating boundaries.

[Ansible entrypoints](ansible/README.md) own explicit host/RKE2/Rancher operations.
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
