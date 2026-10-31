# Rancher: platform cluster management

Rancher Helm deployment now belongs to the optional Big Bang custom package,
reconciled by Flux. It is prepared, unselected and suspended; nothing is installed.
Infrastructure Ansible retains host/RKE2 operations and the separately gated OIDC/
platform-admin API configuration. See [package procedure](../../../big-bang-bootstrap/configuration/packages/rancher/README.md).

## Ownership and dependencies

The direct `playbooks/install-rancher.yml` is a legacy recovery path, blocked by default
under `rancher_deployment_owner: bigbang`; an explicit separately reviewed Ansible
owner override must never coexist with Flux. Its offline fixture tests are retained.
Legacy inputs use `group_vars/rancher.yml` and `values.yaml.j2`. The operator supplies existing kubectl/Helm, exact kubeconfig/context/cluster UID, hostname/ingress class, protected exact/nonblank bootstrap-password file (no accidental trailing newline) and ingress TLS prerequisites. Versions remain Rancher 2.15.2 and optional cert-manager 1.21.2. No client binary, password, CA or TLS key is silently generated. Helm uses direct official --repo URLs without changing or refreshing the operator's unrelated cached repositories.

Ingress uses the existing `cattle-system/tls-rancher-ingress` Secret. Private-CA deployments also require reviewed Rancher CA trust (`tls-ca`/additional trusted CA configuration as appropriate) and browser/agent trust. No TLS verification bypass is allowed. cert-manager installation defaults off: choose one lifecycle owner and do not compete with Big Bang or another installer.

Rancher provisioning requires Fleet internally. Disable **Continuous Delivery** (`continuous-delivery=false`), not the Fleet dependency. No Fleet application GitRepo or tenant deployment workflow is configured; Flux owns application reconciliation. Rancher and its system dependencies still require inventory/capacity and actual startup validation. See [official v2.15 feature flags](https://ranchermanager.docs.rancher.com/v2.15/getting-started/installation-and-upgrade/installation-references/feature-flags) and [pinned feature source](https://github.com/rancher/rancher/blob/v2.15.2/pkg/features/feature.go).

## Platform-only OIDC

`playbooks/configure-rancher-oidc.yml` consumes explicit HTTPS issuer/client inputs and an existing protected client-secret file. Keycloak client creation/group membership and CA delivery remain separately approved prerequisites; callback is `https://<hostname>/verify-auth`, with full-path `groups` claims. Server-to-server endpoints remain HTTPS and must already be trusted by Rancher.

`accessMode: required` admits only explicitly authorized principals; unlike `restricted`, it does not add implicit cluster/project-member login. Only `genericoidc_group:///platform/admins` is allowed/mapped by default, explicitly to the existing `admin` GlobalRole. No tenant or application-developer principal is accepted, no local-auth provider is disabled, and no ProjectRole/ClusterRole tenant workflow is recreated. Separate PE groups/roles require a deliberate reviewed choice; do not infer that application developers are platform engineers or admins.

The configurator refuses competing enabled external providers, unowned existing provider settings, unknown roles and conflicting immutable bindings before writes. It uses a resourceVersion-checked private-stdin patch, compares only authored nonsecret fields, preserves unrelated server defaults and avoids resending unchanged client credentials. Changing the secret file alone is not a credential-rotation workflow; rotation needs separate review. Omitted owned bindings require explicit revocation review; it never silently leaves that change unreported or deletes grants. Secret-bearing tasks use no_log and no credential appears in command arguments or tracked files.

Both install/configure apply flags default false; check mode reads no secrets and performs no cluster calls. Future live approval must cover Helm/CRDs/system components, named TLS/bootstrap/OIDC credentials, AuthConfig and GlobalRoleBinding permissions. No role membership, current service or live setting has changed.

## Validation limits

Offline tests execute real Ansible against synthetic CLI state, covering safe defaults, cluster identity, exposed credentials, exact admin mapping, unowned/conflicting providers/bindings, break-glass preservation and idempotent managed fields. Pinned chart rendering checks the feature/TLS inputs. Actual login, external CA/client interoperability, effective PE/admin permissions and system-controller behavior still need separately approved live tests.

API fields are checked against [Generic OIDC](https://github.com/rancher/rancher/blob/v2.15.2/pkg/apis/management.cattle.io/v3/authn_types.go) and [GlobalRoleBinding](https://github.com/rancher/rancher/blob/v2.15.2/pkg/apis/management.cattle.io/v3/authz_types.go) definitions.
