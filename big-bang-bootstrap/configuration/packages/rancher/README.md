# Rancher local-admin management stage

Rancher 2.15.2 was separately activated at **v0.12.0** on 2026-11-01. The
Rancher/Big Bang/root readiness, required runtime controller availability and
trusted HTTPS ping checks passed. **First login/password setup has not been
attempted.** Local administration only: no Keycloak/SSO, group/role mapping or
tenants. Publication alone never promotes the live source or authorizes another
credential/prerequisite operation; the procedure below records those separate
initial-install gates and must not be blindly repeated on this installed cluster.

Big Bang generates Rancher 2.15.2 from the official stable HelmRepository; Flux
owns reconciliation. Keep Longhorn 1.13.0 unchanged and its UI ingress disabled.
Rancher is platform-admin cluster lifecycle management, not another application
installer. Continuous Delivery is disabled; Rancher's required internal Fleet
controllers remain available. Do not install a second Longhorn through Rancher.

## Compatibility, capacity and trust

Checked against current vendor guidance on 2026-11-01:

- [Rancher 2.15.2 matrix](https://www.suse.com/suse-rancher/support-matrix/all-supported-versions/rancher-v2-15-2/)
  includes RKE2 1.34–1.36. The [RKE2 1.36 matrix](https://www.suse.com/suse-rke2/support-matrix/all-supported-versions/rke2-v1-36/)
  lists v1.36.5+rke2r1 and RHEL 10.2. The Rancher table lists Longhorn 1.12, not
  our independently Flux-managed 1.13; this custom combination is not claimed
  vendor-certified. Its Rancher coexistence remains a live acceptance question.
- [Installation requirements](https://documentation.suse.com/cloudnative/rancher-manager/latest/en/installation-and-upgrade/requirements/requirements.html)
  give 4 CPUs/16 GB per node as the small RKE2 management starting point and require
  HA for production. The recorded physical lab has six CPUs/16 GB installed RAM
  per node, but one control-plane/etcd server and **one Rancher replica**: no HA.
  Rancher requests 500m CPU/1Gi memory, with a 4Gi memory limit and CPU bursting.
  This is a provisional lab budget, not a measured load guarantee; check actual
  allocatable/usage and scheduling headroom before activation.
- The pinned official archive SHA256 is verified by the test fixture downloader.
  The selected render has 14 resources, including bootstrap/pre-upgrade hooks.
  Installer object permissions, every roleRef/bind and named escalation are tested.
  The chart gives `cattle-system:rancher` cluster-admin. Granting its installer
  named cluster-admin bind is effectively administrative delegation, not least
  privilege or tenant authority. Source-writer permission for the application root
  is only namespaced HelmRepository access, not RBAC self-grant.
- The optional broad post-delete cleanup hook is explicitly disabled; its unused
  named installer permissions are removed. Uninstall and data/controller cleanup
  need a separate reviewed action. The pre-upgrade hook remains authorized.
  The umbrella timeout is 15m, longer than the 10m child window, avoiding the
  earlier parent-timeout problem while retaining zero automatic remediation retries.

## Inputs and separately approved activation

The recorded DNS/private-CA design is retained: `rancher.perkforge.home.arpa`,
Traefik ingress, existing-Secret TLS, privateCA true, additionalTrustedCAs true,
and strict agent TLS. Existing-Secret TLS needs no second cert-manager installer.
Trusted HTTPS ping and required runtime controller availability passed in the
approved installation. Browser login and first-password setup are **not tested**.

| Protected input/reference | Purpose |
|---|---|
| Reviewed released tag/commit, kubeconfig/context/kube-system UID | Exact source and target; never substitute dirty/main/feature execution for gated prerequisite delivery |
| `cattle-system/tls-rancher-ingress`, tls.crt/tls.key | Existing issued leaf/chain and service key for the exact hostname |
| `cattle-system/tls-ca`, cacerts.pem | Public private-CA chain for agents; never the CA signing key |
| `cattle-system/tls-ca-additional`, ca-additional.pem | Public outbound CA trust; this does not configure SSO |
| `bigbang/rancher-bootstrap-values`, values.yaml | Required external Secret containing only a nonempty bootstrapPassword string |

The outer post-renderer appends that required bootstrap Secret to the child.
A missing Secret blocks Flux input resolution. Presence alone does not validate
its content: separately approved delivery must check the exact single key/type
and nonempty password before creation. No password is authored/generated here.
Use the approved credential store for durable custody; protected temporary files,
no_log/redacted delivery and cleanup are runtime concerns, not public Git values.
Helm/controller memory, the external Secret, the chart's retained bootstrap-secret
and Helm release-history Secrets are trusted runtime copies. Do not print them,
put passwords in CLI arguments/URLs, or use chart NOTES setup-URL convenience
commands. Changing values is not rotation: the chart preserves an existing
bootstrap-secret, which the real Helm lookup regression tests with dummy data.

After a new release and explicit action approval:

1. Verify exact target, published artifact, current Longhorn readiness and capacity;
   preserve existing storage/test resources and compare prerequisites for drift.
2. Use namespace-only `platform-tls.yaml` staging and separately approved TLS/public
   CA delivery. Validate SAN/chain/expiry/key matches first. Deliver the checked
   bootstrap values Secret separately without reading its contents into logs.
3. Apply reviewed common/Rancher prerequisites through default-off
   `rancher-prerequisites.yaml`, `rancher_foundation_apply=true`, from the clean
   published checkout. This grants the privileged namespace/installer and scoped
   source-writer access; it neither deploys Rancher nor delivers credentials.
4. Promote the existing source to the verified new release, verify its artifact,
   then observe umbrella/child/root. Do not rerun bootstrap on the active cluster.
   Use `readiness.yaml`, `platform_readiness_verify=true`,
   `platform_readiness_phase=rancher`, for the server checks. These do not prove
   browser login, all runtime Fleet/webhook health or lifecycle operations.
5. Verify hostname/chain and HTTPS without an insecure bypass before entering
   credentials. Use local admin, reset the first-login password privately and
   retain independent direct RKE2 administrator recovery access. Verify required
   runtime controllers before any later cluster lifecycle action. Stop before SSO.

Rancher Helm uses Kubernetes datastore resources, not an application PVC; do not
invent a Longhorn storage dependency. Storage-first is the completed operator
checkpoint, not a chart requirement. Keycloak readiness is needed for later OIDC,
not this initial local-admin installation.

## Deployment ownership and obsolete installer audit

The direct infrastructure Ansible installer was already deleted in #84
(`036f1ec`), including `playbooks/install-rancher.yml`, `tasks/rancher-install.yml`,
old Rancher vars and their old infrastructure test fixture. No remaining competing
installer file was found. Current Ansible prerequisites, TLS and later API
configuration are active shared responsibilities and are retained. RKE2 paths
under `/etc/rancher/rke2` belong to RKE2; they are not obsolete Rancher installers.
Do not reintroduce direct Helm install/upgrade or a second cert-manager path.

## Deferred platform-only OIDC

This initial stage does not run the configurator or approve its existing mappings.
Install Keycloak later, then review the original groups/roles before extending
authentication. Preserve the current definitions for that review.

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
