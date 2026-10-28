# Paused portal tenant enrollment

This folder is **platform-owned enrollment**, separate from privileged Big Bang
packages in `apps/openbao/`. Both `clusters/local` and `clusters/dev` explicitly
include it for the illustration; a shared definition installs nothing by itself.
The local Kustomize file assembles only a paused GitRepository and Flux
Kustomization in the proposed `tenant-example-portal` namespace. It does not
create the namespace, tenant apps, RBAC, secrets or a Big Bang portal package.

## Ownership and flow

```text
platform foundation (future reviewed namespace, boundaries, identities)
 → platform-owned GitRepository + Flux Kustomization enrollment
 → tenant repository's paused Flux app entrypoint
 → tenant-owned app HelmRelease/configuration
 → existing tenant-owned portal chart, under a scoped deployment identity
```

Platform owns `source.yaml` and `reconcile.yaml`, their source pin/path and the
identity contract. The platform parent's `platform-reconciler` applies enrollment
resources from protected platform Git, not from tenant-controlled configuration.
`reconcile.yaml.spec.serviceAccountName: portal-reconciler` is the identity used
to apply the tenant entrypoint. It must be confined to reviewed tenant
release/config objects and unable to mutate platform policy, RBAC, service
accounts, enrollment sources/reconcilers or privileged namespaces.

The **tenant-owned** HelmRelease sets
`spec.serviceAccountName: portal-deployer`, target `tenant-example-portal`, and
separate `storageNamespace: tenant-example-portal-release`. That deployer needs
only reviewed workload permissions plus its isolated Helm storage permissions.
`portal-runtime` is a separate unprivileged runtime identity. Kubernetes RBAC
alone cannot constrain arbitrary HelmRelease fields: admission/protected
enrollment must enforce allowed identities, namespaces, sources, secret refs and
storage. Missing identities, credentials or dependencies must fail closed;
no broad fallback grants are supplied here. These names are contracts, not
created identities or verified enforcement.

Tenant Git contains app configuration/chart definitions, no platform or Big Bang
internals. Application inputs do not grant permissions. Preserve portal image,
secret-mount, runtime and release-storage admission boundaries; keep tenants from
editing enrollment/impersonation settings. Retain one Flux owner per release and
never run Fleet against the same portal release during an eventual transfer.

## Verified feature pin and remaining gates

`source.yaml` pins `perkforge/perkforge-tenant-portal` at
`28cac682f12253de7f10d7b3634a6a957733bbb4`. Its existing chart is
`bundles/portal/chart`, name `household-portal`, version `0.1.0`, and defaults to
`enabled: false`. No chart, generated application YAML, image digest, token or
client-secret value is copied here. The chart accepts separately provisioned
secret/account names and emits only a Deployment and ClusterIP Service when
correctly configured and enabled.

That feature-branch commit adds the tenant-owned `gitops/portal` entrypoint in
[portal PR #5](https://github.com/perkforge/perkforge-tenant-portal/pull/5).
It references the existing chart, supplies disabled application values and a
suspended scoped HelmRelease. It is a review dependency, not a merged/live
activation. No chart or child application manifest is copied into platform Git.
Both enrollment resources remain suspended. Namespace/policy/RBAC foundation, read credentials,
registry/OIDC secret references, image approval and live tests are also missing.
The separate parent/bootstrap remains disabled. The application source repository
`perkforge-portal` remains unchanged.

## Separate enrollment repository: initialization pending

The user-created **platform-owned `perkforge-platform-tenants` repository** is
the intended separate enrollment boundary, following the [official Flux multi-tenancy pattern](https://github.com/fluxcd/flux2-multi-tenancy).
A platform parent would reconcile a named-cluster entrypoint that explicitly
lists small tenant-enrollment folders, then each child reconciles its tenant's
external app repository under the scoped identity above. Platform ownership of
that parent Git is essential: it creates reconcilers, so an untrusted tenant
must not control its source, identity or child-enrollment manifests.

Use explicit reviewed enrollment lists, not automatic discovery of every
repository or directory. No custom generator, Argo clone or Flux Operator
ResourceSet is needed. The
enrollment repository currently has no default branch/initial commit; user
initialization is pending before any feature branch or PR can be created. No
main write is made to initialize it. Keep the pinned Big Bang Flux lifecycle
unchanged. The illustrative enrollment stays here while that repository base is
pending;
its feature-branch implementation will use this same explicit selection model.
