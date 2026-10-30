# Physical infrastructure Ansible

PXE/Kickstart installs RHEL. Infrastructure Ansible owns OS prerequisites, RKE2 and Rancher cluster management. Big Bang bootstrap Ansible installs pinned Flux prerequisites and seeds Git configuration; Flux then reconciles Big Bang packages.

| Entrypoint | Purpose | Default |
|---|---|---|
| `playbooks/configure-hosts.yml` | physical OS preparation starter | still scaffolding |
| `playbooks/install-rke2.yml` | recovered single-server RKE2 installation/join/readiness | no connections |
| `playbooks/install-rancher.yml` | pinned management server installation | no cluster access |
| `playbooks/configure-rancher-oidc.yml` | explicit platform-group login and global-role bindings | no credential reads or cluster access |

See [RKE2 inputs and safety](RKE2.md) and [Rancher management](rancher/README.md). The committed inventory is deliberately generic; concrete addresses and SSH identity belong in an ignored private inventory. No username, key or password is guessed.

All apply flags default false; check mode never contacts nodes/clusters. Source restoration is not physical-readiness or live-execution approval. RHEL, repositories, SSH/become, network/CNI/firewall, storage, TLS and capacity must be reviewed first. No VM or AWS provisioning workflow is reintroduced.
