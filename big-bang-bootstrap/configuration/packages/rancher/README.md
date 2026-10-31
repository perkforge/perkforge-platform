# Optional Rancher management package

Prepared, unselected and suspended. Big Bang generates Rancher 2.15.2's HelmRelease;
Flux owns Helm reconciliation. The official stable HelmRepository is declared once
in this optional directory (avoiding shared helmRepositories list collisions).
The outer post-renderer appends required bigbang/rancher-bootstrap-values,
values.yaml, to the generated release. That external Secret must contain only the
reviewed bootstrapPassword value and must be delivered separately without logging.
No plaintext credential is authored here. Missing Secret blocks installation
instead of implicitly generating a password. The selected local hostname is
rancher.perkforge.home.arpa; DNS resolution and matching TLS remain prerequisites.

Use existing cattle-system/tls-rancher-ingress with matching reviewed DNS/SANs and
Traefik ingress. External TLS avoids a second cert-manager installer. The selected private CA requires cattle-system/tls-ca (cacerts.pem) for the
privateCA:true setting and tls-ca-additional (ca-additional.pem) for the
additionalTrustedCAs:true outbound Keycloak trust mount. Deliver only the public
root into these Secrets, never its signing key. Agent/browser trust and Secret
delivery remain separately reviewed actions. The package
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

RKE2/host creation and recovery remain infrastructure Ansible. Rancher installation
has one owner: Big Bang/Flux. There is no direct infrastructure Helm installer.
Platform OIDC configuration is a separately gated API operation under
configuration/ansible/configure-rancher-oidc.yaml, after Rancher and Keycloak readiness.

For later activation select this directory in the authoritative cluster root,
review hostname/TLS/credentials, source permissions and resource capacity, then
explicitly clear the child suspend flag under approved bootstrap. Storage-first is
a useful rollout checkpoint, but Rancher has no fabricated Longhorn dependency.
OIDC configuration depends on a ready Keycloak, not the initial Rancher Helm release.

## Platform-only OIDC

`configuration/ansible/configure-rancher-oidc.yaml` consumes explicit HTTPS issuer/client inputs and an existing protected client-secret file. Keycloak client creation/group membership and CA delivery remain separately approved prerequisites; callback is `https://<hostname>/verify-auth`, with full-path `groups` claims. Server-to-server endpoints remain HTTPS and must already be trusted by Rancher.

`accessMode: required` admits only explicitly authorized principals; unlike `restricted`, it does not add implicit cluster/project-member login. Only `genericoidc_group:///platform/admins` is allowed/mapped by default, explicitly to the existing `admin` GlobalRole. No tenant or application-developer principal is accepted, no local-auth provider is disabled, and no ProjectRole/ClusterRole tenant workflow is recreated. Separate PE groups/roles require a deliberate reviewed choice; do not infer that application developers are platform engineers or admins.

The configurator refuses competing enabled external providers, unowned existing provider settings, unknown roles and conflicting immutable bindings before writes. It uses a resourceVersion-checked private-stdin patch, compares only authored nonsecret fields, preserves unrelated server defaults and avoids resending unchanged client credentials. Changing the secret file alone is not a credential-rotation workflow; rotation needs separate review. Omitted owned bindings require explicit revocation review; it never silently leaves that change unreported or deletes grants. Secret-bearing tasks use no_log and no credential appears in command arguments or tracked files.

The OIDC apply flag defaults false; check mode reads no secrets and performs no cluster calls. OIDC live approval must cover the client credential, AuthConfig and GlobalRoleBinding permissions; Helm activation is separate. No role membership, current service or live setting has changed.

## Validation limits

Offline tests execute real Ansible against synthetic CLI state, covering safe defaults, cluster identity, exposed credentials, exact admin mapping, unowned/conflicting providers/bindings, break-glass preservation and idempotent managed fields. Pinned chart rendering checks the feature/TLS inputs. Actual login, external CA/client interoperability, effective PE/admin permissions and system-controller behavior still need separately approved live tests.

API fields are checked against [Generic OIDC](https://github.com/rancher/rancher/blob/v2.15.2/pkg/apis/management.cattle.io/v3/authn_types.go) and [GlobalRoleBinding](https://github.com/rancher/rancher/blob/v2.15.2/pkg/apis/management.cattle.io/v3/authz_types.go) definitions.

OIDC defaults are in `configuration/ansible/vars/rancher-oidc.yml`.

The namespace-only TLS stage uses prerequisites/namespace.yaml without applying
installer.yaml. Installer privileges remain separately approved. The gated
platform-tls.yaml creates the leaf Secret and public CA Secrets only after reviewed
release/target checks and explicit namespace/delivery approval; it never unpauses
this optional package.
