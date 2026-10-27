# Portal Fleet release storage

Portal remains disabled and unselected. This draft supplies the missing Helm history
permissions using Fleet's documented tenancy model; it does not apply live RBAC.

## Reviewable permission change

The generic deployment Role supports an explicit `helmReleaseStorage` opt-in per
repository. Home portal opts in to Secret **create, update, delete** in
`tenant-home-portal`, alongside its existing Deployment/Service permissions.
No Secret get/list/watch/patch, namespace creation, RBAC modification, or impersonation
permission is added. Other tenant Roles and legacy outputs remain unchanged.

Portal's separate fail-closed `portal-deployer-surface` admission checks the exact
request identity, namespace, resource/subresource and operation. Secret envelopes must
have the exact home-portal revision name, matching positive version, Helm owner/name
labels and release type, known Helm status, and only a nonempty release data key.
Owner references and finalizers are rejected. CREATE checks the new object; UPDATE
checks old and new objects; DELETE checks the old object. OIDC and other nonrelease
Secrets remain denied, including attempts to convert them into release records.
Platform operators remain responsible for protected credentials; this rule scopes the
deployer and does not prevent a platform administrator from managing those credentials.

RBAC cannot limit Secret create by name. Install and verify admission before granting
the Role; never activate the grant on its own. Existing policies, runtime image/env/SA
constraints and network restrictions remain in place. No deployed controls change on merge.

## Documented model and pinned implementation

[Fleet Tenant Setup](https://fleet.rancher.io/how-tos-for-operators/tenant-setup)
describes operator-owned bootstrap, workspace Policy and a downstream deployment SA
in the agent namespace, bound to Roles in workload namespaces. Its example includes
broad Secret permissions and asks operators to adapt them. Our narrower storage verbs
are derived from installed Fleet v0.16.2, not an official minimum-permissions recipe.

- [Policy](https://fleet.rancher.io/reference/ref-policy): requireServiceAccount and
  an allow-list pin initial deployments to the approved account. Tenants cannot write
  Policy or BundleDeployment resources. Namespace creation stays disabled.
- [v0.16.2 storage client](https://github.com/rancher/fleet/blob/v0.16.2/internal/helmdeployer/helmcache/secret.go):
  Get/List use the agent cache; Create/Update/Delete use the impersonated deployment client.
- [v0.16.2 deployer](https://github.com/rancher/fleet/blob/v0.16.2/internal/helmdeployer/deployer.go):
  selects Helm Secret storage. HELM_DRIVER is not a supported workaround here.

## Conditional cleanup concern and evidence limits

[Cleanup source](https://github.com/rancher/fleet/blob/v0.16.2/internal/helmdeployer/delete.go)
reads identity from serialized Helm history. Synthetic offline fixtures demonstrate
that two identical allowed envelopes can contain different compressed identities.
Envelope admission does **not** authenticate this payload. Neither these tests nor
source inspection demonstrate a successful live privilege escalation in our setup.
The exact reviewed repository pin also prevents an arbitrary unreviewed commit from
entering the current desired deployment.

Fleet documents multi-tenant isolation, including independent teams. Do not dismiss a
possible boundary failure as inherently unsupported, or label this conditional finding
an established exploit. Follow the documented operating model, verify normal operation,
and retain this concern for separately authorized investigation. No custom storage
service or upstream redesign is an activation prerequisite established by this evidence.

Offline tests cover release permission scope, valid history lifecycle statuses and
negative old/new object mutations using Kubernetes 1.36 CEL against Fleet 0.16.2 output.
They do not exercise live API defaulting, webhook ordering, Helm operations or cleanup.
After explicit approval, verify install, upgrade, rollback and cleanup, plus Policy
and cross-namespace RBAC denial. Retain expected/actual results and exact versions.

## Local image already prepared

Merged app source: 5efe468755a8c40bee799e03e8cc4980ce44755c.
Node24 amd64 base: docker.io/library/node@sha256:2dd9a4f758e173b65fee15388f7706af6fb01ef50cf7a2c0538711d67a6981ae.
Preloaded image: ghcr.io/perkforge/perkforge-portal@sha256:3826fbae9f6102c8bf69176d8307866b382ff624c7d99f1ea0653ecdfa3a831a.
OCI archive checksum: 33dca8a5c38028ed33d0389e48e61e36e39411c9366a5184fbc9155c3f9905fa.

The rootless Podman 5.4.2 build used disk-backed temporary storage, one CPU and 1 GiB.
Both RKE2 nodes resolved that exact manifest through containerd and CRI. Network-isolated
smoke checks passed under UID 1000/read-only/no-capabilities settings. This was a preload,
not a registry push or deployment; the image is not GC-pinned. Private workstation build
logs/archive remain outside Git. Recheck availability before later activation. Catalog
imageDigest stays null, tenant values stay disabled, and no deployment pin changes here.
