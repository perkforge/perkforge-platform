# Store ownership and consumer contract

These are inactive, reviewed-source candidates. Neither a current cluster root nor
controller installation selects the stores. Render with `kubectl kustomize
big-bang-bootstrap/configuration/external-secrets/stores/platform`; apply only in
the separately approved post-controller/auth/trust stage.

`openbao-platform` is cluster-scoped but initially accepts only `external-secrets`.
Its machine policy has **no data rights**. Each platform destination needs a
reviewed exact namespace, remote KV-v2 record, field, output Secret and consumer
before adding rights and an ExternalSecret. Never add a tenant namespace to this
store to work around its tenant policy. Do not use a wildcard namespace selector.

The platform public CA input is ConfigMap `external-secrets/openbao-ca`, key
`ca.crt`. Deliver only the verified public trust root, not a TLS private key,
OpenBao token or signing key. An empty/placeholder CA is deliberately not rendered.
The endpoint keeps the existing certificate hostname; private cluster service DNS
names must not be substituted without verified SAN coverage.

[Enrollment follow-up #51](https://github.com/perkforge/perkforge-platform-tenants/pull/51)
prepares the first inactive tenant stage, separately from the normal Portal
foundation and active enrollment source. The enrollment repository owns each tenant's namespaced `openbao-tenant`
SecretStore and separate non-mounting auth ServiceAccount. For physical Portal the
namespace is `tenant-portal`, the identity is `eso-tenant-portal`, and the only
candidate KV-v2 records are `tenants/tenant-portal/oidc`,
`tenants/tenant-portal/registry/ghcr`, and `tenants/tenant-portal/tls`. This is a new
proposed contract, not evidence of existing records. No old VM values are copied.
The Store omits namespaces on its local CA and ServiceAccount references. Its separate OpenBao CA
is `eso-openbao-ca`, key `ca.crt`, never a new app mount. Do not assume the
Portal-to-Keycloak `portal-identity-ca` has the same issuer or rotation lifecycle.

The auth mount is `kubernetes-eso`, audience `openbao-eso`, controller class
`perkforge`. Every tenant role binds one exact service-account name **and** one
namespace. No namespace glob, default policy, cross-tenant metadata listing or
write/delete capability is allowed. The SA gets no Kubernetes permissions.

Only the platform-owned enrollment reconciler may manage the Store/auth identity
and future ExternalSecrets. The app reconciler/deployer may not create Stores,
ExternalSecrets, ServiceAccounts, RBAC or token requests. Admission keeps Portal
on `portal-runtime` and rejects projected token volumes and alternate service
accounts. Verify direct Pod creation, exec and other workload escape paths are
also absent in effective tenant RBAC. `automountServiceAccountToken: false` alone
is not a token-isolation boundary.

No ExternalSecret is included in the foundation. Consumer delivery needs
separate review of exact field mappings, destination type and ownership. Preserve
`portal-oidc-existing/client-secret`, `portal-registry-existing` (docker config),
`portal-local-tls` (TLS), and `portal-identity-ca/ca.crt`. Existing/immutable Secret
ownership and collisions must be checked before activation. Prefer explicit
`spec.data` mappings over broad `dataFrom`/find. Retain downstream values if a
remote record disappears; do not trigger automatic cleanup/restart or assume an
application reloads a rotated Secret.
