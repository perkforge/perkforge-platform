# Home portal: Fleet-native platform configuration

Portal is a household application under Home, not another tenant or a platform-admin
exception. Its new configuration uses Fleet-native YAML templates and values directly.
There is no Python generation step, authored Helm chart/library, pre-rendered manifest
source, or custom deployment wrapper. The existing legacy tenant foundation is unchanged;
its later Python cleanup is a separate effort.

Portal is **disabled**. Its bundle path is not selected by the current platform GitRepo.
Merging this draft neither deploys portal controls nor changes the 16 existing foundation
files. No image, Keycloak client, Secret, role grant or live policy has been created.

## Read the configuration in this order

All paths below are under `local-lab/tenant-config/`:

1. `fleet.yaml` selects the local cluster and loads `values.yaml`, `tenants.yaml`, then
   `tenants/home.yaml`. Shared portal defaults come first, existing cluster metadata
   second, and explicit Home overrides last. Other tenants are not loaded for this bundle.
2. `tenants/home.yaml` owns `applications.portal`: lifecycle, namespace, origin,
   issuer/client/audience, Secret reference and immutable tenant source revision.
   Home group paths and resource defaults are already in that same file; the Kubernetes
   Pod Security version comes from the selected cluster in `tenants.yaml`.
3. `templates/portal-namespace.yaml` declares the portal namespace, quota and limits
   under Home's existing Project. `portal-controls.yaml` declares the platform-owned
   service accounts, restricted deployer RBAC, network policies and Fleet workspace.
4. `templates/portal-registration.yaml` supplies the tenant GitRepo and immutable
   identity-values ConfigMap. `_portal-values.yaml` holds the shared values definition.
5. `templates/portal-admission.yaml` and `_portal-workload-validations.yaml` declare the
   admission controls once for controller templates and Pods. `_portal-contract.yaml`
   contains short fail-closed input checks, including lifecycle, approved image and scope.

`.fleetignore` excludes tenant data, shared values and obsolete preview locations from
raw-resource packaging. Fleet reads the explicitly referenced values files first.
There is no `Chart.yaml`, `tpl`, external chart dependency, hook or live lookup here.
The YAML uses normal Helm expressions inside Fleet's native `templates/` directory;
plain YAML elsewhere does not automatically consume values. This does not introduce
a chart/library for the operator to maintain.

Fleet v0.16's [renderer](https://github.com/rancher/fleet/blob/v0.16.0/internal/helmdeployer/render/helm.go)
handles `templates/*.yaml` and supplies its internal chart. Its
[values loader](https://github.com/rancher/fleet/blob/v0.16.0/internal/bundlereader/resources.go)
loads target-customization values files without an authored chart. This is why
`valuesFiles` is explicitly under the local target, rather than the top-level Helm
block (whose values-file loading in this version is conditional on chart/repo settings).
There is one target for this Home bundle; target customizations are cluster selectors,
not a loop that creates multiple tenants on the same cluster.

## Lifecycle and ownership

| State | Platform output | Tenant GitRepo |
|---|---|---|
| `disabled` | Nothing; no allocation | Absent |
| `active` | Namespace, quota, identity/configuration and all security controls | Exact revision, unpaused |
| `paused` | Same identities and enabled configuration | Exact revision, paused |

Active/paused require an approved image digest and explicit
`applications.portal.resources.allocation`. No allocation is included in the current
Home record. Defaults stay disabled. Paused stops application Git reconciliation;
it does not scale down pods, remove controls or delete data. Platform controls can
still receive reviewed updates while application reconciliation is paused.

The native portal bundle exclusively owns its new namespace/quota. Do not also add
that namespace to Home's legacy `environments` list: rendering rejects duplicate
ownership. It references the existing Home Project without taking ownership of it.
Before activation, review aggregate Home allocations and the Project's actual budget.
The current Project has no reserved portal capacity. Changing that existing quota owner
or migrating its legacy renderer is separate reviewed work, not a prerequisite for
merging this disabled configuration.

The CI transition check rejects removing an active/paused entry or changing it back
to disabled, comparing the exact Git base. Budget checks include existing Home allocations
plus portal. These are review gates, not cluster admission or an inferred live inventory;
branch protection is not configured by this draft. Bypassing review can still prune
resources. Decommission requires a separate explicit plan. Native Fleet `keepResources`
addresses bundle removal, not omission of resources during an update. Never use a false
switch or `doNotDeploy` as a preservation strategy for an existing deployment.

## Identity and security boundary

The platform ConfigMap `tenant-home-portal/portal-platform-values` contains non-secret
Helm values. The existing tenant repository uses `helm.valuesFrom` to read its
`values.yaml` key. The deployer has only named ConfigMap get access. The tenant chart
sets the exact issuer/client/audience/origin and references `portal-oidc/client-secret`;
no Secret is generated. The approved companion remains pinned to
`ecafe09a497e971a4a4af04a331d837e4e1a146a`.

Keycloak provisioning remains a separate approval gate: trusted HTTPS realm issuer,
confidential authorization-code client with PKCE S256 and exact `/auth/callback`,
separate API audience, short-lived access tokens, full-path existing Home groups and
API `tenant-reader` role claims. Disable implicit/password/service-account flows and
broad scope; approve the role scope and individual membership separately. No automatic
client creation, role assignment, admin credential or executable realm import is supplied.
The former generated identity-plan/preview artifacts have been removed.

Values precedence is not security. Native admission validates actual Deployment and
ReplicaSet templates and final Pods, including ephemeral-container updates. It constrains
image, exact seven env entries, issuer/client/audience, Secret reference, service account,
container count, security settings, ports and probes. It denies command/args/lifecycle,
envFrom, init/sidecar/ephemeral containers, mounts, other secrets, host/interactive access
and custom DNS. Service exposure stays ClusterIP. The deployer may mutate only the
reviewed workload/service surface in the exact namespace, not security resources or
scale/exec/token subresources. Namespace matching does not trust tenant-editable labels.
An unapproved image prevents active/paused rendering rather than producing deployable output.

The approved app can read its own limited OIDC client secret. Compromised tenant code
is not trusted for privileged APIs: future operations need independent server-side
authorization outside tenant-editable configuration. GitLab remains disabled. No GitLab
or Keycloak administrative capability is granted.

## Offline checks, without deployment

Use the checksum-pinned Fleet v0.16.0 CLI from `.github/workflows/portal-contract.yml`:

```sh
KUBECONFIG=/dev/null fleet test -N local local-lab/tenant-config
```

The default result is empty. Fleet's `test` command is deprecated but retained in this
pinned version; it exercises the actual bundle reader, target merge and Helm renderer
locally. It does not connect to Kubernetes. Do not substitute `fleet target` (which
reads live clusters) or a deploy command. The production path is Fleet consuming Git,
not running this test command or Python.

Python is used only for tests/evidence for the new portal. Tests create temporary
active/paused copies with a synthetic digest/allocation, invoke the real Fleet CLI,
verify defaults/overrides and excluded data files, compare existing controls and exercise
lifecycle/budget regressions. The unchanged legacy foundation still has its own check.

```sh
python3 local-lab/scripts/render-tenant-foundation.py --check
python3 -m unittest discover -s local-lab/tests -v
python3 local-lab/tests/validate_portal_schemas.py
(cd local-lab/tests/portal-cel && GOMAXPROCS=1 GOMEMLIMIT=256MiB go test -p=1 -count=1 ./...)
```

Install the pinned Python test requirements and Go1.27.3. Set `FLEET` to a custom Fleet
binary path if needed. For real tenant-chart comparison, check out the exact tenant SHA
above, set `PORTAL_CHART_DIR` to its `bundles/portal/chart`, and supply Helm3.19 (`HELM`
can override the path). CI does this automatically. Tests do not require main merges.
The native CEL suite exercises Kubernetes1.36.5 libraries; schemas target Kubernetes1.36.5
and Fleet0.16. Rancher FleetWorkspace schema, live defaulting/admission ordering,
controller identities and CNI enforcement remain unverified.

## Remaining activation gates

Keep the bundle outside the platform GitRepo's selected paths until activation is
explicitly approved. Resolve capacity/Home Project allocation, approve and scan a real
image, verify installed API versions, configure trusted HTTPS Keycloak and secure
client-secret delivery, approve exact internal TLS ingress/identity egress (current
network policies allow DNS only), and verify admission/CNI after mutating webhooks.
Install and verify controls before supplying secrets or allowing workloads.

**Fleet Helm release-Secret storage remains unresolved.** Fleet uses the configured
deployment identity for values lookup and Helm operations. No broad Secret permissions
were added to make installation succeed. Resolve and verify least-privilege release
storage/impersonation before activating the child tenant GitRepo. This draft is tested
offline configuration, not a claim of successful live integration.
