# Physical infrastructure Ansible

The operator uses PXE and interactive Anaconda to install RHEL. Infrastructure Ansible owns OS prerequisites and RKE2; platform Ansible owns gated Rancher API configuration. Big Bang/Flux owns optional Rancher and Longhorn Helm deployment. Big Bang bootstrap Ansible installs pinned Flux prerequisites and seeds Git configuration; Flux then reconciles Big Bang packages.

| Entrypoint | Purpose | Default |
|---|---|---|
| `playbooks/label-longhorn-workers.yml` | separately approved worker-only storage labels | no cluster access |
| `playbooks/prepare-longhorn-hosts.yml` | separately approved worker-only V1 storage prerequisites | no connections |
| `tests/longhorn-preflight.yml` | read-only worker storage prerequisite audit | no connections |
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
