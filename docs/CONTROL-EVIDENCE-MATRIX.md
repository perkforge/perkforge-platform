# Tenant control and evidence matrix

Status describes repository implementation, not formal control satisfaction.
An `Implemented, unverified` status means source configuration exists but a
live enforcement test has not passed.

| Control | Tenant objective | Implementation path | Verification/evidence | Status |
|---|---|---|---|---|
| AC-2 | Manage tenant membership and remove access | Keycloak groups and Rancher project role bindings | Group membership change, token/session expiry, denied project/API access; sanitized JSON result | Planned; OIDC disabled |
| AC-3 | Enforce tenant project and namespace permissions | Rancher RoleTemplates, ProjectRoleTemplateBindings, Kubernetes RBAC | `local-lab/scripts/verify-tenant-rbac.py` records impersonated-group allow/deny checks; actual OIDC login and dashboard checks remain separate | Partially implemented; runner exists, no live bindings |
| AC-4 | Prevent unauthorized cross-tenant information flow | Default-deny NetworkPolicies and explicit service exceptions | `verify-tenant-network.py` records same-tenant allow, cross-tenant deny, and DNS allow; `verify-tenant-observability.py` checks the tenant scrape exception and denies tenant access to shared metrics/dashboard endpoints | Implemented, unverified; executable runners exist, no live result |
| AC-6 | Grant least privilege | Admin/developer/viewer RoleTemplates; no tenant cluster roles | `local-lab/scripts/verify-tenant-rbac.py` checks secrets, Roles/RoleBindings, service-account/token access and impersonation, Pod exec, namespace creation, cross-tenant operations, and cluster resources | Implemented, unverified; no live result |
| AU-12 | Generate useful audit records | Kubernetes audit, Rancher, Keycloak, and deployment logs | Event and audit-log source validation with timestamped samples | Planned |
| CM-6 | Enforce secure baseline settings | Pod Security Admission Restricted, NetworkPolicies, quotas, LimitRanges | `local-lab/scripts/verify-tenant-admission.py` server-side dry-run rejection cases and rendered-manifest checks | Implemented, unverified; runner exists, no live result |
| SC-7 | Protect tenant network boundaries | Canal/Calico NetworkPolicy and controlled ingress/egress | Opt-in probes in `verify-tenant-network.py` and `verify-tenant-observability.py`; external egress, ingress-controller paths, host and node-local traffic, and live observability behavior remain untested | Implemented, unverified; executable runners exist, no live result |
| SC-39 | Isolate tenant processes | Restricted PSA, non-privileged workloads, future supplemental admission controls | `local-lab/scripts/verify-tenant-admission.py` covers privileged, host namespace, hostPath, capability, and seccomp admission cases | Partially implemented; PSA labels and dry-run runner exist, no live enforcement result |
| SC-6 | Apply resource allocation limits | Rancher Project quotas, namespace ResourceQuota, and LimitRange defaults | `local-lab/scripts/verify-tenant-quota.py` checks project quota configuration, per-namespace reservation and quota configuration, LimitRange defaults, and namespace CPU/memory quota admission; aggregate project consumption and storage admission remain untested | Implemented, unverified; runner exists, no live result |
| CA-7 | Continuously assess security posture | Repeatable tenant test harness and evidence artifacts | Timestamped machine-readable test reports, findings, remediation state | Planned |

These mappings are engineering traceability. They do not establish that a
control is fully satisfied, inherited, assessed, authorized, or applicable to a
specific DoD information system. A finding must record the failed test and
residual risk rather than being omitted from evidence.
