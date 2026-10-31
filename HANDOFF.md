# Current operator handoff

Live cluster work is paused at the operator's request. Use this existing feature
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
  root on LVM. Worker-1's Primary and Automatic boot sequences were corrected;
  connected boot succeeded. Do not assume all other firmware paths were retested.
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
ZIP is not an etcd backup. No off-node snapshot backup or restore test has been
performed. Keep local credentials until independent custody is confirmed.

## Repeat and resume

Use [PXE/RHEL procedure](pxe/README.md), [RKE2 procedure](infrastructure/ansible/RKE2.md)
and [C4 views](docs/architecture/README.md). Configuration belongs in Ansible/YAML;
private inputs and credentials remain ignored. Host preparation refuses an
existing RKE2 installation; do not rerun it on the installed cluster. Token export
refuses to overwrite existing exports.

Before platform activation, separately approve disposable cross-node/DNS/service
validation, off-node snapshot/token custody, sequential reboot verification and a
persistent-storage choice. These checks remain outstanding; no new live action
is authorized by this handoff. Keep architecture and human repeat instructions,
not session journals, planning archives or duplicate procedure documents.
