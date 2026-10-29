# Physical infrastructure Ansible

This inventory and the starter host/RKE2 playbooks are reserved for physical clusters. Inventory hosts and site-specific variables must be supplied by the operator. There are no personal addresses, VM inventories or AWS lab resources.

The inventory is empty and playbooks are scaffolding, not a complete runnable installer. Keep private keys, passwords, join tokens and kubeconfigs outside version control. Platform bootstrap and application API configuration live in `big-bang-bootstrap/ansible`, separate from infrastructure.
