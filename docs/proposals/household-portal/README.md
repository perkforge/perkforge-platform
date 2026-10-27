# Household portal integration proposal — INACTIVE

This directory is documentation and review material. It is outside every active
Fleet GitRepo path and tenant catalog index. Merging it creates no namespace,
workload, network allowance, identity client or privilege. Do not apply these files.

Portal is a protected Home household app, with a proposed separate namespace
`tenant-home-portal` in existing `local:p-home-local`. It is not a synthetic tenant
and gets no platform-admin, Rancher dashboard, Kubernetes API or cross-tenant
bypass. Existing Nextcloud resources and allocations must remain untouched.

Before activation, append a portal environment to Home via the existing catalog
loader and renderer; explicitly review the aggregate Home budget increase and
fresh capacity. Do not hand-edit generated tenant-foundation resources. Run
`python3 local-lab/scripts/render-tenant-foundation.py --check` and the offline
suite. The paused Keycloak and memory pressure remain deployment blockers.

Fleet should follow the existing scoped workspace model: `fleet-home-portal`,
Policy restricting the exact `perkforge-tenant-portal` repository, `allowNamespaceCreation: false`,
required `home-portal-deployer`, and a mapping limited to fleet-local/local with
both Home and portal labels. The workload GitRepo must use reviewed immutable SHA,
`keepResources: true`, `targetNamespace: tenant-home-portal`, and be paused until
activation is separately authorized. No registration is added now: there is not
yet an approved tenant commit/image or resolved Helm release-storage boundary.

`rbac.yaml.example` is a proposed deployer boundary only. The runtime account has
no RoleBinding and must disable automount. Do not grant Secret reads to the app
or its deployer; an operator-managed Secret can be mounted by an approved workload,
which means deployment authority still effectively permits reading that mounted
secret. That residual privilege requires review. No namespace/RBAC/quota/policy/
PVC/CRD authority, wildcard verbs, or ClusterRoleBinding is proposed.

`networkpolicy.yaml.example` defaults to deny both directions, allowing DNS only.
It deliberately does not yet allow ingress or identity: approved TLS proxy and
Keycloak endpoint routing are unresolved. No broad namespace egress, API server,
GitLab or Internet allowance is proposed. The app defaults to loopback locally; the inactive tenant chart explicitly selects
pod networking and needs a reviewed internal HTTPS ingress topology. Future NetworkPolicy allowances
must use verified namespace AND pod selectors and exact ports; validate actual
CNI enforcement rather than inferring it from rendered YAML.

GitLab integration stays disabled. The API stub's source is exact logical path
`/PerkForge/platform/tenants`, direct subgroups only, with clearly labeled fixture
metadata. Future live read scope and household visibility rules need separate
approval. No Keycloak/GitLab admin credentials or grants are part of this proposal.

Approval sequence: capacity → tenant quota/lifecycle review → image/config and
TLS topology → exact OIDC audience/role/group mapping → scoped Fleet registration
and network enforcement tests → explicit deployment. Backup/recovery and protected
lifecycle safeguards must be considered before introducing persistent portal data.

## Three repositories

Application source/tests/image build: `perkforge/perkforge-portal`. Tenant Helm/Fleet
bundle and app configuration: `perkforge/perkforge-tenant-portal`, path
`bundles/portal`. Platform foundations/security and registration stay here.
The tenant chart renders no objects by default (`enabled: false`) and only a
Deployment/ClusterIP Service when explicitly configured. It cannot own RBAC,
service accounts or NetworkPolicy. See [tenant boundary plan](../../TENANT-REPOSITORY-BOUNDARY.md).

The example `fleet.yaml.example` is paused, outside active paths, and deliberately
has an unresolved revision. It is review material, not ready for application.
The no-Secret deployer boundary has an unresolved Fleet/Helm release-storage
compatibility gate; do not add broad Secret rights as a workaround.
