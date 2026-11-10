# Alternative for baselines requiring tighter secret isolation

The initial baseline deliberately chooses one Big Bang-native trusted controller.
This alternative was source-inspected and rendered against the same pinned ESO
2.12.0-bb.0 wrapper. It is **not selected, deployed or live accepted**. Choose a
threat model before reusing the PaaS baseline in a different security boundary.

## What changes

One controller watching the entire cluster requires cluster-wide Secret
list/watch. Namespace Stores, controller classes, NetworkPolicy and disabled
caches do not prevent that controller from reading other namespaces through the
API. Kubernetes does not filter an all-namespace list to the namespaces allowed
by RoleBindings. Merely removing the global grant leaves that informer broken.

For controller-compromise separation:

1. Scope **every** controller's watch and Secret RBAC to one approved namespace.
   This includes the platform controller; retaining an unrestricted platform ESO
   still exposes tenant values even if tenant controllers are individually scoped.
2. Keep the native addon as the platform instance. Additional instances may use
   Big Bang `packages` with the **same pinned Big Bang wrapper** and Iron Bank
   image, not a fork. Track the native addon pin in validation so extras cannot
   drift. Add a dependency on the native CRD foundation and configure extra
   releases with `flux.install.crds: Skip` and `flux.upgrade.crds: Skip`.
3. Give each instance a unique service account and explicit namespaced RoleBinding,
   controller class and deployment name. Disable cluster Stores and unused
   cluster/push controllers for tenant-only instances. Keep native RBAC creation
   off when explicit narrower Roles own permissions.
4. Deploy controllers in protected namespaces where **no ESO controller may write
   Secrets**, for example `eso-tenant-portal`, while watching `tenant-portal`.
   Do not colocate a tenant controller SA in a platform Secret-writing namespace:
   Secret creation can mint a legacy service-account-token Secret for another SA
   in that namespace. A shared protected controller namespace is possible only
   when no controller has Secret-write or tenant-workload authority there.
5. Keep one exact OpenBao auth SA/namespace/audience and allowed KV paths per tenant.
   Tenant-controlled workloads must not impersonate auth/controller SAs. Separate
   roles do not protect against a compromised OpenBao administrator, node,
   cluster administrator or secret-bearing backup operator.

## Verified native values behavior

`upstream.scopedNamespace` takes one namespace, not a list. For protected tenant
placement, set `env.EXTERNAL_SECRETS_NAMESPACE` and `upstream.namespaceOverride`
to the protected deployment namespace, while `upstream.scopedNamespace` names the
tenant runtime namespace. Also use unique `upstream.fullnameOverride` and
`upstream.controllerClass`. Omitting the wrapper environment override rendered its
ConfigMap in `external-secrets` even when the release targeted another namespace.

`upstream.scopedRBAC: true` disables ClusterSecretStore processing. That is suitable
for a tenant SecretStore, not a platform ClusterSecretStore. A scoped platform
instance can use `scopedRBAC: false`, `rbac.create: false` and explicit permissions.
The cluster-scoped Store object itself does not require global Secret watching.

For **one shared platform ClusterSecretStore across several platform namespaces**,
each scoped consumer controller must keep ClusterSecretStore processing enabled.
In this exact version, disabling that reconciler also disables primary
ClusterSecretStore consumption. Same-class controllers will duplicate provider
validation and share status-writing ownership; conflicting auth/network visibility
can make readiness unstable. Separate per-namespace Stores/classes avoid that
contention but change the one-store model. Review and test that choice explicitly.

Leader election is off by native default. If enabled for replicas, independent
instances in a shared controller namespace require unique election IDs. A shared
lease is not a multi-namespace controller: the losing instance stops serving its
namespace. Explicit classes should be enforced in source/admission, but class
selection alone is not authorization because empty-class Stores are accepted.

## Operational costs

Each additional controller's pinned defaults request and limit **100m CPU and
256Mi RAM**, before any platform-specific adjustment. These are configured values,
not measured workload consumption. There is another release, service account,
RBAC/trust/network contract, pull-secret destination and upgrade/acceptance target
for every watched namespace. Additional generic `packages` entries do not inherit
every native-addon-specific image-pull, monitoring or network integration; carry
only the reviewed equivalent values and test the complete effective render.

Keep one owner for the exact native CRD bundle. Upgrade CRDs before compatible
controllers, validate all Store schema versions, and test each namespace's
positive/negative API and OpenBao boundaries. No chart fork is required, but this
is more configuration and maintenance than the baseline's single native addon.

## Evidence

- [Pinned Big Bang wrapper](https://repo1.dso.mil/big-bang/product/packages/external-secrets/-/tree/2.12.0-bb.0),
  including its separate `chart/crds` bundle and namespace environment input.
- [Single namespace cache and leader configuration](https://github.com/external-secrets/external-secrets/blob/v2.12.0/cmd/controller/root.go#L357-L392).
- [Unconditional Secret metadata watch](https://github.com/external-secrets/external-secrets/blob/v2.12.0/pkg/controllers/externalsecret/externalsecret_controller.go#L1425-L1435).
- [ClusterStore processing and consumption share one flag](https://github.com/external-secrets/external-secrets/blob/v2.12.0/pkg/controllers/externalsecret/externalsecret_controller.go#L1104-L1106).
- [Empty-class behavior](https://github.com/external-secrets/external-secrets/blob/v2.12.0/pkg/controllers/secretstore/common.go#L214-L220).
- [Kubernetes service-account-token Secrets](https://kubernetes.io/docs/concepts/configuration/secret/#serviceaccount-token-secrets).

Offline native renders verified a protected tenant Deployment/SA/ConfigMap with
only a tenant namespace watch, correct pinned image, disabled cluster processing,
and no generated cluster RBAC. This is source/render evidence, not deployed
controller startup, real RBAC enforcement or resistance to compromise.
