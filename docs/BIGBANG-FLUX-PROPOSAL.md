# Big Bang reuse and Flux proposal

Status: proposed for human review; issue [#46](https://github.com/perkforge/perkforge-platform/issues/46).
Research date: 2026-10-28. This document approves no adoption or migration.

## Recommendation

Keep the working Fleet/Rancher path while completing the layout decisions in
[#14](https://github.com/perkforge/perkforge-platform/issues/14) and
[#20](https://github.com/perkforge/perkforge-platform/issues/20). Reuse Big Bang's
package integration knowledge, pinned release discipline, values conventions,
and upgrade guidance as design inputs. This means retaining the current system
while investigating, not starting a partial migration. A separately reviewed
standalone package chart could later be reused through Fleet, but this proposal
does not select or install one. Do not install the Big Bang umbrella, Flux, or
any default packages into the current Fleet environment.

If deeper Big Bang adoption proves useful, prefer **one Flux GitOps system per
cluster** over permanent Big Bang plus Fleet layering. Evaluate it first in a
separately approved disposable environment with a tenant UI, explicit RBAC, and
the existing security tests. Retain Rancher as a management UI if useful; its
presence need not make Fleet authoritative for workloads. Controller replacement
and object ownership transfer require their own reviewed plan.

| Choice | Benefit | Cost and fit |
| --- | --- | --- |
| Current Fleet + selective package reuse | Existing Rancher UI, scoped workspaces, native values files, established local evidence; smallest change | We own integration and upgrade testing. A Big Bang package may depend on bb-common, mesh, policy or registry conventions; it is not automatically a standalone upstream chart |
| Big Bang + Fleet | Preserves Fleet entry point while Flux deploys curated packages | Fleet may own only the outer Big Bang Helm release/CRs; Flux owns child releases. Two status, drift, prune and recovery paths. Never let both manage the same release, CRD or workload. Technically plausible, not locally integrated or recommended as the steady state |
| One Flux system + tenant UI | Native Big Bang model; one reconciliation vocabulary and shared values API | New onboarding, tenant controller permissions, UI authentication and upgrade ownership. Reproduce current boundary evidence before replacing Fleet. Best conditional direction if Big Bang benefits outweigh the transition |

## What was verified

**Documentation/source verified:** Big Bang **3.35.1**, commit
`02efc8b0d259ee0cd2c31ea857d50a4021cf6d8e`, was inspected locally. The authored
chart source and Ansible prerequisite checkout now select release tag `3.35.1`;
the bootstrap verifies its resolution against that observed commit. A tag is not
intrinsically immutable, and the Flux tag reference alone does not enforce the
recorded commit. This is a
research pin, not a declaration of the newest or adopted release. Its
[Chart.yaml](https://repo1.dso.mil/big-bang/bigbang/-/blob/3.35.1/chart/Chart.yaml)
requires Kubernetes `>=1.34.0-0`; the repository's RKE2 `1.36.5` satisfies that
chart constraint. That does not verify RHEL/SELinux, Canal, ingress, storage,
package images or the complete RKE2 integration.

The [bootstrap](https://repo1.dso.mil/big-bang/bigbang/-/tree/3.35.1/base)
installs the Big Bang chart as a Flux HelmRelease. That chart produces package
sources, HelmReleases and values Secrets, rather than rendering all child
workloads directly. The pinned `base/flux/gotk-components.yaml` identifies Flux
**v2.9.5**. Its `kustomization.yaml` substitutes Iron Bank controller images:

| Controller | Image tag | Bootstrap request |
| --- | --- | --- |
| helm | v1.6.4 | 900m CPU, 1 GiB |
| kustomize | v1.9.5 | 300m CPU, 600 MiB |
| notification | v1.9.4 | 100m CPU, 200 MiB |
| source | v1.9.5 | 300m CPU, 384 MiB |

Total: **1.6 CPU and 2208 MiB per cluster**, from source settings, not measured
usage. Limits total 3.2 CPU and 4448 MiB. Two clusters repeat these controller
costs. [install_flux.sh](https://repo1.dso.mil/big-bang/bigbang/-/blob/3.35.1/scripts/install_flux.sh)
applies these local manifests, optionally creates `private-registry`, and waits
for four controllers. It was read, never executed. Registry access is a separate
prerequisite; no credentials were acquired or tested.

Choose exactly one lifecycle owner for Flux controllers and CRDs. If separately
managed Flux is selected, verify compatibility with this Big Bang release's
APIs and upgrades; do not run its bootstrap installer over another owner's
controllers. Avoid choosing a different lifecycle owner solely to obtain a UI.

## Small values files, explicit precedence

### Bootstrap: how the first reconciliation starts

The user's previous `run.sh` pattern fits the native design: apply a small seed,
then let controllers follow Git. There are two different objects called
Kustomization. Local `kustomization.yaml`
(`kustomize.config.k8s.io/v1beta1`) tells Kustomize how to build YAML; it has no
reconciliation loop. A Flux `Kustomization`
(`kustomize.toolkit.fluxcd.io/v1`) is a cluster custom resource instructing a
controller to fetch a source artifact, build a path and reconcile it repeatedly.
`GitRepository` is another CR, watched by source-controller. Neither works until
its CRD and controller exist.

Proposed sequence for a future approved clean-cluster evaluation:

1. **Ansible prepares the substrate.** Provision RHEL/RKE2, networking, DNS,
   storage prerequisites and the reviewed Kubernetes API authentication. Establish
   an attended bootstrap administrator path independent of in-cluster Keycloak,
   OpenBao or Headlamp. Their own installation must not depend on their already
   being available. Confirm the intended cluster identity before any write.
2. **Seed only the prerequisites for pulling desired state.** Create the reviewed
   namespaces, registry pull access and source authentication/decryption material
   through the separately approved secret procedure. A GitRepository's
   `secretRef` resolves in its own namespace. Separate registry image-pull access
   from Git read access. Use per-cluster, least-privilege credentials; do not make
   steady-state Git read access depend on a write-capable bootstrap token. ESO
   cannot deliver the credentials required to install/authenticate ESO itself.
3. **Install pinned Flux CRDs and controllers.** Use the exact selected
   release's `base/flux`, with the reviewed tenancy settings and platform
   identities, and wait for CRDs Established and controllers Available. This is
   the chicken-and-egg seed; a Flux CR cannot install the controller needed to
   interpret that same CR on an empty cluster. The research pin is 3.35.1 as
   recorded above. Do not substitute moving upstream manifests.
4. **Apply the root source and Flux Kustomization.** Select an already published
   platform configuration tag and verify its recorded source resolution and
   named-cluster context before any gated apply. Bootstrap does not select a
   future self-tag; release publication and live activation remain separate. The source points to the
   protected environment repository and the root selects only
   a named `clusters/<cluster>` path. It references the source and an explicit
   platform deployer identity. Source Ready must precede successful path
   reconciliation. Local Kustomize composition produces the root objects; the
   Flux Kustomization then performs recurring reconciliation. The two clusters
   receive separate roots and secrets, not a root that writes both clusters.
5. **Reconcile Big Bang and then its children.** The cluster root applies the
   `bigbang` namespace, ordered values ConfigMaps/Secrets, pinned Big Bang
   GitRepository and Big Bang HelmRelease. Helm-controller installs that chart;
   its rendered child GitRepositories/HelmReleases fetch the pinned packages and
   install their charts. Model prerequisite stages with Flux `dependsOn` plus
   explicit health checks/`wait`, and child release dependencies where needed.
   YAML order alone is not a readiness barrier; an outer chart installing CRs
   does not mean the child applications are healthy. Required milestones are
   source artifact → root apply → outer release → child releases → workloads →
   functional/security checks. Headlamp comes after API identity/RBAC, ingress
   and TLS; it is not required to bootstrap the cluster.
6. **Hand controller ownership to Git explicitly.** The pinned Big Bang
   [self-management workflow](https://repo1.dso.mil/big-bang/bigbang/-/blob/3.35.1/docs/concepts/git-ops-workflow.md)
   allows a `flux-components` Flux Kustomization to reconcile the same controller
   manifests after seeding. Align its source pin with Big Bang. Review field
   ownership, existing apply managers and pruning before handoff; the bootstrap
   tool then stops applying controller manifests during ordinary runs. Keep
   either this Flux self-management path or another deliberately chosen lifecycle
   owner, never both. The small Ansible run is not an additional reconciler.

Prefer a **small, readable Ansible bootstrap playbook**, as requested, rather
than translating the old shell script line for line. It matches the existing
host workflow: validate inputs, use native manifest application, check bounded
readiness and report the first failed stage. A thin `run.sh` can remain a
convenient entrypoint invoking that playbook with a named inventory. A shell-only
seed is also viable if it does little more than build/apply the reviewed seed
and wait. Avoid duplicate bootstrap implementations, custom value generation,
background retry loops or an imperative script deploying every child chart.
These are proposed responsibilities, not a supplied runnable installer.

For recovery/re-runs, stable names and identical reviewed inputs allow declarative
apply and Flux reconciliation to resume after partial failure. Idempotence is
not permission to overwrite drift or ignore failed hooks. Check the failed
layer's conditions first; preserve existing secrets and release/data ownership,
reject a different cluster/pin/owner and do not delete/reinstall or rotate secrets
automatically. A broken controller may require the documented break-glass
administrator to reapply its last reviewed pinned seed; a working controller
normally recovers through a reviewed Git correction. Pruning, CRD removal,
namespace deletion and stateful Helm rollback need explicit recovery decisions.
Protect Nextcloud volumes and test restores separately. No bootstrap or recovery
step described here has been run against a cluster.

This walkthrough is source-verified against the pinned Big Bang
[first deployment guide](https://repo1.dso.mil/big-bang/bigbang/-/blob/3.35.1/docs/getting-started/first-deployment.md)
and bootstrap manifests, with Flux's
[bootstrap](https://fluxcd.io/flux/installation/bootstrap/generic-git-server/) and
[Kustomization dependencies](https://fluxcd.io/flux/components/kustomize/kustomizations/#dependencies)
as references. The disabled example demonstrates root manifest wiring; secret bootstrap,
recovery and a usable implementation still need review and live validation. Flux's `bootstrap git` is a
separate alternative that can also push repository files; it is not an extra
step to run on top of this seed or authorization to write repository credentials.
The supported Flux CLI offers a cohesive install-and-self-management workflow
and reduces hand-maintained seed wiring, but its selected controller version,
rendered manifests and repository-write behavior must be reviewed. Big Bang’s
pinned path gives exact alignment with the researched release and Iron Bank
images. For this investigation, favor Ansible coordinating that pinned path;
choose CLI bootstrap instead only if its generated result and single lifecycle
owner meet the same compatibility and security requirements.

### Values contract

The pinned [configuration guide](https://repo1.dso.mil/big-bang/bigbang/-/blob/3.35.1/docs/configuration/index.md)
and [base HelmRelease](https://repo1.dso.mil/big-bang/bigbang/-/blob/3.35.1/base/helmrelease.yaml)
show the outer sequence: chart defaults → optional Terraform Secret → common
Secret → common ConfigMap → environment Secret → environment ConfigMap.
Later values win. Ordinary Flux inline `spec.values` wins over `valuesFrom`;
avoid it here so the documented file order remains the entire override contract.
Keep sensitive and non-sensitive key paths disjoint: a later ConfigMap must not
silently override a credential. Maps merge; lists are replacement inputs, not
automatic append operations.

There is a second values boundary. Big Bang's child releases consume `common`,
then generated `defaults`, then user `overlays` keys from their package values
Secret. The package chart may then use `upstream` passthrough for the original
application chart. A top-level Helm render verifies the Flux resources and
values payload, not the resulting child deployments. Avoid deep post-render
patches; prefer documented package values, and upstream values only when needed.

Proposed evaluation layout is a separate `local-lab-big-bang/` folder in this
repository. Existing `local-lab/` stays intact. Bring forward reviewed concepts
from identity, tenancy, secrets and portal work; do not copy the old lab wholesale.
The folder contains documentation and a disabled authored bootstrap example. It is
not runtime isolation: target cluster, namespaces, CRD/controller ownership and
resource capacity must be selected explicitly before a live evaluation.

```text
local-lab/                       # existing effort, unchanged
local-lab-big-bang/              # new evaluation boundary
  ansible/                      # future small bootstrap, distinct inventory
  shared/{releases,values}/      # future pinned platform-owned definitions
  providers/{rke2,eks,...}/     # provider prerequisites; no impact-level meaning
  profiles/{il2,...}/        # reusable reviewed profiles, no inheritance chain
  clusters/<cluster-name>/       # explicit profile selection + shallow overrides
  examples/                     # this PR: disabled Ansible + native Flux/Kustomize inputs
```

Prefer `profiles/<name>` selected by `clusters/<cluster-name>` over duplicating
`cluster-name/il2` trees. Cluster name and impact profile are independent axes;
cluster-specific secrets, addresses and capacity never belong in an IL profile.
`profiles/il2` is retained. The only examples are local/local/il2 (local VMs)
and dev/dev/il2 (future physical cluster), written as cluster/environment/profile.
Future profiles such as il5 require reviewed requirements and explicit selections
in each repository; no executable il5 profile or target is supplied. Neither the
il2 label nor these UI guardrails constitutes an IL baseline or authorization.
Cluster identity, environment, profile, distribution and hosting stay independent.

The inventory, platform Flux parent, enrollment and app roots explicitly record
`example.perkforge.io/{cluster,environment,profile}` context. Tests follow exact
published tag resolutions and compare those claims with the actual selected paths/profile
inputs. A profile does not automatically propagate across Git repositories.
The app composes shared → environment → app profile → cluster values; its example
profile only changes the supported identity-audience input. That is not DoD
policy, permission or approval of the example identity registration. App context
cannot override platform-owned security controls. Mismatched environment/profile,
cluster path or revision fails the offline contract tests, including actual
Ansible seed rendering. Context annotations are evidence, not live enforcement.

The values order is chart defaults → shared/app defaults → provider values → selected profile → named
cluster overrides. Match that order in local Helm commands and live valuesFrom;
keep secrets on separate, disjoint key paths.

Keep environment and impact-level selection separate from tenant identity,
provider and cluster name. Preserve both shared clusters with namespace-scoped
tenants and dedicated tenant clusters, including clusters organized around an
environment/IL. Each named cluster explicitly selects applicable shared,
provider, optional reusable environment, impact-profile and cluster values, plus
a generic reference to the separate platform-owned enrollment repository.
Individual tenant foundations/enrollments are selected inside that repository,
not by this bootstrap. If environment values
are shared, their precedence is between provider and impact; otherwise the
minimal example keeps those settings in cluster values with no extra layer.
Validate allowed combinations, cluster/tenant ownership, scoped identities,
namespace/secret boundaries and final policy invariants. Neither example assigns
a tenant model yet; no automatic overlay cross-product or dedicated-cluster
security exemption is implied. See the evaluation README for the selection rule.

RKE2 is the current target, not an application dependency. A future EKS provider
must supply its own API identity/OIDC trust, IAM/workload identity, CSI/storage
classes, CNI/network policy, load balancers/DNS/TLS and credentials. Keep Fleet
CRs, Rancher project IDs, RKE2 ingress/storage names, node paths and provider
annotations outside the portable application layer. Provider selection and
impact-profile selection are independent; EKS does not imply an IL profile, and
a profile cannot supply AWS prerequisites or authorization. The neutral values
contract and pinned native Flux/Helm application definitions are a portability
strategy, not proof that an untested target works. See the new effort README
for provider-specific validation gates. Big Bang can contribute useful control
implementation patterns and upgrade evidence to RMF/cATO work; neither its
adoption nor any cluster/provider/profile inherits an authorization.

A profile cannot enforce itself by merge order. After the final merge, validation
must reject weakened invariants and unexpected enabled packages. The specimen
uses illustrative UI constraints (no default cluster-admin binding and no shared
service-account authentication), not alleged IL2 controls. Check both effective
values and rendered resources. A deliberate exception needs a separate reviewed
record naming cluster, rule, reason, owner, expiry and verification; never make
a late override a silent exception. Test that an intentionally weakening cluster
file is rejected. Production validators must also inspect admission, networks,
identity, secrets and cluster ownership, rather than treating these two checks
as a complete impact-level policy.

Each cluster root enumerates resources explicitly and contains only simple
composition plus its values files. No environment inheritance chain or remote
Kustomize bases. Pin Big Bang's base and its GitRepository to the same release;
keep the bootstrap vendor code pinned locally if lockdown denies remote bases.
Use native Kustomize generators to package common and cluster values into
ConfigMaps, and ordered Flux `valuesFrom` to combine them. A few repeated lines
are preferable to a custom generator or hidden merge framework. Fleet can use
the same principle today: existing `tenant-config/enrollments/home.yaml` loads
`values.yaml`, `tenants.yaml`, then `tenants/home.yaml` explicitly.

Ansible owns host/bootstrap and application configuration through APIs. Python
is reserved for tests and evidence, not configuration generation. GitOps owns
cluster manifests; Ansible must not continually overwrite GitOps-owned objects.

### Concrete named-cluster specimens

The [new evaluation README](../local-lab-big-bang/README.md) links shared,
provider/profile and named-cluster values, consumed Ansible inventory selection,
root source/Kustomization, local cluster builds and outer Big Bang release wiring.
Charts and authored values are the source of truth. Generated manifests are not
checked in; temporary local rendering is validation evidence only. The named
cluster roots explicitly select the illustrative il2 profile. Cluster
overrides retain the one/two-replica UI
precedence example. These are **not deployment profiles**: target, four-app
integration, identity, admission/network policy, TLS, resource sizing and secret
delivery are incomplete. The seed and outer release are suspended, bootstrap
writes default off, and no real cluster inputs or credentials are supplied.

OpenBao's repository, chart pin and values are now grouped in the small
`examples/apps/openbao/` folder. Its native ConfigMap generator and explicit
outer `valuesFrom` entry keep the files traceable; Big Bang generates the
HelmRepository and HelmRelease and remains their single owner. No chart,
generated workload YAML or competing standalone release is copied into the repo.
The seed template is unchanged.

The specimen renders Headlamp plus a platform-owned OpenBao extra package and
references a separate platform-owned enrollment repository through a generic
cluster-specific Flux parent. The bootstrap knows that repository URL/revision
and cluster path only; individual tenant names, source repositories, charts and
identities belong to enrollment/app repositories. Tenant foundation definitions
(namespace/RBAC, NetworkPolicy/quota and registration) remain platform-owned in
the enrollment repository, with reusable reviewed foundations and per-tenant
opt-in. The current companions are paused examples, not finished live controls.
Neither addon definitions nor tenant definitions automatically install everywhere.
The README explains the separate opt-in boundaries and future c2-only addon case.
Remote consumers and complete four-app integration remain unimplemented.
Unneeded Big Bang packages (including mesh, monitoring, Vault, and metrics-server
`auto`) are explicitly disabled. OpenBao injector and Headlamp wait Job are also
disabled. Network policy disabled in this render specimen does not propose
weakening any platform policy. A deployable profile must supply its reviewed
replacement and all required flows.

**Locally rendered:** Big Bang 3.35.1 and all four selected app charts now have
an explicit render-only capacity candidate, including Keycloak's pinned database,
the actual Flux bootstrap and all child hooks. See the concise
[local preflight](../local-lab-big-bang/preflight/README.md) for pins, requests,
limits, PVCs, missing inputs and the measured local comparison. The unchanged
base specimen still leaves Keycloak disabled; only the preflight opt-in enables
its offline render. The candidate does not fit the current VM CPU request budget,
and is not an approved sizing/security profile or a live deployment validation.

For a future approved implementation, local checks should render the bootstrap,
outer chart and every enabled pinned child chart; validate schema and policies,
compare before/after rendered output per cluster, detect duplicate object owners,
and total requests/PVCs. Save tool versions, input pins and redacted diffs as PR
artifacts. Never upload rendered real credentials. Run synthetic policy tests
locally; reserve API admission dry-runs and reconciliation for separately
authorized live validation. `helm template` cannot prove CRD admission, hooks,
storage provisioning, OIDC, networking or recovery.

The user-initialized `perkforge-platform-tenants` repository now has a companion
[enrollment PR #1](https://github.com/perkforge/perkforge-platform-tenants/pull/1),
consistent with the [official Flux multi-tenancy example](https://github.com/fluxcd/flux2-multi-tenancy).
A protected platform parent creates reviewed child sources/reconcilers; children
act as scoped tenant identities. The parent Git and identity/ref fields stay
outside tenant control. Use explicit cluster enrollment lists, not automatic
repository discovery. The platform example contains no tenant-specific folder.
Its exact enrollment pin is review-stage and unmerged: merge the tenant app
companion first, advance/revalidate enrollment to the approved app commit and
merge it, then advance/revalidate this platform reference to the approved
enrollment commit. No main writes or merges are performed here. All suspension,
missing-foundation and live approval gates remain after a merge.

## Tenant UI and authorization

Preserve the stable PerkForge portal and household Nextcloud experience. A new
Kubernetes/GitOps UI is an operational companion, not a portal rewrite. Existing
[tenant security evidence](TENANT-SECURITY-BOUNDARY.md) includes targeted Rancher
viewer API denials; it is a baseline to reproduce, not proof for another UI.

Headlamp is the preferred first evaluation candidate, consistent with the user’s
interest. Pair it with the [official Flux plugin](https://github.com/headlamp-k8s/plugins/tree/main/flux)
for GitOps status. Pin plugin image digest and UI/API versions; upstream plugin
examples use moving tags and older Flux APIs and are not deployment templates.
Test namespace-only list/search/graphs without granting broad reads merely to
make a page work. Big Bang 3.35.1 pins the
optional addon, and it exposes Kubernetes resources without requiring Flux
Operator ownership. Its exact package's
[RBAC documentation](https://repo1.dso.mil/big-bang/product/packages/headlamp/-/blob/0.45.0-bb.1/docs/RBAC.md)
requires Kubernetes API OIDC configuration for group-based access. Rancher OIDC
alone does not make direct API tokens valid: validate issuer, audience and group
claims for the forwarded user token as described by [Headlamp OIDC](https://headlamp.dev/docs/latest/installation/in-cluster/oidc/).
Tenant grants should be explicit
namespace RoleBindings; do not copy cluster-wide example role bindings.

**Pinned-source hazard:** vendored upstream Headlamp 0.45.0 defaults
`clusterRoleBinding.create: true` with `clusterRoleName: cluster-admin`.
`bigbang.rbac.enabled` is an independent switch and is insufficient to disable
that binding. Set `upstream.clusterRoleBinding.create: false`; review the
backend service account, and keep `unsafeUseServiceAccountToken: false`.
Login and a visible namespace selector are not authorization evidence.

Flux Operator's UI is another candidate, but its
[standalone installation support](https://fluxoperator.dev/docs/web-ui/standalone-install/)
is explicitly scoped: it can run beside CLI-bootstrapped Flux with CRDs, while
official support requires Operator-managed clusters. Treat Big Bang-owned Flux
plus standalone UI as a support tradeoff. Review authentication defaults,
server-side authorization, distribution/licensing and operational cost before
selection. Its [user management guide](https://fluxoperator.dev/docs/web-ui/user-management/)
describes anonymous cluster-wide Flux viewing by default and predefined roles
with wildcard reads; use authenticated custom roles instead. Review elevated
backend read/action paths, not just namespace filtering. Do not add another
Flux lifecycle owner to resolve a UI limitation.

Flux itself [defaults to controller cluster-admin authority](https://fluxcd.io/flux/installation/configuration/multitenancy/).
For tenant-controlled sources, require scoped `.spec.serviceAccountName`,
deny cross-namespace references and remote bases, and use a default service
account with no deployment privileges when omitted. Check flags against pinned
controller versions. Big Bang's outer and child platform releases need explicit
platform deployment identities when this default is enabled; otherwise they
fail. Platform sources and releases stay platform-owned in protected namespaces.
Do not allow tenants to change impersonated identity, target/storage namespace,
source credentials, arbitrary kubeConfig references, or cluster-scoped resources.
RBAC cannot constrain arbitrary CR fields: enforce those invariants through
admission and protected platform enrollment, then prove the denials.

Workload creation can exfiltrate a Secret through mounts or execute as another
service account without `get secrets`. Preserve existing portal admission,
release-storage separation, image/source constraints, and platform ownership of
PSA, quota, NetworkPolicy and tenant labels. Tenant developer roles must not gain
RBAC bind/escalate/impersonate, policy mutation or privileged workload paths.
Per-tenant deployer/runtime identities remain distinct. UI reconciliation and
suspend actions are mutations and need explicit roles and audit trails.

Before a UI is tenant-ready, test two disjoint tenants and a no-grants identity,
then viewer/developer/admin roles with real issued
tokens: allowed own-tenant reads, denied cross-tenant direct URLs/API calls,
denied secret and release-storage access, denied role/policy changes, deployment
identity escalation and source substitution; include sensitive ConfigMaps, Helm
values/history, source artifacts, logs, exec and port-forward in the exposure
review. Audit effective identity; verify session expiry and group
revocation. Re-run pod network, admission, quota and secret-delivery tests.
Shared namespaces/control planes/kernels remain shared-risk boundaries; a UI
or curated package cannot establish compliance or strong tenant isolation.

Big Bang’s security integrations are a substantive reuse benefit, beyond its
application catalog. Its [pinned NetworkPolicy guide](https://repo1.dso.mil/big-bang/bigbang/-/blob/3.35.1/docs/configuration/network-policies.md)
and bb-common/package values provide policy, SSO and optional mesh wiring.
Inspect and adapt their generated output before duplicating those controls.
A separate local Headlamp render with network policies enabled produced eight
policies: default ingress/egress denial, namespace-local and DNS allowances, plus
API/mesh/monitoring allowances. The API-labelled egress rule in this specimen
actually allowed `0.0.0.0/0` except metadata IP, without a port restriction; mesh
allowances also remained despite this specimen’s disabled mesh. These are
rendered findings, not live enforcement evidence or an approved network policy.
Review actual destinations, selectors, ports and provider API topology rather
than inferring narrow coverage from a policy name.

Reuse suitable package controls, then address gaps explicitly: the unwrapped
OpenBao chart and tenant portal do not inherit those bb-common integrations.
Their secrets/database/identity/API flows, cross-tenant denial, policy ownership
and admission boundaries still need platform-owned review and tests. Mesh or
security-package enablement alone neither proves tenant separation nor replaces
RBAC/admission. These requirements do not authorize installing the default stack.

## Capacity, secrets, and maintenance

Three M920q nodes at 16 GB each provide 48 GB nominal aggregate memory, not
48 GB schedulable application capacity. Reserve OS/RKE2/CNI/CSI/control-plane
resources per node, then plan for a node outage with two nodes remaining.
CPU models/core counts and per-node disks still need confirmation. The 750 GB
aggregate raw storage is not usable resilient storage: three replicas would
give at most roughly 250 GB before filesystem, system, reserve and imbalance
costs. Local-path is node-bound; replication is not backup. #42 must settle
storage, off-cluster backups and demonstrated restores before household data use.

Big Bang's default enabled packages include Istio components, Kiali, Kyverno,
Alloy, Loki, NeuVector, Tempo, monitoring/Grafana and cert-manager. Those defaults
are a curated integration starting point, not a small-cluster capacity plan.
The [pinned prerequisites](https://repo1.dso.mil/big-bang/bigbang/-/blob/3.35.1/docs/getting-started/prerequisites.md)
offer no universal production minimum. Choose an explicit package allowlist,
short bounded retention, realistic requests, and measure steady state, upgrade
surge and one-node-loss behavior before enabling more services. Mesh adoption
belongs to #45's threat model; do not replace Traefik or Canal incidentally.

Curated packages provide coordinated source/image pins, integration values,
policy/SSO wiring and release guidance. They also add package-specific schemas,
Iron Bank access and licensing obligations, integration coupling and ongoing
upgrades. Budget time for Big Bang + controller + child package release notes,
schema changes (including the documented future 4.0 values migration), rendered
diffs, API deprecations, CVE response and backup/restore rehearsal. Pinning is
reproducibility, not a patching policy. Selective reuse gives up some integrated
test coverage and makes PerkForge responsible for the resulting combination.

Each cluster should pull its own root source and have separate Git read
credentials, registry credentials, encryption keys and secrets-provider identity.
No management cluster should routinely hold all workload-cluster admin kubeconfigs.
Shared values are non-sensitive only. Keep OpenBao/ESO work (#31–#33), with
cluster-specific auth mounts/roles and narrowly scoped tenant delivery; do not
replace it with Big Bang Vault merely because a package exists. Bootstrap
secrets and any SOPS recovery custody require a separate approved design.
Tenants cannot write ClusterSecretStores or select other tenants' paths.

## Human review and later validation

This PR changes documentation only. It does not supersede accepted
[ADR-0001](ADR-0001-tenant-foundation.md), move workloads, create repositories,
change credentials or authorize #41 implementation. Resolve #14/#20 layout and
ownership first. Preserve Nextcloud data and the portal while reviewing #41's
authentication, network, TLS, storage and recovery foundations incrementally.

Human review should decide whether selective reuse is sufficient, or whether a
small separate Flux/UI evaluation is worth its cost. A later approved evaluation
must prove the same tenant/security behavior, package compatibility, resource
headroom, upgrade/recovery and usable UI before any adoption decision. Keep #46
In Review until the proposal is approved; do not equate a ready proposal with
an adopted architecture or a completed migration.
