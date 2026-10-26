# Tenant control and evidence matrix

Status describes repository implementation, not formal control satisfaction.
An `Implemented, unverified` status means source configuration exists but a
live enforcement test has not passed.

| Control | Tenant objective | Implementation path | Verification/evidence | Status |
|---|---|---|---|---|
| AC-2 | Manage tenant membership and remove access | Keycloak groups and Rancher project role bindings | Synthetic tenant groups and Rancher OIDC are configured; browser login, group-claim behavior, membership revocation, and session-expiry behavior remain unverified | Partially implemented; user-flow validation pending |
| AC-3 | Enforce tenant project and namespace permissions | Rancher RoleTemplates, ProjectRoleTemplateBindings, Kubernetes RBAC | Live `verify-tenant-rbac.py` run passed 94/94 impersonated-group API authorization checks; interactive OIDC login and dashboard behavior remain separate | API authorization verified; browser SSO/dashboard pending |
| AC-4 | Prevent unauthorized cross-tenant information flow | Default-deny NetworkPolicies and explicit service exceptions | Live network verifier passed 7/7 checks for same-tenant traffic, cross-tenant denial, Keycloak discovery, and DNS; shared-observability access checks remain pending | Basic pod-network boundary verified; observability boundary pending |
| AC-6 | Grant least privilege | Admin/developer/viewer RoleTemplates; no tenant cluster roles | Live impersonated-group verifier passed 94/94 allowed/denied checks, including secrets, RBAC edits, service-account/token access, exec, namespace creation, cluster resources, and cross-tenant access | API authorization verified; SSO-derived identity still pending |
| AU-12 | Generate useful audit records | Kubernetes audit, Rancher, Keycloak, and deployment logs | Event and audit-log source validation with timestamped samples | Planned |
| CM-6 | Enforce secure baseline settings | Pod Security Admission Restricted, NetworkPolicies, quotas, LimitRanges | Live Pod Security Admission server-side dry-run matrix passed 9/9 compliant/violation cases; runtime behavior is not exercised by dry-run | Admission verified at API admission; runtime behavior pending |
| SC-7 | Protect tenant network boundaries | Canal/Calico NetworkPolicy and controlled ingress/egress | Live network suite passed 7/7 for same-tenant HTTP, cross-tenant denial, Keycloak discovery, and DNS. External egress, ingress-controller paths, host/node-local traffic, and observability flows remain untested | Core pod-network tests verified; broader boundary tests pending |
| SC-39 | Isolate tenant processes | Restricted PSA, non-privileged workloads, future supplemental admission controls | Live server-side dry-run rejected privileged, host namespace, hostPath, root, privilege escalation, unconfined seccomp, and added capability cases (9/9 total including compliant Pod) | Admission verified; runtime behavior and shared-kernel limits remain |
| SC-6 | Apply resource allocation limits | Rancher Project quotas, namespace ResourceQuota, and LimitRange defaults | Live quota verifier passed 4/4 configuration/admission cases, including Rancher project ceilings, namespace reservations, LimitRange defaults, and CPU/memory quota dry-runs; aggregate consumption and storage admission remain untested | Configuration and tested admission paths verified; aggregate/storage tests pending |
| CA-7 | Continuously assess security posture | Repeatable tenant test harness and evidence artifacts | One-command runner executes RBAC, admission, quota, and network checks and writes timestamped JSON/Markdown summaries; scheduling, alerting, findings ownership, and remediation tracking remain | Partially implemented; manually invoked evidence suite |

These mappings are engineering traceability. They do not establish that a
control is fully satisfied, inherited, assessed, authorized, or applicable to a
specific DoD information system. A finding must record the failed test and
residual risk rather than being omitted from evidence.
