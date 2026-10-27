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

1. `enrollments/home.yaml` is the Fleet options file for this enrollment. It loads
   `values.yaml`, `tenants.yaml`, then `tenants/home.yaml`: shared component defaults,
   existing cluster metadata, and platform-owned tenant overrides, in that order.
2. `values.yaml` defines the reusable foundation switches. `tenants/home.yaml` supplies
   `foundation.lifecycle`, namespaces/allocations, workspace and pinned repositories.
   Home opts out of Project creation because its existing legacy bundle owns that Project.
3. `templates/{project,namespaces,quotas,limits,network-policies,service-accounts,
   deployment-rbac,fleet-access,registration}.yaml` are shared across tenants. They have
   no portal names, OIDC configuration or image settings. `_foundation.yaml` checks
   inputs; each component has one clearly named template and switch.
4. `applications.portal` in Home's values holds only the application-specific contract.
   `templates/applications/` adds portal admission restrictions and validates its identity,
   approved image and runtime inputs. A tenant without that entry gets only the baseline.

For another tenant, add a tenant values file and a small enrollment options file pointing
at those values; reuse the same templates. At activation a platform GitRepo path entry
selects this directory with `options: enrollments/home.yaml`. Do not add a root auto-discovered
`fleet.yaml` that accidentally enrolls all tenants. Fleet GitRepo targets do not supply
Helm value overrides. No registration of this new path is included in the current draft.

`foundation.components` enables each shared component by default. A platform-owned opt-out
must have a matching `foundation.optOutReasons` explanation identifying the alternative
owner or reviewed exception. It is not a tenant self-service escape hatch or proof that
an alternative exists. For an already managed component, switching it off is a removal
and requires separate decommission/ownership-transfer review. Opting out of namespace,
identity or security creation is safe only when the required resources/controls already
have another approved owner. The synthetic `tests/fixtures/tenant-demo.yaml` exercises
all shared components without portal inputs; it is test data, not an enrolled tenant.

`.fleetignore` excludes tenant data, shared values and obsolete preview locations from
raw-resource packaging. Fleet reads the explicitly referenced values files first.
There is no `Chart.yaml`, `tpl`, external chart dependency, hook or live lookup here.
The YAML uses normal Helm expressions inside Fleet's native `templates/` directory;
plain YAML elsewhere does not automatically consume values. This does not introduce
a chart/library for the operator to maintain.

Fleet v0.16's [renderer](https://github.com/rancher/fleet/blob/v0.16.2/internal/helmdeployer/render/helm.go)
handles `templates/*.yaml` and supplies its internal chart. Its
[values loader](https://github.com/rancher/fleet/blob/v0.16.2/internal/bundlereader/resources.go)
loads target-customization values files without an authored chart. This is why
`valuesFiles` is explicitly under the local target, rather than the top-level Helm
block (whose values-file loading in this version is conditional on chart/repo settings).
There is one target for this Home bundle; target customizations are cluster selectors,
not a loop that creates multiple tenants on the same cluster.

## Lifecycle and ownership

| State | Platform output | Tenant GitRepo |
|---|---|---|
| `disabled` | Nothing; no allocation | Absent |
| `active` | Selected shared foundation and application-specific controls | Exact revision, unpaused |
| `paused` | Same identities and enabled configuration | Exact revision, paused |

Active/paused require an approved image digest and explicit
`foundation.namespaces.<name>.allocation`. No allocation is included in the current
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

The CI transition check rejects removing an active/paused entry, namespace, repository
or enabled component, or changing it back to disabled, comparing the exact Git base. Budget checks include existing Home allocations
plus portal. These are review gates, not cluster admission or an inferred live inventory;
branch protection is not configured by this draft. Bypassing review can still prune
resources. Decommission requires a separate explicit plan. Native Fleet `keepResources`
addresses bundle removal, not omission of resources during an update. Never use a false
switch or `doNotDeploy` as a preservation strategy for an existing deployment.

## Identity and security boundary

The downstream tenant repository supplies ordinary application values: origin,
issuer/client/audience, existing Secret and service-account names, plus its image pin.
It knows nothing about platform template layout, values transport, workspace routing
or platform labels. There is no platform-values ConfigMap, `valuesFrom`, or deployer
ConfigMap access. Fleet's platform-owned GitRepo sets the target namespace and deployer;
a platform-owned workspace mapping selects bundles inside that restricted workspace,
with a policy limiting repository URL and deployment identity.

The platform separately declares the expected runtime contract in `applications.portal`
and admission checks the actual workload. Repeating these few ordinary inputs is
intentional: the app can be rendered independently; platform policy does not trust its
values. Candidate-pair tests render the pinned tenant's own values and evaluate its
objects against platform CEL. A mismatch fails instead of silently overriding the app.
Secret references are necessary application inputs, not permission grants; no Secret is
created. The tenant repository revision is in `foundation.repositories.portal.revision`.

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
An unapproved portal image prevents active/paused rendering. The generic baseline does
not impose this app-specific allowlist on other apps: restricted Pod Security and RBAC
alone do not stop arbitrary Secret mounts. Each new application needs its own reviewed
runtime/Secret isolation before it can receive sensitive credentials.

The approved app can read its own limited OIDC client secret. Compromised tenant code
is not trusted for privileged APIs: future operations need independent server-side
authorization outside tenant-editable configuration. GitLab remains disabled. No GitLab
or Keycloak administrative capability is granted.

## Offline checks, without deployment

Use the checksum-pinned Fleet v0.16.2 CLI from `.github/workflows/portal-contract.yml`:

```sh
KUBECONFIG=/dev/null fleet test -f enrollments/home.yaml -N local local-lab/tenant-config
```

The default result is empty. Fleet's `test` command is deprecated but retained in this
pinned version; it exercises the actual bundle reader, target merge and Helm renderer
locally. It does not connect to Kubernetes. Do not substitute `fleet target` (which
reads live clusters) or a deploy command. The production path is Fleet consuming Git,
not running this test command or Python.

Python is used only for tests/evidence for the new portal. Tests create temporary
active/paused copies with a synthetic digest/allocation, invoke the real Fleet CLI,
prove a second tenant and every component opt-out, verify values precedence/excluded files,
preserve the original portal admission expressions and exercise
lifecycle/budget regressions. The unchanged legacy foundation still has its own check.

```sh
python3 local-lab/scripts/render-tenant-foundation.py --check
python3 -m unittest discover -s local-lab/tests -v
python3 local-lab/tests/validate_portal_schemas.py
(cd local-lab/tests/portal-cel && GOMAXPROCS=1 GOMEMLIMIT=256MiB go test -p=1 -count=1 ./...)
```

Install the pinned Python test requirements and Go1.27.3. Set `FLEET` to a custom Fleet
binary path if needed. For real tenant-chart comparison, check out the exact tenant SHA
in the Home values, set `PORTAL_CHART_DIR` to its `bundles/portal/chart`, and supply Helm3.19 (`HELM`
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

**Fleet Helm release-storage permissions remain blocked.** Inspection of installed
v0.16.2 found that cleanup reads deployment identity from the serialized release.
A Secret envelope allowlist is insufficient to authenticate that payload; no Secret
write grants are added. See [the storage assessment](PORTAL-RELEASE-STORAGE.md) for
source evidence, the offline counterexample, alternatives and the preloaded image.
This remains offline configuration, not a successful live portal integration.
