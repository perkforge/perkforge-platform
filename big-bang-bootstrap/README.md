# Big Bang bootstrap

One named cluster root composes reviewed configuration; Ansible bootstraps and configures, then Flux reconciles Big Bang. Infrastructure Ansible separately owns RKE2/Rancher. No custom configuration generator or second application reconciler is required.

```text
clusters/local/                    sole physical starting target
enrollments/                       generic connection to protected enrollment Git
profiles/il2/                      reusable selection label and existing guardrails
providers/rke2/                    distribution-specific values
configuration/
  defaults/                        common disabled-stack defaults
  packages/{bigbang,headlamp,keycloak,openbao}/
  identity/                        realm/API trust, foundations, routes, user grants
  ansible/                         gated bootstrap/API tasks and readiness checks
tests/{configuration,bootstrap,security,integration,fixtures}/
```

Local means an engineer-owned physical cluster, not a VM. Environment, cluster identity, provider, hosting and impact profile are independent. VM/AWS provisioning harnesses and unused concrete dev are removed; their source remains in Git history.

## Point local at your physical cluster

1. Clone and select a reviewed release. Supply a healthy supported Kubernetes cluster and the installed Ansible/kubectl/Helm tools. Physical RHEL/RKE2/Rancher inputs are described in `infrastructure/ansible`; IP reservations are not OS installation or live approval.
2. Edit `configuration/ansible/inventory.yaml`: target kubeconfig/context, actual kube-system UID, published configuration tag/evidence and writable pinned Big Bang checkout. Defaults are UNCONFIGURED/apply=false. Use external protected credentials; never CLI secret values.
3. Edit `clusters/local/values.yaml`, the selected package values and `configuration/identity/context.yaml`. Replace example.test hosts, node/storage placeholders, TLS/Secret references and issuer/callback inputs consistently. Configure trusted DNS; no personal hosts alias is supplied.
4. If enrolling tenants, publish matching context/endpoints/placement in the separate enrollment/app repositories and select those reviewed releases. Existing dependency tags describe the preceding trial; they are not automatically portable to a new cluster.
5. Render the complete inventory and assess capacity/security before the separately approved [activation order](configuration/ansible/README.md). The root seed, outer release and generic enrollment remain paused. Moving files or publishing a release never activates them.

Safe syntax/default walkthrough:

```sh
ansible-playbook -i big-bang-bootstrap/configuration/ansible/inventory.yaml big-bang-bootstrap/configuration/ansible/bootstrap.yaml --syntax-check
ansible-playbook -i big-bang-bootstrap/configuration/ansible/inventory.yaml big-bang-bootstrap/configuration/ansible/bootstrap.yaml --limit local
```

Inventory gitops_path → seed.yaml.j2 → cluster-root.spec.path → clusters/local/kustomization.yaml → package HelmRelease/valuesFrom → pinned Big Bang child releases. A local kustomization file is a build recipe; a Flux Kustomization is a reconciling CR.

## Values and ownership

The cluster root's resource list is its table of contents. Packages are explicitly selected, not installed everywhere. The outer ordered values are chart defaults → common defaults → selected package/identity settings → provider → impact profile → cluster. Later maps merge, lists replace; inspect `configuration/packages/bigbang/release.yaml` for exact order. No generated deployment manifests are committed.

Big Bang3.35.1 and its prerequisite source commit remain verified separately from configuration release tags. Ansible owns namespaces/installer foundations; the umbrella/children have scoped identities and no namespace-creation authority. Only protected enrollment Git owns tenant namespaces/security/deployment identities. App Git owns applications; app values cannot grant platform privileges.

## Add a target such as dev

1. Copy clusters/local to clusters/dev and enrollments/local to enrollments/dev. Change the new cluster resource reference to ../../enrollments/dev plus cluster/environment annotations; change enrollment context annotations and reconcile.yaml path to ./clusters/dev. Keep source/root/release/enrollment paused until reviewed.
2. Add inventory host dev with gitops_path ./big-bang-bootstrap/clusters/dev, deployment_environment dev and explicit impact_profile il2. Supply its API identity/release inputs separately. Never infer hardware/distribution from the name dev.
3. Set its hosts, issuer/callback, placement/storage and package selections. Add matching roots/environment/profile settings in enrollment/app Git; publish compatible tags and update evidence. Shared environment values are optional when actual reuse justifies them.
4. Test context/pin/path mismatches, omitted apps, precedence, permissions and safe defaults. No new target is live merely because its folder exists.

## Add an impact profile such as il5

Establish reviewed requirements first. Copy profiles/il2 to profiles/il5 as a structural starting point, author supported values/invariants, and explicitly select ../../profiles/il5 in the target root, its annotation and inventory. Select the same context downstream. Add real app-profile inputs only where needed; they cannot weaken platform controls. Validate rendered late overrides and reviewed exceptions (owner/rationale/expiry).

Only il2 ships, containing existing Headlamp unsafe-token/default-binding guardrails. Actual IL2 preparation/hardening/evidence readiness is deferred. A copied il5 label implements no IL5 controls or authorization; capability gates must be reviewed for any new profile.

## Add a tenant

Work in perkforge-platform-tenants. Enrollment owns foundation/registration/scoped identities and explicitly opts tenants in per cluster; app Git contains chart settings. This bootstrap knows only enrollment repository/ref/path, not individual tenants. Shared and dedicated tenant clusters require explicit ownership and reviewed boundaries.

See [test responsibilities and commands](tests/README.md), [shared evidence](../evidence/README.md) and [restructuring inventory](../docs/RESTRUCTURE-INVENTORY.md). Rancher is platform management only; its internal Fleet dependency does not restore the archived custom Fleet deployment.
