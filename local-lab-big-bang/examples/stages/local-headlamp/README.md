# Local Headlamp workload smoke test

This stage is prepared for a later approved test. Nothing runs until an operator
explicitly resumes the paused root. Ordinary `clusters/local` and `clusters/dev`
remain unchanged. No tenant enrollment, OpenBao or Keycloak input is selected.

The path is **shared + RKE2 provider + il2 profile + values.yaml**; this final
values file wins. `il2` remains an illustrative selection, not authorization.
One Big Bang release owns the Headlamp package source/release; there is no second
standalone Headlamp owner. It requests **100m/128 MiB**, limits **500m/256 MiB**,
and places one Pod on `cks-worker`. Initial install only; one rollout surge can
add another 100m/128 MiB request and 256 MiB cap.

## What gets created

| Layer | Exact authored/rendered inventory |
| --- | --- |
| Ansible foundation | 2 Namespaces, 3 installer ServiceAccounts, 4 Roles, 4 RoleBindings |
| Root | 4 values ConfigMaps, `bigbang-chart` GitRepository, `bigbang` HelmRelease |
| Big Bang after its post-render | 2 values Secrets, `headlamp` GitRepository and HelmRelease |
| Headlamp | 1 ServiceAccount, 1 ClusterIP Service on 4466, 1 Deployment |
| Runtime | 2 HelmCharts, parent/child Helm history Secrets; `headlamp/private-registry` delivered separately |

No PVC, ingress/gateway, CRD, NetworkPolicy, hook/wait Job or UI RoleBinding is
added by the application render. Existing Flux/RKE2 CRDs and NetworkPolicies stay
in place. Network policies for an eventual tenant-facing UI still need review.

## Ownership and permissions

Ansible owns `bigbang` and `headlamp` namespaces. The root omits `bigbang`'s
Namespace object, and the umbrella's single post-render rule omits `headlamp`'s
Namespace object. These two explicit ownership rules avoid Helm namespace
adoption and any new cluster-wide namespace permission. No chart is vendored.

| Identity | Allowed scope |
| --- | --- |
| `flux-system/platform-reconciler` | ConfigMaps, GitRepositories and HelmReleases in `bigbang`; no Secrets or RBAC |
| `bigbang/platform-reconciler` | Helm storage/values Secrets and package GitRepositories/HelmReleases in `bigbang` |
| `bigbang/headlamp-installer` | Deployment, Service and ServiceAccount management in `headlamp`; read Pods/ReplicaSets for Helm readiness; Helm storage Secrets in `bigbang` |

There are no new ClusterRoles/bindings, wildcards, impersonation grants, exec or
RBAC-write grants. Helm history needs namespaced Secret CRUD; create cannot be
resourceName-restricted in Kubernetes RBAC. Workload deployers can mount namespace
Secrets through Pods even without direct Secret API permission: these are trusted
platform installer roles, never tenant/login roles. Platform authors can change
reconciler identity fields; these Roles alone are not an admission boundary for
untrusted tenant repositories. No tenant is enrolled in this stage.

Headlamp's application ServiceAccount gets **no RoleBinding**, upstream
cluster-admin binding stays disabled, and unsafe service-account-token fallback
stays false. Default binding examples are cleared to avoid creating `dev-sa`.
No tenant/browser SSO claim: Keycloak and API OIDC trust are not configured by
this smoke test. HTTP readiness does not need Keycloak; tenant UI acceptance does.

## Prepare and activate only after review

All commands run from the repository root. Safe offline walkthrough:

```sh
ansible-playbook -i local-lab-big-bang/examples/ansible/inventory.yaml \
  local-lab-big-bang/examples/ansible/headlamp-foundation.yaml --limit local
ansible-playbook -i local-lab-big-bang/examples/ansible/inventory.yaml \
  local-lab-big-bang/examples/ansible/bootstrap.yaml --limit local \
  -e @local-lab-big-bang/examples/stages/local-headlamp/bootstrap-inputs.yaml
```

For a later live approval, first merge/release this platform change through the
existing Release Please process. Select an actual published tag containing this
path; v0.3.0 does not contain it. Check out that exact release cleanly. The
foundation playbook rejects code differing from supplied release evidence. No
changes/releases are needed in the enrollment or portal repos for this stage.

Prepare a private ignored input file with target kubeconfig/context/expected
cluster UID, published config tag and release evidence. For credential delivery,
also supply `registry_username` and **path only** `registry_credential_file` (mode
0600, regular file). Never put credential values in Git or CLI arguments.

The bundled activation scope must explicitly approve:

1. `foundation_apply=true` for namespaces/installer RBAC; optional explicit
   `headlamp_registry_apply=true` delivers Registry1 auth to
   `headlamp/private-registry` through `no_log`/stdin. The existing `flux-system`
   Secret is not available across namespaces. Verify exact Headlamp image access
   using the designated file only with Registry1; do not reuse it with GitHub.
2. Existing `bootstrap.yaml` with the stage's `bootstrap-inputs.yaml`, published
   tag/identity inputs and `bootstrap_apply=true`. This still leaves source/root
   **paused**; public source omits `secretRef`, without creating Git credentials.
3. Resume `cluster-config`, verify its artifact, then resume `cluster-root`.
   Only this authored stage may be selected; no ad hoc full-stack unpause.
4. Verify chart sources, parent and child HelmRelease Ready; exact image/placement,
   private Service endpoints, zero restarts and ten minutes of resource evidence.

Applications use public pinned chart sources. Headlamp needs its own Registry1
image pull Secret; explicit values wire it into the Pod. No storage class, PVC,
new certificate, API-server OIDC, host DNS, Traefik change or port-forward is
needed for workload readiness. Traefik continues to own node ports 80/443.

## Failure and next gates

Retain the measured Flux-trial host/node/PSI/swap floors, with a fresh baseline
before this test. Observe source fetch/render peaks as well as the Pod; idle Flux
measurements do not prove active reconciliation peaks. Installation remediation
retries are zero so failed attempts are retained rather than repeatedly removed.
If a stop criterion fires, separately pre-approved containment suspends the stage
root, stage sources and parent/child releases, then scales only the Headlamp
Deployment to zero. No Helm uninstall, namespace deletion, resource increase,
image substitution or broad Flux shutdown. Keep chronological sanitized evidence
under ignored `local-lab/evidence/bigbang-trial/`.

Later stages: approved storage + PostgreSQL, Keycloak/realm/client/API trust,
Headlamp SSO/plugin/tenant denial tests and ingress/TLS, TLS/init/recovery-reviewed
OpenBao, then separately scoped tenant portal enrollment. This stage provides
workload-integration evidence, not those later security or runtime guarantees.
