# Platform bootstrap and configuration operations

These are explicit Ansible operations, not another reconciler. All apply/verify gates default false; check mode must not contact APIs or read private inputs. configuration/ holds desired package/identity YAML; this directory executes reviewed bootstrap/application API steps.

## Readiness and activation order

1. Infrastructure: approved RHEL preparation → RKE2 nodes Ready; Longhorn host compatibility/preparation is separate. Rancher Helm belongs to the optional Big Bang package, with separate TLS/identity/capacity approval.
2. Bootstrap: install the verified Big Bang Flux prerequisite and seed a paused source/root. Choose the exact released cluster path, kubeconfig/context/UID and public/private source access explicitly.
3. Prerequisites: headlamp-prerequisites.yaml explicitly applies packages/bigbang/prerequisites then packages/headlamp/prerequisites. keycloak-prerequisites.yaml applies common Big Bang prerequisites then only packages/keycloak/prerequisites, with separately gated identity/routing and identity/kubernetes user grants. It does not prepare Headlamp. The shared Helm-history Role stays in Big Bang; each package owns its installer and binding. enrollment-prerequisites.yaml prepares only the generic protected enrollment writer. Existing foundation_apply and identity_foundation_apply gate names are retained for compatibility. External registry/database/OIDC/TLS inputs require concrete approval before named delivery.
4. Storage first (when selected): longhorn-prerequisites.yaml applies reviewed common/package namespace and privileged installer RBAC, never a chart or activation. The optional Longhorn child is suspended until later approval; verify readiness.yaml phase storage after activation. Keycloak defaults to its prerequisites-longhorn overlay and waits for Longhorn release/class readiness. Rancher prerequisites have their own default-off rancher-prerequisites.yaml; no Rancher Helm dependency on Longhorn is invented. DNS/TLS and an external bootstrap-values Secret precede Rancher Helm; Keycloak readiness precedes Rancher OIDC API configuration.
5. Packages: author the reviewed state in the one clusters/<name> root and outer HelmRelease. No trial stage roots remain. If a database-only checkpoint is required, set Keycloak replicas to0 in that authoritative configuration first, then review its activation/replica advance; do not create a second HelmRelease owner. Run readiness.yaml phase packages to wait PostgreSQL → Keycloak → Headlamp without changing them.
6. Identity: configure the new realm/client once, verify HTTPS discovery/JWKS and the exact callback/issuer/audience/groups. API OIDC is cross-layer maintenance: back up the RKE2 config and approve any control-plane restart separately; the existing CA-mount regression remains enforced. readiness.yaml phase identity checks verified discovery; identity-verify.yaml performs separately approved token/RBAC positive/negative checks using protected external tokens. Neither discovery nor UI login proves authorization.
7. Enrollment: only after identity/security acceptance, review source changes enabling the generic enrollment source/reconciler in enrollments/<name>. They default paused independently of the outer release. readiness.yaml phase enrollment waits that parent; tenant-specific foundations and app deployment remain in enrollment/app Git.

Kustomize file order is not readiness. Database startup also retains a bounded native readiness init-container. Checks observe status; they never activate, scale or create extra reconcilers. Enabling gates or resuming resources outside reviewed source cannot replace this sequence.

## Containment and recovery

Pause the affected root first, then the affected child source/reconciler/release before manually stopping new workloads. Root suspension stops manifest updates, not running services or every child controller. Preserve retained database data, backups and existing healthy Flux/services. Resume only from a reviewed canonical configuration; do not let an active parent undo containment. Existing published tags/old paths remain unchanged and provide historical source, not permission to run removed workflows.

Keep private logs locally with timestamps, symptoms, confirmed causes versus hypotheses, fixes and verification; no token/password/Secret bodies or shell tracing around credentials. The temporary laptop guardian was operational trial tooling, not a controller deployed by this code. Physical observation thresholds/duration and recovery actions require a new measured plan.

Rancher OIDC/admin configuration lives in `configure-rancher-oidc.yaml`, with
explicit private inputs overriding `vars/rancher-oidc.yml`. It is default-off,
contacts no cluster in check mode, and requires separate security-change approval
after Rancher and Keycloak readiness. See the Rancher package README. Infrastructure
contains no direct Rancher installer or Rancher API operations.

## TLS prerequisites before application activation

`platform-tls.yaml` prepares only explicitly named Headlamp/Keycloak/Rancher inputs.
Both platform_tls_namespaces_apply and platform_tls_apply default false; check
mode never reads key files or contacts Kubernetes. The first flag creates only
missing authored Namespace objects. It does not select charts, grant installer
RBAC, create PVCs or apply routes. Headlamp/Keycloak retain their standard namespace
labels; cattle-system retains the explicitly privileged PSA label required by its
separate reviewed package namespace. Rancher's Namespace file is split from
installer.yaml so namespace preparation cannot accidentally grant cluster-admin.

The delivery flag validates all selected leaf/key pairs and the recorded CA
fingerprint before writes, then creates (never overwrites) these exact resources:

| Namespace | Resource | Material |
|---|---|---|
| headlamp | Secret/headlamp-local-tls | Headlamp leaf and service key |
| headlamp | ConfigMap/identity-ca, ca.crt | Public root only; existing OIDC mount |
| keycloak | Secret/keycloak-local-tls | Keycloak leaf and service key |
| cattle-system | Secret/tls-rancher-ingress | Rancher leaf and service key |
| cattle-system | Secret/tls-ca, cacerts.pem | Public root for strict agent trust |
| cattle-system | Secret/tls-ca-additional, ca-additional.pem | Public root for outbound Keycloak trust |

Select an explicit nonempty platform_tls_applications list from headlamp, keycloak
and rancher; default is empty. OpenBao is rejected until its listener/localhost/
internal TLS contract is resolved. No root signing key is read or delivered.
Use the normal local platform inventory plus protected external vars for reviewed
config_tag/config_release_evidence, target_kubeconfig/target_context,
expected_cluster_uid, platform_tls_bundle and platform_tls_expected_ca_fingerprint.
All normal release checks apply: published immutable source, matching selection
annotations, exact clean checkout and exact cluster. Uncommitted work cannot be applied through this gate. Review/publish a compatible release first.

After release review and action-specific approval, invoke platform-tls.yaml with
platform_tls_applications set explicitly and the separately approved namespace/
delivery flags. Public CA identity and certificate chain/hostname/server purpose,
minimum30-day lifetime, matching keys, private directory/key modes and symlinks are
checked. Existing namespaces must match authored ownership/PSA labels. Existing
TLS/CA objects cause refusal, not implicit adoption/rotation. Creates use JSON over
stdin under no_log; no rendered credential manifest is written to disk or Git.
TLS readback verifies the exact stored certificate/key under redaction. Credentials
in transient facts are cleared. Partial failures can leave earlier objects created;
inspect metadata and plan resume/rotation explicitly rather than deleting them or
bypassing guards. There is no automatic credential rollback or prune.

This prepares inputs only. Routes, Headlamp/Keycloak deployment, Rancher selection,
API-server CA path/OIDC activation and live HTTPS still need separate operations.
Do not enable the legacy Keycloak local-PV path just to create its namespace: this
namespace-only stage has no storage dependency and does not bypass Longhorn checks.
