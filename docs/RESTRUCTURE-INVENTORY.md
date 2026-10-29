# Restructuring inventory

All historical Fleet tests and evidence producers are retained under `archive/fleet/local-lab/`. No raw operational evidence is moved from other worktrees. Portable evidence producers require explicit Big Bang catalog/identity adaptation before live use; historical passing tests do not prove the new stack.

## Retained historical checks

- `archive/fleet/local-lab/scripts/manage-security-findings.py`
- `archive/fleet/local-lab/scripts/run-tenant-security-suite.py`
- `archive/fleet/local-lab/scripts/tenant_catalog.py`
- `archive/fleet/local-lab/scripts/verify-rancher-tenant-ui.py`
- `archive/fleet/local-lab/scripts/verify-tenant-admission.py`
- `archive/fleet/local-lab/scripts/verify-tenant-network.py`
- `archive/fleet/local-lab/scripts/verify-tenant-observability.py`
- `archive/fleet/local-lab/scripts/verify-tenant-quota.py`
- `archive/fleet/local-lab/scripts/verify-tenant-rbac.py`
- `archive/fleet/local-lab/tests/fixtures/openbao/LICENSE`
- `archive/fleet/local-lab/tests/fixtures/openbao/README.md`
- `archive/fleet/local-lab/tests/fixtures/openbao/ingressroutetcp-v1alpha1.schema.json`
- `archive/fleet/local-lab/tests/fixtures/openbao/traefik-provider.json`
- `archive/fleet/local-lab/tests/fixtures/portal/README.md`
- `archive/fleet/local-lab/tests/fixtures/portal/admission-baseline.json`
- `archive/fleet/local-lab/tests/fixtures/portal/schemas/LICENSE`
- `archive/fleet/local-lab/tests/fixtures/portal/schemas/README.md`
- `archive/fleet/local-lab/tests/fixtures/portal/schemas/fleet-0.16.2.json`
- `archive/fleet/local-lab/tests/fixtures/portal/schemas/kubernetes-1.36.5.json`
- `archive/fleet/local-lab/tests/fixtures/portal/schemas/workload-types-1.36.5.json`
- `archive/fleet/local-lab/tests/fixtures/portal/workload.json`
- `archive/fleet/local-lab/tests/fixtures/tenant-demo.yaml`
- `archive/fleet/local-lab/tests/portal-cel/flux_portal_test.go`
- `archive/fleet/local-lab/tests/portal-cel/go.mod`
- `archive/fleet/local-lab/tests/portal-cel/go.sum`
- `archive/fleet/local-lab/tests/portal-cel/policy_test.go`
- `archive/fleet/local-lab/tests/portal-cel/requirements.txt`
- `archive/fleet/local-lab/tests/portal-cel/typecheck_test.go`
- `archive/fleet/local-lab/tests/portal_admission_cases.py`
- `archive/fleet/local-lab/tests/portal_fleet_fixture.py`
- `archive/fleet/local-lab/tests/test_check_profile_capacity.py`
- `archive/fleet/local-lab/tests/test_configure_keycloak_tenants.py`
- `archive/fleet/local-lab/tests/test_configure_rancher_oidc.py`
- `archive/fleet/local-lab/tests/test_manage_security_findings.py`
- `archive/fleet/local-lab/tests/test_observability_profile.py`
- `archive/fleet/local-lab/tests/test_openbao_secrets.py`
- `archive/fleet/local-lab/tests/test_platform_config.py`
- `archive/fleet/local-lab/tests/test_portal_activation.py`
- `archive/fleet/local-lab/tests/test_portal_boundary.py`
- `archive/fleet/local-lab/tests/test_portal_fleet.py`
- `archive/fleet/local-lab/tests/test_portal_identity.py`
- `archive/fleet/local-lab/tests/test_portal_release_storage.py`
- `archive/fleet/local-lab/tests/test_reconcile_tenant_rancher_bindings.py`
- `archive/fleet/local-lab/tests/test_render_tenant_foundation.py`
- `archive/fleet/local-lab/tests/test_run_tenant_security_suite.py`
- `archive/fleet/local-lab/tests/test_shared_foundation.py`
- `archive/fleet/local-lab/tests/test_verify_tenant_admission.py`
- `archive/fleet/local-lab/tests/test_verify_tenant_network.py`
- `archive/fleet/local-lab/tests/test_verify_tenant_observability.py`
- `archive/fleet/local-lab/tests/test_verify_tenant_quota.py`
- `archive/fleet/local-lab/tests/test_verify_tenant_rbac.py`
- `archive/fleet/local-lab/tests/validate_portal_schemas.py`

## Retained active Big Bang checks

Existing Big Bang tests were promoted, except the explicitly removed VM-only provisioning/tuning checks; the generic storage retention/pull-secret checks were retained. VM provisioning/recovery scripts, the old VM Ansible tree, VM-specific placement/budget tests and preflight capacity reports were removed following the explicit physical-local scope update. Their originals remain in Git history. Source pins/full-selection render values were retained under tests/fixtures; generic identity/security/render tests remain active. No raw evidence, secrets, disks or running VMs were removed.

## Ownership/move map

| Before | After | Reason |
|---|---|---|
| local-lab-big-bang/examples/* | big-bang-bootstrap/* | Promote maintained platform inputs |
| ansible/* | infrastructure/ansible/* | Separate host/RKE2 from platform |
| platform-config/* | big-bang-bootstrap/ansible/platform-config/* | Retain Ansible app API configuration |
| local-lab Fleet/catalog/generators | archive/fleet/local-lab | Historical assurance/implementation reference only |
| VM provisioning/rebuild and VM Ansible | Removed; Git history | No supported VM clusters |
| native Flux CEL harness | big-bang-bootstrap/tests/portal-cel | Preserve real policy evidence without Fleet generator tests |
| offline findings/API tests | big-bang-bootstrap/evidence + tests | Reuse cluster-independent assurance |

This does not complete #20's separate-app-repository proposal: its Fleet registration wording is superseded by #68. #14's Ansible configuration direction is retained. Neither issue is closed or implemented as a second deployment architecture.

The old Rancher installer remains historical under `archive/fleet/rancher-management`; it is not promoted as a portable management entrypoint because it assumes the old kubeconfig/private-state layout. Rancher lifecycle integration is retained as architecture, not silently installed or granted new permissions.

## Removed unused AWS harness

The 21-file `ansible/aws-lab` EC2/RKE2/CloudFormation/SSM/budget harness is removed, not archived as a supported path. It was unused. No AWS API was called and no resources, credentials, logs or data were torn down. No harness-specific test files existed outside that directory. Physical starter inventory/playbooks, generic bootstrap/render and assurance tests remain. Recover historical source with `git show v0.7.0:ansible/aws-lab/README.md` or inspect that released tree before any future reimplementation; restoring source is not execution approval.

## Review notes and bounded follow-ups

- Historical release CI must use the path that exists in its released tag. The v0.1.0 check now explicitly uses its old path; onboarding uses the new path and needs a new published release before any live ref/path advance. This is a mechanical correction, not activation.
- The separate enrollment/app releases still describe the previous trial's node, browser and identity settings. Physical adoption requires coordinated reviewed configuration/releases there; this PR does not edit those repositories or silently retarget their sources.
- Physical RHEL/RKE2 provisioning remains starter scaffolding. A bounded physical-readiness follow-up should choose storage/CSI, ingress/DNS/TLS ownership, capacity/HA and backup/recovery before activation. The retained static local PV is non-HA; a Retain policy is not backup.
- Archived catalog/Rancher-specific evidence probes need a current enrollment-owned target/expectation adapter before live reuse. Active native Flux policy, identity, storage and findings tests remain runnable offline. IL2 hardening/evidence readiness and portable Rancher management activation remain future work, not implied by profile names or folder moves.
