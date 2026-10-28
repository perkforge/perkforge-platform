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
`02efc8b0d259ee0cd2c31ea857d50a4021cf6d8e`, was inspected locally. This is a
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
4. **Apply the root source and Flux Kustomization.** The source points to the
   protected environment repository and the root selects only
   `clusters/lab` or `clusters/physical`. It references the source and an explicit
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
as references. Exact root manifests, secret bootstrap and recovery behavior need
future implementation review and live validation. Flux's `bootstrap git` is a
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

Proposed shallow layout, coordinated with #14/#20, not created by this PR:

```text
perkforge-platform/             # Ansible hosts/RKE2, bootstrap and enrollment
  ansible/{local-lab,physical}/ # distinct inventories; no shared addresses
  platform-config/             # Ansible API configuration, shared + scoped vars
perkforge-platform-apps/        # platform-owned deployment definitions
  shared/{releases,values}/    # pinned charts and common non-secret settings
  clusters/lab/               # own root source/path and short cluster values
  clusters/physical/          # own root source/path and short cluster values
perkforge-tenant-*/             # application charts, tenant-maintained inputs
```

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

### Concrete two-cluster specimen

[common.yaml.example](examples/bigbang-flux/common.yaml.example),
[lab.yaml.example](examples/bigbang-flux/lab.yaml.example), and
[physical.yaml.example](examples/bigbang-flux/physical.yaml.example) illustrate
one common file plus one cluster file. They are deliberately outside all live
enrollment paths and use `.invalid` DNS. They are **not a deployment profile**:
identity, ingress, policy, resource sizing and secret delivery are incomplete.
Only Headlamp is enabled for rendering; metrics-server `auto` is explicitly
disabled to avoid an additional RKE2 component owner. Network policy disabled
in this render specimen does not propose weakening platform policy.

Common values set `addons.headlamp.values.upstream.replicaCount: 1`, disable
upstream cluster-admin binding, and leave unsafe shared-SA authentication false.
Lab overrides only domain and one replica; physical overrides domain and two
replicas. Two is an illustration, not an HA or sizing recommendation.

Equivalent ordered local commands with an already installed Helm 3.19.0 and
the exact research checkout (no cluster access):

```sh
helm lint /tmp/perkforge-bigbang-3.35.1/chart --kube-version 1.36.5 \
  -f docs/examples/bigbang-flux/common.yaml.example \
  -f docs/examples/bigbang-flux/lab.yaml.example
helm template bigbang /tmp/perkforge-bigbang-3.35.1/chart \
  --namespace bigbang --kube-version 1.36.5 \
  -f docs/examples/bigbang-flux/common.yaml.example \
  -f docs/examples/bigbang-flux/lab.yaml.example > /tmp/lab.yaml
# Repeat with physical.yaml.example; compare each cluster before/after a change.
```

**Locally rendered:** Helm lint and both outer chart renders passed. The pinned
Headlamp package `0.45.0-bb.1` (commit
`f8a2b6c9b47edd9c86307ed40c3e9dd959d9bd8f`) includes vendored dependencies.
Its child chart was also rendered using the outer Secret's ordered effective
values. Deployment replicas were respectively 1 and 2; both rendered zero
ClusterRoleBindings. These observations verify values flow, not tenant access.
Hook resources still need review; package defaults include a wait Job and its
egress policy. No bootstrap, installer, admission call or cluster check ran.

For a future approved implementation, local checks should render the bootstrap,
outer chart and every enabled pinned child chart; validate schema and policies,
compare before/after rendered output per cluster, detect duplicate object owners,
and total requests/PVCs. Save tool versions, input pins and redacted diffs as PR
artifacts. Never upload rendered real credentials. Run synthetic policy tests
locally; reserve API admission dry-runs and reconciliation for separately
authorized live validation. `helm template` cannot prove CRD admission, hooks,
storage provisioning, OIDC, networking or recovery.

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
