# Big Bang evaluation proposal

Documentation and local render specimens only; see the
[architecture proposal](../docs/BIGBANG-FLUX-PROPOSAL.md). This new effort leaves
`local-lab/` intact. It reuses reviewed concepts, not a wholesale copy or migration.
No installer, inventory, root Flux enrollment or deployable profile is provided.
Do not apply these files to the current tiny VMs. A separate folder does not
separate runtime resources: the target cluster and every controller/CRD/release
owner remain undecided. A later approved test needs an explicit target and budget.

## Inputs and inspectable outputs

The exact Big Bang research pin remains 3.35.1, commit
`02efc8b0d259ee0cd2c31ea857d50a4021cf6d8e`. Examples select one shared profile:

| Input | Purpose |
| --- | --- |
| [shared values](examples/shared/values.yaml.example) | Explicit package switches and platform-owned OpenBao source |
| [RKE2 provider placeholder](examples/providers/rke2/values.yaml.example) | Empty provider values; prerequisites unimplemented |
| [il2 profile](examples/profiles/il2/values.yaml.example) | Illustrative UI guardrails only; not DoD requirements |
| [lab selection](examples/clusters/lab/selection.yaml.example), [values](examples/clusters/lab/values.yaml.example) | Profile/file order and one replica |
| [physical selection](examples/clusters/physical/selection.yaml.example), [values](examples/clusters/physical/values.yaml.example) | Same profile, different domain and two replicas |
| [lab rendered directory](examples/rendered/lab), [physical rendered directory](examples/rendered/physical) | Full outer Big Bang plus Headlamp/OpenBao child outputs; synthetic inputs only |

Order: **chart defaults → shared → provider → selected profile → named-cluster values**.
The `selection.yaml.example` is descriptive, not a Kubernetes manifest and not
consumed by a custom generator. Future Ansible/bootstrap and native Flux wiring
must enumerate the same inputs explicitly. `il2` labels selection intent only;
neither these values nor their output establish an impact-level authorization.
Reusable profiles avoid duplicating `cluster-name/il2` trees. Cluster-specific
endpoints, capacities, credentials and deployment identities stay with clusters.

After merging, validate constraints independently of precedence. For these
illustrative inputs, reject a true upstream clusterRoleBinding.create or
unsafeUseServiceAccountToken, then check actual rendered bindings/backend args.
A negative check with a late weakening override must fail. Real profiles need
approved requirements and reviewed exceptions (cluster, rule, justification,
owner, expiry and test evidence), never silent bypass by a later values file.
Protect profile and platform-package changes from tenant repository writers.

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

## Local evidence and remaining gates

Already available Helm 3.19.0 and cached exact chart inputs were used. No tools,
dependencies, credentials or cluster resources were installed. From repo root:

```sh
helm lint /tmp/perkforge-bigbang-3.35.1/chart --kube-version 1.36.5 \
  -f local-lab-big-bang/examples/shared/values.yaml.example \
  -f local-lab-big-bang/examples/providers/rke2/values.yaml.example \
  -f local-lab-big-bang/examples/profiles/il2/values.yaml.example \
  -f local-lab-big-bang/examples/clusters/lab/values.yaml.example
helm template bigbang /tmp/perkforge-bigbang-3.35.1/chart \
  --namespace bigbang --kube-version 1.36.5 \
  -f local-lab-big-bang/examples/shared/values.yaml.example \
  -f local-lab-big-bang/examples/providers/rke2/values.yaml.example \
  -f local-lab-big-bang/examples/profiles/il2/values.yaml.example \
  -f local-lab-big-bang/examples/clusters/lab/values.yaml.example > /tmp/lab.yaml
# Repeat with physical inputs; compare with examples/rendered/<cluster>/bigbang.yaml.example.
```

Child output uses the outer chart's generated Secret values: Headlamp's
`common`, `defaults`, `overlays` in that order, and OpenBao's `values.yaml`.
Render those with the exact Headlamp 0.45.0-bb.1 and OpenBao 0.30.6 charts.
Artifact trailing whitespace is normalized for review; these are render evidence,
not byte-for-byte chart archives or deployable manifests. These rendered Secrets
contain only synthetic non-sensitive configuration.
Do not reuse this artifact publishing pattern with real secret values.

Local findings: outer lint/renders passed for both selections; Headlamp child
replicas are 1/2 with no ClusterRoleBindings. The wait Job and OpenBao injector
are explicitly disabled. OpenBao still renders a server StatefulSet, 10 GiB
PVC template and Kubernetes auth-delegator binding. Headlamp and OpenBao server
resources lack explicit budgets in these outputs. OpenBao's default TLS/backend
configuration is not an approved secured service; do not deploy it. Keycloak,
portal, their dependencies and full bootstrap are not rendered integrations in
this specimen. The two UI guardrails passed effective-values checks, including
a negative weakening case; that is not a complete security-policy validator.

Before any live action: decide target and ownership; complete four-app/dependency
pins and full renders; explicit per-workload budget and capacity review; approved
network/admission, TLS, OIDC/RBAC, bootstrap secrets and recovery designs; then
obtain action-specific approval. Preserve the small Ansible bootstrap preference,
pinned Flux prerequisites and one-owner Git handoff from the proposal. Runtime
reconciliation, tenant API denials, revocation, resource usage and recovery all
need future live validation. The illustrations cannot yet be deployed safely.
