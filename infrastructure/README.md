# Infrastructure

PXE boots the RHEL installer/Kickstart. `ansible/` owns physical OS preparation and RKE2/Rancher management. `big-bang-bootstrap/configuration/ansible/` handles Flux/Big Bang bootstrap and platform application configuration, followed by Flux reconciliation.

RKE2 installation/join/readiness is recovered from the proven primitives, with physical inputs and default-off gates. Rancher installation and platform-only OIDC configuration are active infrastructure Ansible. OS preparation remains an explicit starter; RHEL installation and all live actions require approval. See [Ansible entrypoints](ansible/README.md).

Local means an engineer-owned physical cluster. The committed inventory is a template, private inventories stay ignored, and laptop VM/AWS harnesses remain removed. No restructuring operation contacts or powers on physical nodes.
