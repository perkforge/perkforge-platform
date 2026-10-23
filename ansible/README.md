# Ansible environments

The root-level inventory and playbooks in this directory are reserved for the
future physical homelab cluster. They are separate from both the disposable
libvirt VMs in [`../local-lab/`](../local-lab/README.md) and the temporary EC2
environment in [`aws-lab/`](aws-lab/README.md).

Do not put VM or AWS inventories, their addresses, or environment settings in
the physical-host inventory. Add physical machines only after their
switch/VLAN, addressing, RHEL release, and roles have been decided.

The physical-host starter inventory has no hosts, and its playbooks are empty.
It is not currently runnable. Keep private keys, passwords, join tokens, and
kubeconfigs out of version control.
