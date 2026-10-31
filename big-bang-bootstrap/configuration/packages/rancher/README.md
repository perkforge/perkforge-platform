# Optional Rancher management package

Prepared, unselected and suspended. Big Bang generates Rancher 2.15.2's HelmRelease;
Flux owns Helm reconciliation. The official stable HelmRepository is declared once
in this optional directory (avoiding shared helmRepositories list collisions).
The outer post-renderer appends required bigbang/rancher-bootstrap-values,
values.yaml, to the generated release. That external Secret must contain only the
reviewed bootstrapPassword value and must be delivered separately without logging.
No plaintext credential or actual hostname is authored here. Missing Secret blocks
installation instead of implicitly generating a password. The input hostname is
UNCONFIGURED.invalid and must be replaced before any activation.

Use existing cattle-system/tls-rancher-ingress with matching reviewed DNS/SANs and
Traefik ingress. External TLS avoids a second cert-manager installer. Private CA,
agent/browser trust and extra trust bundles require explicit review. The package
has one lab replica, strict agent TLS, no Flux dependency on Longhorn and disables
Continuous Delivery without disabling Rancher's internal Fleet provisioning dependency.
Rancher stores management resources in the Kubernetes datastore, so its Helm
installation needs no application PVC; installing it is separate from storage.

prerequisites/ contains the namespace and privileged installer/source RBAC. The
upstream chart binds Rancher's runtime service account to cluster-admin; granting
the installer named cluster-admin bind rights is effectively administrative authority,
not tenant access. Review this and actual chart hooks before separate approval.
rancher-prerequisites.yaml is default-off, verifies published clean source and exact
cluster identity, and applies only common/package prerequisites. It neither starts
Rancher nor delivers TLS/bootstrap credentials nor activates Big Bang.

RKE2/host creation and recovery remain infrastructure Ansible. The direct Ansible
Helm installer defaults to refusing under rancher_deployment_owner=bigbang. Its
explicit legacy owner override is only for separately reviewed recovery/migration,
never alongside Flux. The existing configure-rancher-oidc.yml remains a gated API
operation after Rancher, Keycloak issuer/JWKS, TLS and admin-group acceptance.
Preserve break-glass access; application developers/tenants do not get platform admin.

For later activation select this directory in the authoritative cluster root,
review hostname/TLS/credentials, source permissions and resource capacity, then
explicitly clear the child suspend flag under approved bootstrap. Storage-first is
a useful rollout checkpoint, but Rancher has no fabricated Longhorn dependency.
OIDC configuration depends on a ready Keycloak, not the initial Rancher Helm release.
