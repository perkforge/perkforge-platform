# PerkForge Platform

Big Bang supplies the curated platform packages; Flux owns GitOps reconciliation.
Platform-owned tenant enrollment is kept in the separate
[enrollment repository](https://github.com/perkforge/perkforge-platform-tenants);
application repositories own application configuration.

- [Big Bang bootstrap](big-bang-bootstrap/README.md): cluster/environment/impact-profile selection, Flux bootstrap, platform application configuration and staged operations.
- [Infrastructure](infrastructure/README.md): physical-host inventory and RHEL/RKE2 starter provisioning.
- [Current handoff](HANDOFF.md): operational boundaries and known trial limits.
- [Evidence inventory](docs/RESTRUCTURE-INVENTORY.md): retained verification and historical provenance.
- [Releases](RELEASING.md): reviewed release PRs and verified tag references.

Rancher is reserved for platform-admin cluster lifecycle management. It does not
own application reconciliation. The historical custom PaaS/Fleet effort is
[archived](archive/fleet/README.md), not an alternative active deployment path.

These are reference-platform capabilities and evidence, not a claim of DoD impact-level authorization or inherited compliance. Protected credentials, raw operational logs and VM disks remain outside tracked configuration. No restructuring command changes the running cluster.
