# Infrastructure

`ansible/` contains the physical-host inventory and starter RHEL/RKE2 playbooks. Repository `pxe/` contains physical installation templates, not enabled network services. Local means an engineer-owned physical cluster; laptop VM and unused AWS EC2 cluster harnesses are removed.

The starter inventory has no real hosts and the physical playbooks are incomplete. Provide an existing healthy cluster for Big Bang onboarding until physical provisioning is implemented and reviewed. No workload, Flux or Big Bang installation belongs in infrastructure. Host/network/provisioning changes require action-specific approval.
