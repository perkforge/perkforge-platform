# Infrastructure

The physical RHEL10.2 pilot completed interactive installation and operator-verified
key-only SSH/sudo access. Operator reports workstation PXE shutdown successful; read the
[current handoff](../pxe/pilot/HANDOFF.md). Workers and host/RKE2/platform preparation
remain separate approved stages. Before workers, review the [redesign proposal](PROVISIONING-REDESIGN.md)
and [retrospective](PROVISIONING-RETRO-2026-10-31.md), then [tomorrow readiness](TOMORROW-READINESS.md). Ansible owns physical OS preparation,
RKE2/Rancher and Flux/Big Bang bootstrap configuration.

RKE2 installation/join/readiness is recovered from the proven primitives, with physical inputs and default-off gates. Rancher installation and platform-only OIDC configuration are active infrastructure Ansible. OS preparation remains an explicit starter; RHEL installation and all live actions require approval. See [Ansible entrypoints](ansible/README.md).

Local means an engineer-owned physical cluster. The committed inventory is a template, private inventories stay ignored, and laptop VM/AWS harnesses remain removed. No restructuring operation contacts or powers on physical nodes.

Start with the [offline preparation and staged handoff](PREPARATION.md),
[PXE prerequisites](../pxe/README.md), and [credential lifecycle proposal](CREDENTIALS.md).

Record approved steps and manually sanitized output in the
[physical-cluster execution journal](EXECUTION-JOURNAL.md).
