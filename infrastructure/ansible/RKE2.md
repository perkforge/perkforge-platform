# Physical RKE2 installation

The reusable RPM install/configuration/join/readiness primitives come from v0.7.0's former local-lab Ansible. This port removes DVD/libvirt/address assumptions and retains a single server with one or more serially joined agents. It rejects multiple server hosts rather than pretending to implement HA.

## Operator inputs

- An ignored inventory with `rke2_servers` and `rke2_agents`, explicit `ansible_host` and SSH user/authentication. No private addresses or credentials belong in the committed template.
- Installed RHEL with Python/SSH/become, working OS repositories, enforcing SELinux and reviewed physical firewall/CNI/NetworkManager prerequisites. PXE/OS setup is separate; these playbooks do not wake or scan nodes.
- A unique `rke2_cluster_id`, protected `rke2_private_output_dir`, reviewed pod/service CIDRs and optional API TLS SANs. RKE2 is pinned to v1.36.5+rke2r1; the release-tagged installer is SHA256-checked. A version change needs compatibility review.
- Deliberate `physical_operator_inputs_complete`, `rke2_network_prerequisites_reviewed` and `rke2_install_apply` gates, supplied only after action-specific approval.

Syntax/default checks use no nodes:

```sh
ansible-playbook -i infrastructure/ansible/inventory/hosts.yml infrastructure/ansible/playbooks/install-rke2.yml --syntax-check
ansible-playbook -i infrastructure/ansible/inventory/hosts.yml infrastructure/ansible/playbooks/install-rke2.yml --check
```

## Existing state and recovery

Controller preflight runs before dynamic approved groups are formed; defaults/check mode gather no remote facts. The remote installer refuses unowned existing RKE2 state, a mismatched installation marker or version, and managed config drift. It never wipes data, silently adopts a cluster, upgrades an existing release or restarts it to apply changes. Interrupted unmarked installations require a separate recovery review.

Server readiness precedes token transfer and agent joining. Join tokens remain only in no_log runtime variables and root-only agent config; no fact cache is enabled by this code. Kubeconfig and bundled kubectl go only to protected operator-selected state, never `~/.kube/config`. Existing output requires matching ownership; output directory/file modes are 0700/0600. Shared/private credential parent paths must also be protected.

The approved install would create credentials and start RKE2 services, then wait for the exact selected nodes Ready. None of that has been executed by this correction. Synthetic/default-gate tests and template checks do not establish physical OS/package/network compatibility, startup, HA or backup/recovery readiness.
