# Portal release storage: activation remains blocked

The proposed Secret create/update/delete grant is **withheld**. Portal remains disabled,
with no Secret permissions in its deployer Role. A name/type/label allowlist would protect
ordinary credential Secret names, but is not enough to protect the deployment identity
stored inside Helm history. This is a source-derived trust-boundary finding, not a
claim that an exploit has been run or that the existing cluster was compromised.

## Installed implementation

Read-only inspection found Fleet agent v0.16.2 (source commit
14b1cd93eea8772b3abcf1b3786c254233ac149a). Offline CLI/schema checks now match that
version; Kubernetes CEL/schema checks remain on the installed 1.36.5 API generation.

- [deployer.go](https://github.com/rancher/fleet/blob/v0.16.2/internal/helmdeployer/deployer.go):
  getCfg builds the write client using the chosen service account's impersonation.
  createCfg always selects the Helm Secret driver; setting HELM_DRIVER is not a solution.
- [helmcache/secret.go](https://github.com/rancher/fleet/blob/v0.16.2/internal/helmdeployer/helmcache/secret.go):
  Get/List use the agent's cache, while Create/Update/Delete use that write client.
  Thus storage does not justify giving the tenant deployer Secret get/list/watch.
- [Helm 4.2.2 secrets.go](https://github.com/helm/helm/blob/v4.2.2/pkg/storage/driver/secrets.go):
  storage uses Get/List/Create/Update/Delete and release records of type helm.sh/release.v1.
  Its payload contains the serialized chart, annotations and manifests.
- [delete.go](https://github.com/rancher/fleet/blob/v0.16.2/internal/helmdeployer/delete.go):
  deleteByRelease and delete read fleet.cattle.io/service-account from stored chart
  annotations, then call getCfg with that identity. The stored payload is therefore
  authorization-relevant, not just an opaque revision counter.
- [list.go](https://github.com/rancher/fleet/blob/v0.16.2/internal/helmdeployer/list.go):
  bundle/agent association and keepResources are also read from stored chart annotations.
  Keeping resources is not a general integrity guarantee for tenant-writable history.

A tenant-controlled release record can retain its allowed name, namespace, type and
labels while changing its compressed payload. Checking oldObject on update/delete is
necessary for envelope integrity but cannot authenticate that payload. Kubernetes CEL
has no general gzip/Helm-release decoder. The currently proposed policy matches the
restricted deployer identity; it must not be assumed to constrain a different identity
selected later from history. Granting namespace-wide write verbs without solving this
would weaken the intended boundary, even with Secret reads denied.

`test_portal_release_storage.py` demonstrates indistinguishable envelopes with distinct
synthetic stored identities and asserts that desired RBAC still grants no Secret access.
This is an offline counterexample, not an executed Fleet lifecycle exploit. Existing
native CEL cases continue rejecting deployer Secret writes. No live write/dry-run,
credential access, impersonation probe or controller operation was performed.

## Choices requiring review

1. **Preferred: fix/verify the upstream trust boundary.** Fleet must select cleanup
   identities from trusted platform-owned deployment state, and keep release storage
   writes under a distinct trusted identity, or authenticate and validate stored release
   content before using it for authorization. Test install, upgrade, rollback, drift,
   uninstall and orphan cleanup before proposing narrower tenant permissions. A version
   upgrade alone is not evidence of a fix. No upstream issue or patch is submitted here.
2. **Platform-owned deployment for the initial portal.** Treat its exact reviewed chart
   and values as platform-trusted input, using a separate platform deployment identity.
   This changes the ownership model and requires explicit approval; do not simply remove
   serviceAccount and fall back to the cluster-admin Fleet agent. General tenant-writable
   charts must not inherit that authority. The current PR does not implement this option.
3. **Dedicated validating release-storage service/webhook.** Decode and validate the
   payload against trusted state, including historical identities/manifests and bounded
   decompression. This introduces a new security-critical component and substantial
   maintenance; it is not the simple initial solution and is not implemented here.

Until a choice is approved and validated, do not grant even create/update/delete to the
portal deployer. RBAC cannot scope create by resource name, and labels are not a security
boundary. The existing Nextcloud deployer has broader Secret permissions; it is unchanged
and is not a model for portal permissions. Its separate security review remains necessary.

## Namespace creation correction

Fleet 0.16.2 Policy supports allowNamespaceCreation. With requireServiceAccount true and
allowNamespaceCreation omitted/false, the controller sets CreateNamespace false on the
BundleDeployment. Read-only inspection confirmed this for the existing Nextcloud bundles.
The portal policy already has those defaults. Do not add namespace-create authority or
invent a GitRepo field. This is version-specific behavior, now covered by pinned schemas;
it is not a portal live integration pass.

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
