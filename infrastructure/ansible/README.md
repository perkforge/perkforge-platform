# Physical infrastructure Ansible

The operator uses PXE and interactive Anaconda to install RHEL. Infrastructure Ansible owns OS prerequisites, RKE2 and Rancher cluster management. Big Bang bootstrap Ansible installs pinned Flux prerequisites and seeds Git configuration; Flux then reconciles Big Bang packages.

| Entrypoint | Purpose | Default |
|---|---|---|
| `playbooks/configure-hosts.yml` | reviewed RHEL/Canal prerequisites | no connections |
| `playbooks/install-rke2.yml` | pinned single-server RKE2 installation/join/readiness | no connections |
| `tests/reboot-verification.yml` | bootstrap-only worker-first reboots and persistence/Ready checks | no connections |
| `tests/etcd-backup.yml` | named snapshot, protected off-node token/datastore copy and integrity checks | no connections |
| `tests/workload-smoke.yml` | disposable two-worker DNS/pod/ClusterIP verification and cleanup | no cluster access |
| `playbooks/export-rke2-tokens.yml` | protected, nonoverwriting server/agent token export | no connections |
| `playbooks/install-rancher.yml` | pinned management server installation | no cluster access |
| `playbooks/configure-rancher-oidc.yml` | explicit platform-group login and global-role bindings | no credential reads or cluster access |

See [RKE2 inputs and safety](RKE2.md) and [Rancher management](rancher/README.md). The public hosts.yml is an empty skeleton. The ignored .topology.yml beside it contains the physical IP/MAC map and SSH identity references; use it explicitly with -i for approved local operations. Its ignored known_hosts.local file retains existing verified host trust. A fresh checkout must establish trust physically before connecting.

All apply flags default false; check mode never contacts nodes/clusters. Source restoration is not physical-readiness or live-execution approval. RHEL, repositories, SSH/become, network/CNI/firewall, storage, TLS and capacity must be reviewed first. No VM or AWS provisioning workflow is reintroduced.
