# Platform bootstrap and configuration operations

These are explicit Ansible operations, not another reconciler. All apply/verify gates default false; check mode must not contact APIs or read private inputs. configuration/ holds desired package/identity YAML; this directory executes reviewed bootstrap/application API steps.

## Readiness and activation order

1. Infrastructure: approved RHEL preparation → RKE2 nodes Ready; optional Rancher management has separate TLS/identity/capacity approval.
2. Bootstrap: install the verified Big Bang Flux prerequisite and seed a paused source/root. Choose the exact released cluster path, kubeconfig/context/UID and public/private source access explicitly.
3. Prerequisites: headlamp-prerequisites.yaml explicitly applies packages/bigbang/prerequisites then packages/headlamp/prerequisites. keycloak-prerequisites.yaml applies common Big Bang prerequisites then only packages/keycloak/prerequisites, with separately gated identity/routing and identity/kubernetes user grants. It does not prepare Headlamp. The shared Helm-history Role stays in Big Bang; each package owns its installer and binding. enrollment-prerequisites.yaml prepares only the generic protected enrollment writer. Existing foundation_apply and identity_foundation_apply gate names are retained for compatibility. External registry/database/OIDC/TLS inputs require concrete approval before named delivery.
4. Packages: author the reviewed state in the one clusters/<name> root and outer HelmRelease. No trial stage roots remain. If a database-only checkpoint is required, set Keycloak replicas to0 in that authoritative configuration first, then review its activation/replica advance; do not create a second HelmRelease owner. Run readiness.yaml phase packages to wait PostgreSQL → Keycloak → Headlamp without changing them.
5. Identity: configure the new realm/client once, verify HTTPS discovery/JWKS and the exact callback/issuer/audience/groups. API OIDC is cross-layer maintenance: back up the RKE2 config and approve any control-plane restart separately; the existing CA-mount regression remains enforced. readiness.yaml phase identity checks verified discovery; identity-verify.yaml performs separately approved token/RBAC positive/negative checks using protected external tokens. Neither discovery nor UI login proves authorization.
6. Enrollment: only after identity/security acceptance, review source changes enabling the generic enrollment source/reconciler in enrollments/<name>. They default paused independently of the outer release. readiness.yaml phase enrollment waits that parent; tenant-specific foundations and app deployment remain in enrollment/app Git.

Kustomize file order is not readiness. Database startup also retains a bounded native readiness init-container. Checks observe status; they never activate, scale or create extra reconcilers. Enabling gates or resuming resources outside reviewed source cannot replace this sequence.

## Containment and recovery

Pause the affected root first, then the affected child source/reconciler/release before manually stopping new workloads. Root suspension stops manifest updates, not running services or every child controller. Preserve retained database data, backups and existing healthy Flux/services. Resume only from a reviewed canonical configuration; do not let an active parent undo containment. Existing published tags/old paths remain unchanged and provide historical source, not permission to run removed workflows.

Keep private logs locally with timestamps, symptoms, confirmed causes versus hypotheses, fixes and verification; no token/password/Secret bodies or shell tracing around credentials. The temporary laptop guardian was operational trial tooling, not a controller deployed by this code. Physical observation thresholds/duration and recovery actions require a new measured plan.
