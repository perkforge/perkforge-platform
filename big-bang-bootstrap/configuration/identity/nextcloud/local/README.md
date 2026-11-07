# LOCAL Nextcloud issuer egress

The LOCAL Nextcloud integration selects `network.yaml` through
`clusters/local-nextcloud`, inherited by the metrics pilot roots. The existing
platform root reconciles it as `flux-system/platform-reconciler`. App/enrollment
identities receive no network authority. Other environment and Portal roots do
not select it. This network selection changes no image or immutable input.

The policy preserves the existing `tenant-home-nextcloud/nextcloud-oidc-issuer`
object: exact app labels, `192.168.1.102/32`, TCP443, and no additional egress.
This is the verified shared-ingress endpoint, not a hostname-level boundary:
other virtual hosts at that IP remain reachable at L3/L4. Same-Pod cron shares
this egress. DNS/database rules and default deny remain unchanged.

## Owner-admin adoption prerequisites

`access.yaml` is deliberately absent from all Kustomizations. It records the
approved owner-admin Role/RoleBinding, not authority for Flux to manage its own
permissions. For a new cluster or restoration, obtain explicit approval before
applying exactly this Role/RoleBinding in `tenant-home-nextcloud`: only
`flux-system/platform-reconciler`, only `nextcloud-oidc-issuer`, only get/patch/update.
No create/delete/list/watch, other policy, credential, or tenant authority is granted.
Do not switch the root to a broad identity or include access.yaml in its resources.

Read-only named access and server-side patch adopt the existing object in place.
Before separately approved promotion, verify the existing object and field ownership,
unchanged selector/destination/port, no competing Flux owner, and record its UID.
Then verify root readiness/inventory and the same UID/spec after adoption. Unexpected
ownership conflicts require review, never force replacement. The object disables
Flux force and prune; root prune also remains false, and the Role has no
delete permission. Removing it from source does not silently remove the live rule.

If the object is absent or deleted, reconciliation fails: the Role cannot
create it. The existing default-deny policy then blocks this issuer path unless
another independently allowed rule permits it. Do not claim global isolation from
that failure alone. Restoration requires separate operator approval; do not widen
RBAC to make it recreate automatically. Kubernetes cannot constrain create by
resourceNames. This intentional adoption-only contract preserves least privilege.

The enrollment repository's `tenants/nextcloud/sso/prepare.yaml` and
`boundary.yaml.j2` remain offline review fixtures. Do not apply their policy over
this selected source after adoption: this integration is the authoritative policy
lifecycle. Existing public-CA and Secret delivery remain separate operator-owned
immutable inputs. No certificate/credential contents belong in this directory.

For withdrawal, first disable provider/client under separate approval, remove the
selection in Git, then explicitly approve removal of this policy and unused access
prerequisite. Preserve local recovery, DNS, database access and other tenants.
Publishing or merging this source does not authorize adoption, RBAC application,
rollout, user grants or SSO activation. Offline tests do not prove live authorization
or actual network enforcement; repeat positive/negative probes after adoption.

## Accepted release and runtime-policy access

The accepted LOCAL source is platform **v0.26.0**, commit
`076f38651ae747d31a8269e0e6acfcca412e3047`, selecting
`./big-bang-bootstrap/clusters/local-metrics-limited-pilot-ui`. The explicit
[Ansible selection](../../../ansible/vars/local-nextcloud-selection.yaml) records
these public inputs for the existing bootstrap procedure. It is not automatically
loaded and does not change other cluster defaults. Keep kubeconfig, context,
cluster UID and verified release evidence as separately validated operator inputs.
Do not replay `bootstrap.yaml` on the running installation to record this pin:
its seed deliberately pauses source/root. Existing source promotion changes only
the reviewed GitRepository tag after the normal release/cluster checks, preserving
root path, identity, force=false, prune=false and the approved suspension state.
No second GitRepository, child controller or self-reconciling seed is introduced.

`runtime-policy-access.yaml` records the separately approved ClusterRole and
ClusterRoleBinding for the same `flux-system/platform-reconciler`. Its only grant
is get/patch/update on the existing `nextcloud-app-pod-templates`
ValidatingAdmissionPolicy. It grants no policy binding, create/delete/list/watch,
Secret or RBAC authority. Like `access.yaml`, it stays outside every Kustomization;
authorized owner-admin application is the existing bootstrap route, not Flux
self-escalation. On a fresh/recovery installation, review both files and apply
only the approved named prerequisites before promoting the source. Verify exact
rules, subjects and roleRefs afterward; do not broaden rights when an object is
missing. The approved live application already completed; do not reapply merely
because this cleanup PR is merged.

The runtime policy and its Deny binding remain owned by the enrollment
repository's `tenants/nextcloud/foundation/runtime-policy.yaml`, released at
**v1.5.0**, commit `5bbe571fb70532ab3f071bdb8b66bddbea2da3f8`.
That foundation is an operator-applied prerequisite, not selected by the running
enrollment root. The new grant does not create a second policy owner or add an
automatic policy reconciler. Its reviewed policy accepts the digest-pinned GHCR
images, exact Docker Hub rollback image and read-only OIDC mounts. Use that source,
not a copied policy in platform Git, for future explicitly approved updates.

Read-only checks on 2026-11-07 found all 43 released foundation SA/RBAC/admission/
binding/NetworkPolicy objects present. Authored non-metadata fields matched,
except removed blank lines in three runtime CEL expressions (same expressions).
The source tag and unchanged root settings above matched live state. This is
configuration evidence, not fresh network, login, recovery or denial acceptance.
CI gates remain intentionally paused; this source capture does not restore them.
