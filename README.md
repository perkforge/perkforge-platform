# PerkForge Platform

Big Bang supplies the curated platform packages; Flux owns GitOps reconciliation.
Platform-owned tenant enrollment is kept in the separate
[enrollment repository](https://github.com/perkforge/perkforge-platform-tenants);
application repositories own application configuration.

- [Platform maintenance](docs/platform/README.md): add/configure apps, targets/environments and impact profiles.
- [Big Bang bootstrap](big-bang-bootstrap/README.md): cluster/environment/impact-profile selection, Flux bootstrap, platform application configuration and staged operations.
- [Infrastructure](infrastructure/README.md): physical-host inventory and RHEL/RKE2 provisioning.
- [Interactive provisioning architecture](docs/architecture/README.md): context-to-detail LikeC4 views, local network topology and the operator procedure.
- [Current handoff](HANDOFF.md): operational boundaries and known trial limits.
- [Releases](RELEASING.md): reviewed release PRs and verified tag references.

Rancher is reserved for platform-admin cluster lifecycle management. It does not
own application reconciliation. No Fleet application deployment path is supported.

These are reference-platform capabilities and evidence, not a claim of DoD impact-level authorization or inherited compliance. Protected credentials, raw operational logs and VM disks remain outside tracked configuration. No restructuring command changes the running cluster.
