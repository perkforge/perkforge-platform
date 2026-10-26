# Tenant control and evidence matrix

Status describes repository implementation, not formal control satisfaction.
An `Implemented, unverified` status means source configuration exists but a
live enforcement test has not passed.

| Control | Tenant objective | Implementation path | Verification/evidence | Status |
|---|---|---|---|---|
| AC-2 | Manage tenant membership and remove access | Keycloak groups and Rancher project role bindings | Playwright authenticated the synthetic Alpha viewer through Keycloak and confirmed Alpha project access; group removal/revocation and session expiry remain unverified | Synthetic user flow verified; lifecycle/revocation pending |
| AC-3 | Enforce tenant project and namespace permissions | Rancher RoleTemplates, ProjectRoleTemplateBindings, Kubernetes RBAC | Live `verify-tenant-rbac.py` passed 94/94 impersonated-group checks. Playwright confirmed Alpha project/pod access and HTTP 403 for direct Bravo project/pod reads | Selected browser/UI-session and API authorization verified; remaining roles/workflows pending |
| AC-4 | Prevent unauthorized cross-tenant information flow | Default-deny NetworkPolicies and explicit service exceptions | Live network verifier passed 7/7 checks for same-tenant traffic, cross-tenant denial, Keycloak discovery, and DNS; observability service boundary checks await Fleet deployment | Basic pod-network boundary verified; observability runtime boundary pending |
| AC-6 | Grant least privilege | Admin/developer/viewer RoleTemplates; no tenant cluster roles | Live impersonated-group verifier passed 94/94 checks. Alpha viewer browser session received HTTP 403 for Bravo project/pods and secret listing in both tenant namespaces | Selected viewer least-privilege paths verified; other role browser flows pending |
| AU-12 | Generate useful audit records | Kubernetes audit, Rancher, Keycloak, and deployment logs | Event and audit-log source validation with timestamped samples | Planned |
| CM-6 | Enforce secure baseline settings | Pod Security Admission Restricted, NetworkPolicies, quotas, LimitRanges | Live Pod Security Admission server-side dry-run matrix passed 9/9 compliant/violation cases; runtime behavior is not exercised by dry-run | Admission verified at API admission; runtime behavior pending |
| SC-7 | Protect tenant network boundaries | Canal/Calico NetworkPolicy and controlled ingress/egress | Live network suite passed 7/7 for same-tenant HTTP, cross-tenant denial, Keycloak discovery, and DNS. External egress, ingress-controller paths, host/node-local traffic, and observability flows remain untested | Core pod-network tests verified; broader boundary tests pending |
| SC-39 | Isolate tenant processes | Restricted PSA, non-privileged workloads, future supplemental admission controls | Live server-side dry-run rejected privileged, host namespace, hostPath, root, privilege escalation, unconfined seccomp, and added capability cases (9/9 total including compliant Pod) | Admission verified; runtime behavior and shared-kernel limits remain |
| SC-6 | Apply resource allocation limits | Rancher Project quotas, namespace ResourceQuota, and LimitRange defaults | Live quota verifier passed 4/4 configuration/admission cases, including Rancher project ceilings, namespace reservations, LimitRange defaults, and CPU/memory quota dry-runs; aggregate consumption and storage admission remain untested | Configuration and tested admission paths verified; aggregate/storage tests pending |
| CA-7 | Continuously assess security posture | Repeatable tenant test harness and evidence artifacts | One-command runner writes timestamped JSON/Markdown summaries and untriaged finding candidates for failed checks; a separate Playwright script checks a synthetic tenant login and positive/negative access. Execution errors are not findings. Scheduling, alerting, risk assessment, findings ownership, and remediation tracking remain | Partially implemented; manually invoked evidence suite and candidate extraction |

These mappings are engineering traceability. They do not establish that a
control is fully satisfied, inherited, assessed, authorized, or applicable to a
specific DoD information system. A finding must record the failed test and
residual risk rather than being omitted from evidence.
