# Platform handoff

Big Bang/Flux is the chosen platform. Start with [bootstrap tasks](big-bang-bootstrap/README.md). The previous Fleet handoff is [historical only](archive/fleet/HANDOFF.md).

## Existing local trial

Historical running trial, outside the supported source workflows: two RHEL/RKE2 VMs: cks-control (192.168.122.201, 2 CPU/4 GiB, 30 GiB disk), cks-worker (.202, 2 CPU/4 GiB, 100 GiB disk). The unused AWS EC2 harness is removed from tracked source. Preserve workstation `.secrets`, backups and ignored evidence. Provisioning or teardown requires action-time approval; a merge is not live approval.

The released trial chain before restructuring is platform v0.7.0 → enrollment v0.4.0 → tenant-app v0.3.0 → portal image v0.3.0. Operator-only Keycloak compatibility fixes are in enrollment v0.4.4. Headlamp and Keycloak/PostgreSQL were working; portal admin SSO and denial tests passed, but the 600-second observation failed at 588 seconds from host memory pressure. The user subsequently restored one portal replica. Recheck live state before operations; this document is not a health probe.

Paths in already published tags remain historical. This refactor does not update live source paths or tags. Advance to the new released path only in a separately reviewed activation; a root still pointing to an old path cannot consume this layout automatically. Do not replace an already watched tag.

## Boundaries

- Platform bootstrap knows the enrollment repository, selected cluster context and path, not individual tenants.
- Enrollment owns tenant namespaces, registration, deployment identities and security foundations. App repositories own applications.
- Platform-admin means full cluster-admin for the explicit platform admin group; that does not grant tenant deployers or workloads cluster-admin.
- Keep existing release pins, scoped installers, external credential inputs and live-approval gates. No auth redesign is part of this move.
- Rancher installation/platform-only OIDC configuration is active infrastructure Ansible, default off. It needs its own capacity budget and live approval; it remains absent from the historical tiny trial.

Private trial evidence is retained under the existing ignored operational checkout and `/tmp/portal-live-20261029/`; it must not be copied into Git. Memory headroom and runtime stability remain unresolved.

For source configuration, local now means a PE-owned physical cluster. The running VM trial has not been changed or removed; its provisioning workflow source is intentionally absent. Do not interpret the new local template as matching that running cluster.
