# PerkForge Platform

PerkForge Platform is a functional, secure, multi-tenant Kubernetes PaaS reference implementation. It demonstrates platform engineering, DevSecOps, security architecture, and RMF/GRC through working services, enforced tenant boundaries, repeatable assessment, and documented evidence. The current operator uses synthetic tenants to verify real multi-tenant behavior.

## Goals

- Connect the homelab machines to a small network switch.
- Install Red Hat Enterprise Linux (RHEL) on the machines.
- Use PXE network boot to make operating system installation repeatable.
- Use Ansible to automate host configuration and cluster setup.
- Install RKE2 as the Kubernetes distribution.

## Initial deployment flow

1. Connect the machines and the provisioning host to the switch.
2. Prepare a PXE environment to boot the machines and install RHEL.
3. Use Ansible to configure the installed systems and their prerequisites.
4. Use Ansible to install and configure RKE2 on the selected server and agent nodes.
5. Verify that the nodes join the cluster and report Ready.

PXE boot and Kickstart starting files are in [`pxe/`](pxe/README.md). They are templates for development, not ready-to-enable network services; the DHCP owner, RHEL release, and lab network still need to be chosen.

The immediate development target is the disposable two-node VM lab, followed by the planned three-node ThinkCentre RKE2 cluster. Their configurations remain separate. The local lab rebuild and manual steps are in [`local-lab/README.md`](local-lab/README.md); the current environment state and resume notes are in [`HANDOFF.md`](HANDOFF.md). The root of [`ansible/`](ansible/README.md) is reserved for physical machines. Its separate [`aws-lab/`](ansible/aws-lab/README.md) subproject is a disposable EC2 harness for Ansible and RKE2 testing; it does not replace the physical RHEL/PXE plan. Prefer reproducible, portable deployment patterns and avoid unnecessary hardware-specific assumptions.

The planned source-to-target GitHub move and its no-history-loss safeguards are documented in [`docs/MIGRATION-PLAN.md`](docs/MIGRATION-PLAN.md). The local lab remains the active development harness while the physical hardware is in transit.

The platform's assurance goal is to connect each selected security control to its working implementation, repeatable verification, collected evidence, findings, risk decisions, and remediation. RMF artifacts describe this reference environment and do not claim a formal government authorization.

The current shared-cluster tenant boundary and its known limits are recorded in
[`docs/TENANT-SECURITY-BOUNDARY.md`](docs/TENANT-SECURITY-BOUNDARY.md), with
implementation status and evidence expectations in
[`docs/CONTROL-EVIDENCE-MATRIX.md`](docs/CONTROL-EVIDENCE-MATRIX.md). These
documents distinguish generated configuration from live-verified enforcement.
The local offline findings register imports candidate reports idempotently and
records reviewed transitions; its human review workflow, security limits, and
usage are documented in
[`docs/SECURITY-FINDINGS-WORKFLOW.md`](docs/SECURITY-FINDINGS-WORKFLOW.md),
with a record skeleton at `docs/templates/security-finding.yaml`.
The remaining Phase 6 recommendations and decisions to review are collected in
[`docs/PHASE-6-REVIEW.md`](docs/PHASE-6-REVIEW.md).

PXE requires a boot and installation service on the network. Decide where that service will run and how it will coexist with the existing DHCP service before enabling it; avoid introducing a second, conflicting DHCP server on a shared LAN.

## Early requirements

### Local VM exercise

The first RKE2 learning cluster uses two existing libvirt VMs on the host's default NAT network (`192.168.122.0/24`). It is a single-server cluster for practice, not a highly available design or the final three-node physical homelab.

- `cks-control` — RHEL 10.2, 2 vCPU, 4 GiB RAM, 30 GiB disk, `192.168.122.201`.
- `cks-worker` — RHEL 10.2, 2 vCPU, 4 GiB RAM, 100 GiB disk, `192.168.122.202`.
- Both nodes use RKE2 `v1.36.5+rke2r1`, SELinux enforcing, and the RKE2 SELinux policy.
- Rancher `2.15.2` manages the local RKE2 cluster. Mattermost Team Edition runs as a Fleet-managed workload with CloudNativePG and the local-path provisioner.
- The RHEL DVD ISO is attached to each VM and provides local BaseOS/AppStream package repositories. The installations are not registered to Red Hat, so they do not receive Red Hat CDN updates.
- Firewalld is disabled in this isolated NAT-based exercise because the default Canal network plugin conflicts with firewalld. Revisit firewall rules before moving nodes onto a shared or physical network.
- The lab-only SSH key, VM install answers, kubeconfig, kubectl copy, and other local credentials live under ignored `.secrets/`. The ISO under `images/` is also ignored. Recreate local credentials from the instructions in `local-lab/README.md` after a laptop replacement.

To recreate the entire local stack, run `local-lab/scripts/rebuild-local-lab.sh --confirm-destroy`. It removes both VM disks and all cluster data on them, then provisions RHEL, configures the hosts, installs RKE2 and Rancher, and deploys the configured platform applications through Fleet. It stops on the first failed stage and writes a log under `.secrets/`. The ISO and `.secrets/` are preserved. Use `local-lab/scripts/teardown-vms.sh` to preview removing only the VMs. These local workflows do not change the future physical homelab setup.

The Mattermost application has no preset admin login or password. The first user account created in the application becomes the system administrator. The database credential in `.secrets/mattermost-db-password` is only for PostgreSQL.

Inspect the cluster from this repository with:

```sh
.secrets/kubectl --kubeconfig .secrets/rke2.yaml get nodes -o wide
```

### Hardware and networking

- A small Ethernet switch connects all homelab machines.
- A provisioning host or service must be reachable by the machines during PXE boot.
- The switch uplink, VLAN use, and whether the lab is isolated from the household LAN are not yet specified.
- Reserve stable addresses or DHCP reservations for the hosts and document their names and addresses.

### Operating system provisioning

- RHEL is the host operating system.
- Machines should be installable by PXE so rebuilds do not require individual installation media.
- Select the RHEL release, installation source, boot mode, and provisioning implementation before building the PXE workflow.
- Keep credentials, subscription details, and other secrets out of this repository.

### Host security

- Keep SELinux enabled in enforcing mode on RHEL nodes.
- Ensure the RKE2 SELinux policy is installed and RKE2 runs with SELinux support enabled on both server and agent nodes. The RKE2 RPM installation method handles these automatically; other installation methods require separate setup.
- Do not plan to install AppArmor on the RHEL nodes. RKE2 requires AppArmor tools only when the host kernel supports AppArmor.
- References: [RKE2 SELinux support](https://docs.rke2.io/security/selinux) and [RKE2 installation prerequisites](https://docs.rke2.io/install/quickstart#prerequisites).

### Configuration management

- Ansible is the intended automation tool for repeatable host configuration and RKE2 installation. The local VM setup has a separate playbook set; the physical homelab inventory and playbooks will be developed under `ansible/` when its hardware and network are known.
- Maintain an inventory of host names, addresses, and intended roles.
- Store reusable configuration in playbooks and roles; keep site-specific values in inventory or variables.
- Define how Ansible reaches newly provisioned hosts and where its controller runs.

### Kubernetes

- RKE2 is the Kubernetes distribution for the cluster.
- Decide the number of server and agent nodes, the RKE2 version, and whether the first deployment is single-server or highly available.
- Define the pod and service network ranges and confirm they do not overlap with the home network.
- Document how cluster credentials and join tokens are generated, distributed, and protected.

## Decisions to make

- Number and specifications of machines, including which will be RKE2 server and agent nodes.
- RHEL release and entitlement or subscription approach.
- Whether the homelab uses a dedicated subnet or VLAN, and its address ranges.
- PXE firmware modes (UEFI/BIOS), DHCP responsibilities, and the host or service that provides PXE/TFTP/HTTP.
- Ansible controller location and inventory format.
- RKE2 version, topology, and pod/service CIDRs.
- Storage, ingress, DNS, backups, and external access requirements for workloads.

## Working principles

- Make provisioning and configuration repeatable so a host can be rebuilt from documented inputs.
- Keep secrets out of version control.
- Record chosen versions, network ranges, host roles, and operational steps here as the design is settled.
