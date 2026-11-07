# LOCAL Nextcloud issuer egress

The LOCAL Nextcloud integration selects `network.yaml` through
`clusters/local-nextcloud`, inherited by the metrics pilot roots. The existing
platform root reconciles it as `flux-system/platform-reconciler`. App/enrollment
identities receive no network authority. Other environment and Portal roots do
not select it. No image, release pin, admission or immutable input changes occur.

The policy preserves the existing `tenant-home-nextcloud/nextcloud-oidc-issuer`
object: exact app labels, `192.168.1.102/32`, TCP443, and no additional egress.
This is the verified shared-ingress endpoint, not a hostname-level boundary:
other virtual hosts at that IP remain reachable at L3/L4. Same-Pod cron shares
this egress. DNS/database rules and default deny remain unchanged.

## Separately approved adoption prerequisite

`access.yaml` is deliberately absent from all Kustomizations. It is an explicit
owner-admin proposal, not automatically applied by this selection. Neither
existing Flux identity currently has permission to reconcile this policy.
Before promoting a release containing this selection, obtain action-time approval
for exactly this Role/RoleBinding in `tenant-home-nextcloud`: only
`flux-system/platform-reconciler`, only `nextcloud-oidc-issuer`, only get/patch/update.
No create/delete/list/watch, other policy, credential, or tenant authority is granted.
Do not switch the root to a broad identity or include access.yaml in its resources.

Read-only named access and server-side patch adopt the existing object in place.
Before separately approved promotion, verify the existing object and field ownership,
unchanged selector/destination/port, no competing Flux owner, and record its UID.
Then verify root readiness/inventory and the same UID/spec after adoption. Unexpected
ownership conflicts require review, never force replacement. The object disables
Flux force and prune; root prune also remains false, and the proposed Role has no
delete permission. Removing it from source does not silently remove the live rule.

If the object is absent or deleted, reconciliation fails: the proposed Role cannot
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
