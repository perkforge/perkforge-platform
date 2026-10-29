# Big Bang bootstrap

Big Bang 3.35.1 supplies curated packages; its pinned Flux prerequisites and Flux reconcilers own deployment. Ansible handles explicit bootstrap and application API configuration. No custom configuration generator or vendored charts are required. Start with `clusters/<target>/kustomization.yaml`; its resource list is the composition table of contents.

## Ownership and entrypoints

```text
infrastructure/                     RHEL and RKE2; no application GitOps
big-bang-bootstrap/
  ansible/inventory.yaml            named API target + environment/profile + Git path
  ansible/bootstrap.yaml            gated Flux install + paused root seed
  clusters/local/             explicit target values and composition
  shared/, providers/, profiles/    reusable selected values
  bigbang/, apps/                   chart references and package values
  enrollments/                     generic reference to separate enrollment Git
  identity/                        reviewed platform identity foundations
  stages/                          explicit incremental activation/recovery selections
  tests/                           pinned render inputs and offline verification
```

Local means the platform engineer's own local physical cluster, environment local/profile il2. It is not a VM target. Cluster identity, environment, profile, hosting and distribution are independent. VM provisioning and deployment workflows are removed; Git history retains their source. Local is the sole concrete starting target; other targets are explicit operator additions.

The safe default does not contact Kubernetes:

```sh
ansible-playbook -i big-bang-bootstrap/ansible/inventory.yaml \
  big-bang-bootstrap/ansible/bootstrap.yaml --limit local
```

Inventory `gitops_path` becomes `cluster-root.spec.path` through `ansible/seed.yaml.j2`. That path selects a local `kustomization.yaml`, which assembles the outer Big Bang HelmRelease and values ConfigMaps. Flux Kustomization CRs reconcile; local kustomization files describe builds. Live bootstrap remains gated by explicit approval, target kubeconfig/context/UID, published configuration tag and checked release evidence.

The bootstrap seeds a paused root and the outer Big Bang release is suspended. Explicit stage/enrollment definitions can contain unsuspended descendants; do not resume the root until their prerequisites and selected companion releases have been reviewed. `stages/` retains the proven incremental Headlamp → Keycloak → identity → enrollment paths and their recovery/approval runbooks; selecting a stage is an explicit operational action. Moving files does not activate a stage or update a running cluster. Existing published tags contain old paths: adopt the new layout only via a new verified release and reviewed root-path change.

## Change values

Edit `clusters/<target>/values.yaml`. Outer Helm precedence is chart defaults → shared → selected OpenBao → selected Keycloak (app then database) → provider → impact profile → cluster. Later maps merge, lists replace; inspect `bigbang/release.yaml` for the authoritative `valuesFrom` order. Reusable definitions do not install an app everywhere: each cluster explicitly selects them. Tenant app values cannot override platform namespace/RBAC/admission/network boundaries.

Keep chart refs pinned and release evidence separate from human-authored config. Do not commit rendered manifests; render to a temporary directory for inspection.

## Add a target such as dev

1. Copy `clusters/local/` to `clusters/dev/` and `enrollments/local/` to `enrollments/dev/`. In the new cluster root change the resource reference to `../../enrollments/dev`, plus cluster/environment annotations. In the enrollment root change cluster/environment annotations and `reconcile.yaml` path to `./clusters/dev`. Keep new reconciliation suspended until reviewed.
2. Add inventory host `dev` with `gitops_path: ./big-bang-bootstrap/clusters/dev`, `deployment_environment: dev`, and explicitly selected `impact_profile: il2`. API kubeconfig/context/UID and release evidence are operator inputs, independent of the alias.
3. Set the new cluster's domains, identity callback/issuer, placement/storage and app selections. Maps merge in documented values order; lists replace. Do not infer hosting/distribution/security from the name dev.
4. Add matching environment/profile/cluster roots in enrollment and app Git; publish reviewed releases and update refs/evidence. Use shared environment values only where real reuse exists. Confirm context agreement, paths/pins, omitted apps, no privilege weakening and safe defaults before live approval.

## Add an impact profile such as il5

1. Establish reviewed security requirements and platform controls; copying il2 is only a structural starting point, not an IL5 implementation.
2. Copy `profiles/il2/` to `profiles/il5/`; author only justified supported values and invariants. In `clusters/dev/kustomization.yaml`, select `../../profiles/il5` and set the profile annotation to il5. Select il5 explicitly in the inventory.
3. Select matching profile context downstream. App-level profile settings cannot override platform-owned RBAC, admission, namespace or networking. If an app needs real profile-specific settings, add a reusable profile values input in its repository; do not fabricate differences for symmetry.
4. Validate rendered precedence (shared → selected app → provider → profile → cluster), required controls and late-override rejection. Review exceptions with owner/rationale/expiry. Test mismatched target/environment/profile rejection and update release evidence before activation.

Only il2 is shipped as a selection label with the existing Headlamp unsafe-token/default-binding guardrails. IL2 preparation, broader hardening and evidence readiness are deferred. Environment, cluster identity and impact profile are separate dimensions; neither profile name confers authorization or compliance. No il5 target or security readiness is claimed.

## Add a tenant

Work in [platform-tenants](https://github.com/perkforge/perkforge-platform-tenants). Enrollment owns tenant namespaces, security foundations, scoped identities and app registration; only intended cluster roots opt in. The application repository owns its chart/settings. This bootstrap knows only the enrollment repository/ref/cluster path, never tenant names. Shared and dedicated tenant clusters need the same explicit ownership choices.

## Operations and verification

- [Identity stage](stages/local-identity/LIVE-PLAN.md), [enrollment stage](stages/local-enrollment/README.md): staged approval and recovery.
- `ansible/platform-config/`: retained gated OpenBao application API configuration; not an installation path or initialization/unseal authorization.
- Rancher remains reserved for platform-admin cluster lifecycle management. Its old installer is historical; no portable management activation is implemented by this restructuring. Flux owns application reconciliation.
- [Evidence inventory](../docs/RESTRUCTURE-INVENTORY.md): active versus historical/adaptation status.

Offline checks use `KUBECONFIG=/dev/null`, temporary renders and pinned source fixtures. No restructuring check should run live integration. Existing test suites under `tests/` retain their opt-in gates for synthetic API tests. See the CI workflow for fixture checkout/environment inputs.

## Point local at your physical cluster

1. Clone the repository and select a reviewed released tag. Install the CLI tools used by the pinned workflow (Ansible, kubectl and Helm); provide an existing healthy Kubernetes cluster, CNI/network-policy support, storage, DNS/ingress and trusted identity/TLS plan. Infrastructure starter playbooks do not provision a complete physical cluster yet.
2. In `ansible/inventory.yaml`, select your target kubeconfig/context and actual kube-system UID, released configuration tag/evidence and a writable pinned Big Bang source checkout. Keep apply false while reviewing. No personal paths or API endpoints are assumed.
3. Edit `clusters/local/values.yaml` and the explicitly selected stage inputs. Replace `example.test` browser hosts, node placeholders, storage class/node/path and TLS/Secret references. Inspect `identity/context.yaml`, identity routes/storage/RKE2 OIDC files and identity verification API/CA paths together. Those are authored YAML inputs, not generated discovery.
4. If enabling tenant enrollment, create matching local context/hosts/issuer settings in the separately reviewed enrollment/application repositories and select their published releases. The retained dependency tags describe the preceding trial and are not automatically retargeted to a new engineer's cluster.
5. Render offline, inspect full inventory and capacity, then review a concrete live plan. Configure registry, identity, TLS and Kubernetes credentials only through the existing gated playbooks with separately approved protected inputs. Never pass secrets in command arguments.

`example.test`, `UNCONFIGURED` and `REPLACE_WITH_*` are deliberately visible operator inputs, not usable deployment defaults. Live identity initialization is one-shot and must not adopt an existing realm blindly. No change here affects the running historical trial.
