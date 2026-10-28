# Big Bang evaluation proposal

Documentation and a disabled bootstrap example; see the
[architecture proposal](../docs/BIGBANG-FLUX-PROPOSAL.md). This new effort leaves
`local-lab/` intact. It reuses reviewed concepts, not a wholesale copy or migration.
A disabled bootstrap example is supplied, not an approved installer or deployable profile.
Do not apply these files to the current tiny VMs. A separate folder does not
separate runtime resources: the target cluster and every controller/CRD/release
owner remain undecided. A later approved test needs an explicit target and budget.

## The entrypoint, file by file

These are **authored inputs**, not generated child manifests. Ansible and Flux
consume the actual files below; the former descriptive `selection.yaml.example`
files and all committed `rendered/` YAML have been removed. Charts and authored
values are the source of truth. Build/render output belongs under `/tmp` for
validation and diff review, never in the deployment source tree.

```text
ansible-playbook -i examples/ansible/inventory.yaml examples/ansible/bootstrap.yaml --limit local
  inventory host local: gitops_path = ./local-lab-big-bang/examples/clusters/local
  → template seed.yaml.j2 into GitRepository/cluster-config + Kustomization/cluster-root
  → cluster-root.spec.path selects examples/clusters/local
  → clusters/local/kustomization.yaml composes shared/app/provider/profile/cluster inputs
  → HelmRelease/bigbang references GitRepository/bigbang-chart and valuesFrom
  → pinned Big Bang chart creates component sources and HelmReleases
```

The command above is a **local no-write walkthrough**, run from
`local-lab-big-bang/`. With the checked-in inventory, it prints the selected path
and skips every Kubernetes/Git task. It does not install or deploy anything.

| Authored file | Role and consumed fields |
| --- | --- |
| [inventory.yaml](examples/ansible/inventory.yaml) | `local`, `dev`, and `dev-secondary` are Ansible inventory aliases. `deployment_environment` and `impact_profile` record context. `gitops_path` selects configuration; kubeconfig/context/expected UID select the target API, independently. Target and configuration commit remain unconfigured |
| [bootstrap.yaml](examples/ansible/bootstrap.yaml) | Standard Ansible tasks: report selection; when separately enabled, validate target UID, obtain Big Bang release tag and verify its observed commit, apply its `base/flux`, wait for required CRDs/controllers, then apply only the paused seed |
| [seed.yaml.j2](examples/ansible/seed.yaml.j2) | Standard Ansible template: config repository + exact `ref.commit` in GitRepository; `spec.sourceRef` and `spec.path` in root Flux Kustomization |
| [local kustomization.yaml](examples/clusters/local/kustomization.yaml), [dev](examples/clusters/dev/kustomization.yaml), [dev-secondary](examples/clusters/dev-secondary/kustomization.yaml) | Local Kustomize build inputs; choose reusable directories and generate that cluster's values ConfigMap |
| [bigbang/source.yaml](examples/bigbang/source.yaml) | Pinned chart source, Big Bang release tag `3.35.1`; no vendored chart or generated child YAML |
| [bigbang/release.yaml](examples/bigbang/release.yaml) | Outer HelmRelease: `chart.spec.chart: ./chart`, sourceRef, and explicit ordered valuesFrom |
| [Generic enrollment source](examples/enrollments/base/source.yaml), [local parent](examples/enrollments/local/reconcile.yaml), [dev parent](examples/enrollments/dev/reconcile.yaml) | Only the platform-owned enrollment repository URL/revision, selected cluster path and declared environment/profile context; no individual tenant definitions |
| [OpenBao app folder](examples/apps/openbao/values.yaml) | Focused repository/package/chart values, consumed through its ConfigMap and outer valuesFrom; no standalone competing release |
| [shared](examples/shared/values.yaml), [provider](examples/providers/rke2/values.yaml), [impact](examples/profiles/il2/values.yaml), [local](examples/clusters/local/values.yaml), [dev](examples/clusters/dev/values.yaml) | Non-secret authored values. Native configMapGenerator packages each values.yaml; fixed ConfigMap names match the release references |

Inventory selection chooses **where Ansible connects** and **which Git path it
seeds**. The root GitRepository URL/revision chooses the protected configuration
snapshot. The root Flux Kustomization path chooses a directory within that
snapshot. Local `kustomization.yaml` is a build recipe, not a controller CR.
The separate Big Bang GitRepository selects the chart source, not cluster config.

The selected context is explicit and checked across repositories:

| Cluster identity | Environment | Profile | App profile example |
| --- | --- | --- | --- |
| local | local | il2 | shared + local + il2 + local overrides |
| dev | dev | il2 | shared + dev + il2 + dev overrides |
| dev-secondary | dev | il5 | shared + dev + il5 + dev-secondary overrides |

`profiles/il2` remains reusable; `profiles/il5` is an **unassessed illustrative
target**, retaining only the same local UI guardrails. Neither file is a DoD
control baseline or authorization. The user's dev hardware target remains the
physical homelab; no hardware or live API target is assigned to the il5 example.
Cluster identity, environment, profile, distribution and hosting remain separate.
RKE2 on AWS is possible; AWS does not imply EKS.

The inventory fields `deployment_environment` and `impact_profile` appear on
the paused Ansible seed as `example.perkforge.io/{cluster,environment,profile}`
annotations. The platform cluster root declares the same context and selects
its reusable profile. Its generic Flux parent selects the same named cluster
in enrollment Git; enrollment records that context and selects the matching
app cluster root. The app root explicitly composes its environment and reusable
profile. No values magically flow between repositories: references and context
must agree. These annotations are inspectable selection evidence, not trusted
security labels or authorization.

Cross-repository tests follow exact pins and compare actual context, selected
paths and inputs. They reject mismatched environment/profile, wrong cluster
path, wrong source/revision, and a seed that does not preserve the inventory
selection. App profiles contain only a real application input (illustrative
identity audience); platform security controls remain platform/enrollment-owned.
No fake tenant policy profiles or privileged platform values are injected into
app Git. App claims cannot relax platform RBAC/admission/network boundaries.

The same environment can serve many uniquely named cluster roots, with explicit
profile choice and small overrides. There is no nested environment/IL/tenant
folder matrix and no mandatory hosting or distribution layer in app Git.

The chart GitRepository uses **`spec.ref.tag: 3.35.1`**, not a moving branch.
The Ansible prerequisite checkout uses the same `bigbang_tag`. This annotated
tag was verified to resolve to commit
`02efc8b0d259ee0cd2c31ea857d50a4021cf6d8e`; Ansible's gated bootstrap also checks
that resolution against `bigbang_expected_commit` before any Flux apply.
A release tag is human-readable but is not intrinsically immutable: a Flux tag
reference alone does not enforce the recorded commit. Review tag resolution
and rendered changes on future updates; no release upgrade is made here. The
configuration repository's separate `config_commit` remains a precise future
snapshot of PerkForge inputs, not the Big Bang release selection.

Later values win: **chart defaults → values-shared → values-openbao →
values-provider → values-impact → values-cluster**. The five references are explicit in
`bigbang/release.yaml`; each ConfigMap has a `values.yaml` key. The OpenBao
reference is optional, so omitting its folder omits the package rather than
leaving a missing required ConfigMap. The generic enrollment
repository reference is separate from these Big Bang values. Secrets are not
included. Future secret inputs need disjoint key paths and separately reviewed
provisioning. No inline `spec.values` silently adds another override layer.

To add a cluster, copy only the small named-cluster directory, edit its
`values.yaml` and the reusable provider/profile directories selected in its local
`kustomization.yaml`, then add an inventory alias with the matching `gitops_path`.
Shared chart pins/release wiring stay in one place. `il2` labels an illustrative
profile, not DoD requirements or authorization. Provider and impact are independent
axes. There is no inheritance chain or custom generator.

Keep **environment, impact level, tenant identity, provider and cluster name**
independent. Support both shared clusters with namespace-scoped tenants and
dedicated tenant clusters. A cluster can be organized around an environment/IL
and host several tenants, or belong to one tenant with its own environment/IL
selection. A dedicated cluster does not automatically grant its tenant platform
administration or establish an authorization boundary.

The named cluster's local Kustomization selects shared/provider/profile inputs
and a generic enrollment-repository reference. Tenant foundation/enrollment
definitions live in that separate platform-owned repository. Tenant model
and membership are explicit platform-owned choices, not inferred from folder
names or the IL label. The current named-cluster examples do not yet implement
or assign either tenancy model; that remains a review gate, not a hidden default.

Use an environment-specific shared values input only when multiple clusters
actually benefit from it. Select it explicitly in the named cluster build and
add an optional `values-environment` reference between provider and impact in the
outer release. Otherwise keep the few environment settings in cluster values;
there is no mandatory new folder or layer. General order is defaults → shared/app defaults →
provider → environment (if selected) → impact → cluster. The minimal example
omits the environment input, so its existing five references remain exact.
Avoid trees such as provider/environment/IL/tenant/cluster and automatic cross-products.

Before live use, validate the selected environment/profile/tenant model together:
allowed combinations, cluster ownership and tenant membership, namespace bindings,
source/deployer identities, secret boundaries and admission/network enforcement.
Reject silent profile weakening or unintended tenant enrollment. Reuse reviewed
foundation controls for shared and dedicated models with explicit exceptions;
do not duplicate the entire platform per combination or treat dedication as a
replacement for RBAC, quotas, policies and recovery tests.

After final merge, validate profile invariants independently of precedence.
The illustrative guardrails reject default Headlamp cluster-admin binding and
shared-SA authentication; a negative late-override check must fail. Real profiles
need approved requirements and explicit reviewed exceptions (cluster, rule,
justification, owner, expiry and evidence). Tenant writers must not control
platform-package/profile input. These two checks are not a complete IL policy.

## Generic enrollment boundary and explicit selection

The bootstrap is tenant-agnostic. Each cluster root includes its
`../../enrollments/<cluster>` component. That component
contains only a shared GitRepository URL/revision and a Flux parent selecting
`./clusters/<cluster>` in `perkforge-platform-tenants`. The
parent's `tenant-enrollment-admin` identity is a generic platform-owned contract,
not a provisioned grant. No individual tenant name, chart or identity appears
in these bootstrap examples.

Individual tenant selection lives only in the enrollment repository's cluster
roots. That repository owns platform-controlled tenant namespace/RBAC,
NetworkPolicy/quota and enrollment definitions, using reusable foundations and
per-tenant opt-in/overrides as reviewed. The current companion PR demonstrates
paused enrollment only; it does not implement those unfinished controls. Tenant
app repositories own application resources/values under scoped identities, with
no Big Bang internals. Explicit lists replace automatic discovery; no generator
or second Flux lifecycle is added.

Platform addons remain separate. Both platform roots currently include
`../../apps/openbao`; omit that line to omit the addon, with optional valuesFrom
preventing a missing-input error. A future c2-only OpenBao service can be selected
only there; remote consumer credentials/TLS/network/recovery design is not
implemented. Removing the generic enrollment component omits all tenant enrollment
from a platform root; individual tenant opt-out belongs to the enrollment repo.
Shared definitions are not automatic installations on every cluster.

## Review-stage references and merge order

Companion PRs: [tenant app #5](https://github.com/perkforge/perkforge-tenant-portal/pull/5),
[platform-owned enrollment #1](https://github.com/perkforge/perkforge-platform-tenants/pull/1),
and [this platform proposal #47](https://github.com/perkforge/perkforge-platform/pull/47).
The authored source here pins exact enrollment feature commit
`c9a3e51ca0fb713457c4b435a9aae41cf2b511c2` for cross-repository review. It is
not a production/adopted revision, and none of these references track a moving
feature branch automatically.

Human merge order: app PR first; update/revalidate the enrollment PR's app pin
to its approved merged commit, then merge enrollment; update/revalidate this
PR's enrollment pin to that approved merged commit, then merge the platform
proposal. Squash/rebase can change SHAs. Re-run exact-pin checks after each
advance. Nothing automatically unsuspends after merge; foundation/security,
capacity/credentials and live activation remain separately reviewed gates.

## Why this example cannot deploy the platform

`bootstrap_apply: false` skips every remote/Git action. The inventory has no real
kubeconfig, context, cluster UID or configuration commit. Both seed CRs and the
outer chart source/HelmRelease have `suspend: true`; no automatic unpause or
approval bypass is supplied. `prune: false` gives the root no deletion authority.
No secrets are created: `cluster-config-read`, registry pull access and the
`platform-reconciler` identities are future reviewed prerequisites, not fabricated
credentials or RBAC. The preflight checks reject placeholders and multiple hosts.

Even if a future operator explicitly enabled the bootstrap block, it would seed
pinned Flux prerequisites and paused root objects only. It would not install
Keycloak/OpenBao/Headlamp/portal or wait for their readiness. The example does not
supply hardened controller settings, application-ready policies, PKI or budgets;
those remain review gates. Do not enable it on the current tiny VMs. No live
portion was run. Flux self-management/ownership handoff is a later reviewed step;
ordinary Ansible reruns must not compete with that future owner.

## Portability without provider or impact-level coupling

RKE2 is the first target; EKS is a possible later target, not a tested deployment.
Keep shared apps and their value contracts free of Fleet resources, Rancher IDs,
RKE2-specific storage/ingress names, host paths and provider annotations. Supply
those through reviewed provider prerequisites and named-cluster values. A provider
folder describes substrate capability, while an impact profile expresses reviewed
security requirements; neither selects the other or grants authorization.

For EKS, decide API access/identity separately from workload IAM. [External OIDC
user authentication](https://docs.aws.amazon.com/eks/latest/userguide/authenticate-oidc-identity-provider.html)
has its own issuer/client/group trust; an EKS cluster's workload identity issuer
is not automatically the Keycloak human-login integration. Recheck the Headlamp
user-token path and group RBAC, alongside platform operator access. Review EKS
network policy enforcement, API endpoint reachability, load-balancer/DNS/TLS
behavior, and [CSI/storage dependencies](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html),
including IAM, availability-zone topology and recovery. Do not copy local-path
or Canal assumptions into EKS or mix cloud credentials into shared/IL values.
No AWS resources or provider dependencies are installed by this PR.

A later portability check must render each provider/cluster combination, inspect
provider-specific resources and duplicate owners, then prove reconciliation,
identity/tenant denials, networking, storage and recovery on the approved target.
Preserve the same evidence contracts across targets. Big Bang's curated patterns
and release artifacts can support RMF/cATO evidence collection; they do not
confer compliance, an authorization or a deploy-anywhere guarantee.

## Candidate evaluation scope and dependencies

Candidate initial scope: **Headlamp, Keycloak, OpenBao, and the existing portal**.
That is four applications, not four Pods or zero dependencies. Start from all
unneeded Big Bang defaults disabled, including Istio, observability, policy-engine
stacks, Vault and metrics-server auto-install. Add only reviewed prerequisites.
Existing tenant security concepts still require enforcement; disabling a default
policy stack does not authorize a policy-free cluster.

| Component | Required inventory before live approval |
| --- | --- |
| Flux | Four pinned controllers, source/Helm/Kustomize/notification CRDs, platform identities, source auth, registry access; one lifecycle owner |
| Headlamp + pinned Flux plugin | User-token/API OIDC trust, namespace RBAC, UI service account, plugin distribution, ingress/TLS, API/DNS access; disable default cluster-admin binding and unsafe shared-SA mode |
| Keycloak | Exact package/chart/image pins, database ownership/version/PVC/backup, bootstrap administrator, TLS/issuer/client/audience/group mapping and revocation tests; reuse established concepts, not existing credentials |
| OpenBao | Exact official chart/image, persistent backend/PVC, TLS, unseal/recovery custody, scoped auth/policies, backup/restore; ESO controller/CRDs only if selected for delivery; injector remains disabled unless justified |
| Portal | Existing pinned private image/chart, namespace runtime/deployer identities, admission/release-storage boundary, pull credential and OIDC client secret references, API dependencies, ingress/TLS; tenant input stays outside privileged package values |
| Substrate and shared services | RKE2/CNI/DNS, ingress controller, CSI/storage classes, PKI/cert renewal, any database operator and CRDs, admission/network policy, explicit DNS/API/identity/database/secrets/ingress flows |

Render every enabled child chart, hooks and bootstrap resources with actual
selected versions and ordered inputs before live approval. Inventory CRDs,
cluster roles/webhooks, controllers, Jobs, PVCs, database and network dependencies.
Total per-node requests/limits, PVC allocation, image storage, startup/upgrade
surge and one-node-loss reserve; missing resource requests are unresolved budget
items, not zero-cost workloads. No full four-app render or resource budget exists
yet. Neither the current VMs nor the future M920q nodes are approved targets by
this PR. Preserve the existing household Nextcloud and stable portal.

## Platform-owned OpenBao extra package

OpenBao's small authored configuration lives in
[`examples/apps/openbao/values.yaml`](examples/apps/openbao/values.yaml).
It contains only its `helmRepositories` entry and `packages.openbao` settings,
including the official chart reference and chart values. The sibling
[`kustomization.yaml`](examples/apps/openbao/kustomization.yaml) packages it as
`ConfigMap/values-openbao`; each named-cluster root selects that folder, and the
outer release explicitly consumes it immediately after shared defaults.
Provider, impact and cluster inputs can still override its values in that order.

This adds one small values file and native composition entry rather than a long
combined shared file. It deliberately does **not** add authored standalone
HelmRepository/HelmRelease objects: Big Bang generates those from these inputs
and remains their single lifecycle owner. Do not add a second OpenBao release.
The `helmRepositories` key is a Helm list, so a later override replaces the whole
list; additional app folders must not independently define that same list and
silently erase each other's repository entries. Review any future aggregation
explicitly rather than introducing a merge wrapper.

Big Bang 3.35.1's catalog offers Vault, not OpenBao. OpenBao is preferred for
this evaluation in line with the user's licensing concern; confirm the selected
software/image licenses separately rather than assuming interchangeability.
The pinned [official extra-package guide](https://repo1.dso.mil/big-bang/bigbang/-/blob/3.35.1/docs/installation/environments/extra-package-deployment.md)
and [custom HelmRelease template](https://repo1.dso.mil/big-bang/bigbang/-/blob/3.35.1/chart/templates/package/helmrelease.yaml)
support `packages.openbao`, `sourceType: helmRepo`, `helmRepo.repoName/chartName/tag`
and `values`. The specimen uses the official public Helm repository and chart
0.30.6, with `addons.vault.enabled: false`. Its already-cached archive SHA256 is
`76e90c2315a4922b4b0c6c63fd8a00b9f4bdf0cffda160664f8ea5762d59911c`.

`wrapper.enabled: false` is supported; wrapper is optional. Also set
`bbCommonValues: false` and `passBigBangValues: false` for the unmodified official
chart, rather than feeding Big Bang-specific integration values into it.
Big Bang’s existing NetworkPolicy and optional mesh/security integrations are
valuable starting points: inspect and reuse suitable generated controls before
writing duplicates. Their defaults still need target-specific flow review, as
the proposal’s separate policy-enabled Headlamp render demonstrates.
No wrapper means no automatic mesh/SSO/network/monitoring integration: platform
owners must supply reviewed policies and identity/secrets configuration.

The package HelmRelease and HelmRepository are both in `bigbang`; its target
namespace is `openbao`. This avoids a cross-namespace source reference when
lockdown is enabled. Platform deployment authority still needs review.
The public repository's empty `existingSecret` satisfies this release's schema
without emitting `secretRef`; no credentials are supplied. Exact syntax passed
the pinned schema and was rendered. Big Bang still emits an unused wrapper
GitRepository for custom packages even with the package wrapper disabled; there
is no wrapper HelmRelease in the output. Review/eliminate unnecessary source
fetches in the eventual implementation without global remote-source workarounds.

Do not place tenant-maintained configuration in privileged `packages.*.values`:
the release uses Helm templating (`tpl`) on custom package values and controls
privileged resources. Tenant application sources and configuration retain scoped
deployer identities and admission boundaries outside this platform-owned input.

## Local assembly and validation evidence

From repository root, using already available tools; no cluster contact:

```sh
ANSIBLE_LOCAL_TEMP=/tmp/perkforge-ansible ANSIBLE_REMOTE_TEMP=/tmp/perkforge-remote \
  ansible-playbook -i local-lab-big-bang/examples/ansible/inventory.yaml \
  local-lab-big-bang/examples/ansible/bootstrap.yaml --syntax-check
kubectl kustomize local-lab-big-bang/examples/clusters/local > /tmp/bigbang-local-seed.yaml
kubectl kustomize local-lab-big-bang/examples/clusters/dev > /tmp/bigbang-dev-seed.yaml
helm lint /tmp/perkforge-bigbang-3.35.1/chart --kube-version 1.36.5 \
  -f local-lab-big-bang/examples/shared/values.yaml \
  -f local-lab-big-bang/examples/apps/openbao/values.yaml \
  -f local-lab-big-bang/examples/providers/rke2/values.yaml \
  -f local-lab-big-bang/examples/profiles/il2/values.yaml \
  -f local-lab-big-bang/examples/clusters/local/values.yaml
# helm template with the same ordered -f inputs writes only /tmp output.
# Repeat for dev; review per-cluster before/after diffs locally.
```

All three local Kustomize assemblies and Ansible syntax passed. The separate
`gitops-selection-offline` CI follows only the exact public review pins and runs
four tests, including real Ansible template rendering and deliberate environment,
profile, target-path and revision mismatches. These are test fixtures, not
bootstrap discovery or Python configuration generation. To run locally:

```sh
ENROLLMENT_CHECKOUT=/path/to/perkforge-platform-tenants \
TENANT_APP_CHECKOUT=/path/to/perkforge-tenant-portal \
  python3 -m unittest discover -s local-lab-big-bang/tests -v
```

Checkouts must be at the exact pinned commits. No live API calls occur.
 The default playbook
walkthrough selected local with `changed=0`, skipping all live tasks. Standard
Ansible templating was checked locally with synthetic inputs. Local checks traced
seed path → cluster build → chart source and all five ConfigMap references, then
used their actual valuesFrom order for Helm lint/render. Pinned Flux CRD field
contracts were inspected locally; this is not full server schema/CEL/admission
validation. All generated output stayed in temporary files.

Moving OpenBao inputs into the app folder preserved the original clusters’ outer and
child output in local comparisons, with one generated OpenBao repository/release.
Pinned Headlamp 0.45.0-bb.1 and official OpenBao 0.30.6 child charts were rendered
for validation only, using the outer chart's generated values. Headlamp replicas
were 1/2 with no ClusterRoleBindings; wait Job and OpenBao injector were disabled.
OpenBao still rendered a 10 GiB PVC template and unbudgeted server resources.
Its default TLS/backend is not an approved secured service. Companion
repo checks cover their paused entrypoints and disabled app renders; individual
tenant/app details stay in those repositories. No full
Keycloak or four-app integration/resource budget has been assembled or validated.
Do not publish temporary output containing real credentials.

Before any live action: choose target and owners; complete pins/full renders,
per-workload capacity budgets, controller hardening and source/API identity;
review network/admission, TLS, OIDC/RBAC, bootstrap secrets and recovery; obtain
explicit action-specific approval. Live source/release readiness, tenant denials,
revocation, storage, resource use and recovery remain untested. Existing
`local-lab/`, Nextcloud data and the stable portal are untouched.
