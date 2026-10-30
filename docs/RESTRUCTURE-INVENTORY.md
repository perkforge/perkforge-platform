# Restructuring and evidence inventory

## Ownership and moves

| Previous source | Current owner/location |
|---|---|
| root ansible/ physical starter | infrastructure/ansible; recovered gated RKE2/Rancher logic |
| local-lab-big-bang/examples/{shared,apps,bigbang,identity,ansible} | big-bang-bootstrap/configuration/{defaults,packages,identity,ansible} |
| cluster/enrollment/profile/provider roots | big-bang-bootstrap/{clusters,enrollments,profiles,providers} |
| nested trial stages | removed; one authoritative cluster root plus native Ansible readiness/runbook |
| platform-config | configuration/ansible/platform-config; mutable app APIs only |
| generic findings register/tests | repository-root evidence/ and evidence/tests |
| custom Fleet deployment/catalogs | archive/fleet; historical, not an active deployment alternative |

The first draft wrongly archived Rancher as a capability and retained an empty physical RKE2 installer. Local review corrections recover RKE2 install/configure/join/readiness and platform-only Rancher installation/OIDC in infrastructure Ansible. PXE/Kickstart installs RHEL; OS preparation remains a starter. Big Bang Ansible seeds Flux/configuration, then Flux reconciles packages. No private inventory/address or credential is committed.

## Preserved assurance

- Configuration: test_package_inventory, test_headlamp, test_identity_packages, test_selection_contract now cover full renders, optional packages, resource/PVC inventory, target/profile/context/pins and managed defaults.
- Bootstrap: test_package_bootstrap, test_identity_bootstrap and test_release_seed retain no-op/check-mode, paused public source/seed, named-secret/private-stdin and one-shot realm safety.
- Security: test_headlamp_permissions, test_identity_permissions and test_portal_boundaries retain scoped installers, exact admin versus restricted user rights, OIDC/CA/claim contracts and tenant deployment/runtime separation. security/cel preserves all38 native Flux policy cases and schema-aware checking.
- Offline integration: test_postgres_lookup executes actual chart server-side lookup against synthetic APIs; test_openbao_api and test_portal_identity_api execute real Ansible against loopback HTTPS fixtures. No real credentials or cluster are used.
- Shared evidence: test_manage_security_findings retains report import, reviewed risk/closure/retest and private-state checks. Infrastructure tests cover physical install gating/templates and management CLI/API fixture flows.
- Historical producers and their tests remain under archive/fleet/local-lab: verify-tenant-{rbac,network,quota,admission,observability}.py, run-tenant-security-suite.py, verify-rancher-tenant-ui.py, OpenBao validation and their fixtures. Rancher/catalog assumptions need a current enrollment-owned expectation adapter before live reuse; nothing claims the old fixture is proof of the new target.

## Removals and intentional differences

VM provisioning/rebuild/teardown, VM Ansible, VM-specific Flux placement/budget tests and preflight capacity reports are removed. Source pins/full-selection test inputs remain in tests/fixtures; generic storage retention, pull-secret and security assertions were preserved when removing VM budget assumptions. The unused21-file AWS EC2/RKE2 harness and references are removed. Source can be recovered from v0.7.0 Git history; recovery is not execution approval. No VM/cloud resource, secret, backup or raw evidence was removed.

Only physical local + illustrative il2 ships. No concrete dev/il5 target exists; documented copy/edit steps and temporary test fixtures exercise extension. Personal IP/domain/node/storage assumptions become visible operator placeholders; the old personal Headlamp hosts alias is removed in favor of reviewed DNS. Generic enrollment now remains paused until identity acceptance. The outer release and bootstrap seed remain paused too. Namespaced RBAC object IDs are preserved even where historical names contain stage, avoiding an unreviewed permission-object migration.

Rancher2.15.2 requires core Fleet internally for provisioning; continuous-delivery=false disables application GitOps/gitjob/UI, not that dependency. No Fleet application GitRepo or tenant Project workflow is restored. Platform-only Generic OIDC uses accessMode required (restricted would admit implicit project/cluster members), preserves local break-glass auth and maps only explicit platform/admins to existing admin by default. Separate engineer-group grants require review.

## Release/testing boundaries and follow-ups

Historical v0.1.0 CI uses its actual old released path; new onboarding requires a new verified release/root-path advance. Configuration, chart and third-party action pins are retained. Existing live consumers of old tags are unchanged.

Review code first, then comprehensive integration/security/persistence/recovery tests before physical adoption. Existing disposable VMs may temporarily supply test infrastructure without restoring their provisioning workflow or redefining physical local. Still needed: coordinated enrollment/app physical inputs/releases; RHEL/SSH/network/OS prerequisites, storage/CSI/HA/DNS/TLS/backup readiness; actual Rancher dependencies/SSO and PE grants; adapted live evidence probes; IL2 preparation. The retained static local PV is non-HA and Retain is not backup. No physical-readiness or authorization claim is made.

Pinned-source investigation: Big Bang3.35.1 renders a shared wrapper GitRepository when its custom-package map is nonempty, even if that entry is disabled and its wrapper is false (templates/wrapper/gitrepository.yaml). The unselected OpenBao entry was removed from the authoritative local values rather than accepting an accidental dependency. Optional OpenBao is rendered explicitly only in its offline full-selection fixture until selected/reviewed for a target; default-source regression remains strict.
