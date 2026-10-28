# Big Bang evaluation: human workflow

This is a disabled, offline-testable example, not a deployable platform. Existing
`local-lab/`, Fleet workloads and protected household data remain unchanged.
See the [architecture rationale](../docs/BIGBANG-FLUX-PROPOSAL.md) for source-backed
tradeoffs and future live acceptance gates. Do not apply this to the tiny VMs.

## Find the entrypoint

| Target | Purpose | Environment | Profile |
| --- | --- | --- | --- |
| local | local VMs | local | il2 |
| dev | future physical cluster | dev | il2 |

From this directory, the safe default walkthrough is:

```sh
ansible-playbook -i examples/ansible/inventory.yaml examples/ansible/bootstrap.yaml --limit local
```

The default `bootstrap_apply: false` and `bootstrap_verify_release: false` print
selection and skip every Git/API task (`changed=0`).
No target kubeconfig/context/UID or configuration tag/evidence has been supplied.

```text
examples/ansible/inventory.yaml: local.gitops_path
 → seed.yaml.j2: cluster-config GitRepository + cluster-root Flux Kustomization
 → spec.path: ./local-lab-big-bang/examples/clusters/local
 → clusters/local/kustomization.yaml: explicit shared/app/provider/profile inputs
 → bigbang/release.yaml: chart source + ordered valuesFrom
 → pinned Big Bang chart: component sources/releases
 → enrollments/local: generic enrollment repo at ./clusters/local
 → enrollment repo: selected tenants → scoped app repo at ./gitops/clusters/local
```

Ansible selects both API identity and Git path; neither implies the other. A local
`kustomization.yaml` is a build recipe; a Flux `Kustomization` is a controller CR.
The seed template is a small convenience for inventory fields, not a generator.
Bootstrap's gated live block would install pinned Flux prerequisites, wait for
CRDs/controllers, then apply only paused seed resources. Ordinary reruns must not
compete with later Flux lifecycle ownership. No live block has been tested.

## Edit a cluster's values

Open `examples/clusters/<target>/kustomization.yaml` first. Its resource list is
the table of contents. Edit its `values.yaml` for per-cluster hosts and settings.
Helm precedence is chart defaults → `values-shared` → optional `values-openbao`
→ `values-provider` → `values-impact` → `values-cluster`. Later values win;
maps merge, lists replace. No inline values add a hidden override.
`helmRepositories` is a list: do not split it across competing app inputs.
Shared app definitions are included explicitly, not installed on every cluster.

Big Bang's chart source is release **tag `3.35.1`**. The bootstrap checks its
observed commit `02efc8b0d259ee0cd2c31ea857d50a4021cf6d8e` before any gated apply.
A tag alone is not immutable. Configuration and companion repos select exact
release tags; reviewed resolved commits live in release metadata and are checked
before use, independently of the chart tag. Do not vendor charts or generated YAML.

## Add a cluster

1. Copy `examples/clusters/dev/` to a unique target name. Update cluster/environment/
   profile annotations, selected resource paths and cluster values.
2. Copy `examples/enrollments/dev/`; set its Flux `spec.path` to the matching
   enrollment `./clusters/<target>`, then select that component in the cluster root.
3. Add the inventory alias and matching `gitops_path`, `deployment_environment`,
   `impact_profile`. Real API identity and config tag/evidence stay unconfigured until reviewed.
4. Add matching enrollment and app cluster roots in their repositories; select
   reusable app environment/profile values there. Run the checks below.

Names are identities, not inferred environment/security/provider settings. Dev is
physical here; another dev cluster could be RKE2 on AWS. AWS does not imply EKS.

## Add an environment

Set the new `deployment_environment` and matching annotations in all three repos.
In app Git, add a small `gitops/environments/<name>/` values/Kustomization pair and
select it explicitly from the cluster root. Reuse it across clusters.
Platform has no environment values layer because current settings fit cluster
values. If reuse warrants one, add an explicitly selected `values-environment`
ConfigMap and optional ordered valuesFrom between provider and impact; update
render commands/tests to match. Do not add a mandatory directory for every label.

## Add an impact profile

Only `examples/profiles/il2/` is supplied; IL5 folders/targets have been removed.
For a future profile, establish reviewed requirements first, then add a small
`profiles/<name>/` values/Kustomization pair. Select it in the platform cluster
root, inventory and matching context annotations. Add app profile inputs only for
real supported application differences, and select the same profile explicitly.
Update allowed-combination/invariant tests and negative late-override checks.
Exceptions need an owner, rationale and expiry. Profile labels and the example
Headlamp guardrails do not constitute DoD controls or authorization; app inputs
cannot weaken platform RBAC, admission, namespace or network controls.

## Add a tenant

Work in **perkforge-platform-tenants**, not this bootstrap. Add a reusable tenant
folder containing its reviewed source/reconciler and foundation contracts; opt in
only from intended `clusters/<target>/kustomization.yaml` roots. Namespace/RBAC,
NetworkPolicy/quota and registration are platform-owned there. Tenant app Git
contains only app chart configuration under scoped identities. The bootstrap
knows only enrollment repo URL, revision and cluster path—no tenant names.
The companion examples declare missing identities/foundations; they do not
implement or prove those controls. Shared and dedicated tenant clusters both
need explicit ownership and reviewed boundaries.

## Browser and identity contracts

Per-cluster hosts use `<app>-<target>-<profile>.local-lab.test`:

| Service | local | dev |
| --- | --- | --- |
| Headlamp | headlamp-local-il2.local-lab.test | headlamp-dev-il2.local-lab.test |
| Keycloak | keycloak-local-il2.local-lab.test | keycloak-dev-il2.local-lab.test |
| OpenBao | openbao-local-il2.local-lab.test | openbao-dev-il2.local-lab.test |
| Portal | portal-local-il2.local-lab.test | portal-dev-il2.local-lab.test |

Hosts are authored in cluster values, not derived from an assumed live DNS zone.
Headlamp/Keycloak use supported `routes.inbound.<app>.hosts` and matching
test URLs; Keycloak also sets supported `upstream.extraEnv` `KC_HOSTNAME`. OpenBao uses the
official chart's `server.ingress.hosts` with ingress **disabled**. Keycloak remains
disabled. Portal app Git sets its origin and explicit issuer
`https://keycloak-<target>-il2.local-lab.test/realms/household`; its exact callback
contract is `https://portal-<target>-il2.local-lab.test/auth/callback`.
Portal chart creates no ingress; routing/TLS and client registration belong to
reviewed enrollment/foundation work. No DNS/hosts/TLS/client/secret changes are made.
Headlamp OIDC/API trust and exact callback remain future pinned-version setup;
no shared service-account token or default cluster-admin binding is allowed.

## Release references and next merge step

The actual checked chain is **platform feature → enrollment `v0.1.1` → portal
`v0.1.0`**. Deployment sources use `ref.tag`; `release-evidence.json` records the
reviewed dependency resolution separately. CI rejects missing, unpublished or
moved tags and checks actual paths, context and paused scope at those revisions.

Merge this platform tag-conversion PR, then review/check/merge its generated
platform release PR. Only that published release will contain the complete
conversion and tag-aware bootstrap. Do not call platform `v0.1.0` the converted
release: it predates this change. Release versions may change with other eligible
commits; verify the actual publication rather than assuming a future tag.

For future updates: release app → update/release enrollment → update/release
platform. Each consumer selects an already published dependency tag. Merge/release
never unsuspends or authorizes live use. Preserve third-party Action SHA pins.

## Select a bootstrap configuration tag

`config_tag: UNCONFIGURED` stays the default. After the new platform release is
published, choose its actual tag and record reviewed non-secret metadata in a
separate JSON file with `repository`, `tag`, `resolvedCommit` (same shape as the
test fixture below). `scripts/verify-release-ref.sh` supplies the resolution for
review; do not put a source hash back in the inventory or seed.

Supply `config_tag` and `config_release_evidence` explicitly. The preflight
uses the small `examples/ansible/verify-release.yaml` task file to verify the
stable release/tag against that evidence, then reads the named
cluster entrypoint at the resolved commit and checks cluster/environment/profile.
It precedes any gated Kubernetes work. `bootstrap_verify_release=true` runs only
that read-only GitHub preflight; it does not set `bootstrap_apply` or supply target
credentials. Default walkthroughs perform neither network nor Kubernetes work.

There is no circular self-version: this PR does not select its own future tag.
Once its approved release exists, use that published version as the input to its
bootstrap playbook. Keep all live gates separate. The CI fixture uses existing
platform `v0.1.0` only to test preflight mechanics/context—not as the converted
chain or a live recommendation:

```sh
ansible-playbook -i local-lab-big-bang/examples/ansible/inventory.yaml \
  local-lab-big-bang/examples/ansible/bootstrap.yaml --limit local \
  -e bootstrap_verify_release=true -e config_tag=v0.1.0 \
  -e config_release_evidence="$PWD/local-lab-big-bang/tests/fixtures/platform-v0.1.0.json"
```

This bounded check contacts GitHub only and finishes with `changed=0`. Tag
immutability needs reviewed repository protection before live reliance; a release
name alone does not prevent a later retag. No settings are changed here.

## Offline local tests

From repository root, using existing tools only:

```sh
ansible-playbook -i local-lab-big-bang/examples/ansible/inventory.yaml \
  local-lab-big-bang/examples/ansible/bootstrap.yaml --syntax-check
ansible-playbook -i local-lab-big-bang/examples/ansible/inventory.yaml \
  local-lab-big-bang/examples/ansible/bootstrap.yaml --limit local
kubectl kustomize local-lab-big-bang/examples/clusters/local > /tmp/bigbang-local.yaml
kubectl kustomize local-lab-big-bang/examples/clusters/dev > /tmp/bigbang-dev.yaml
ENROLLMENT_CHECKOUT=/path/to/perkforge-platform-tenants \
TENANT_APP_CHECKOUT=/path/to/perkforge-tenant-portal \
  python3 -m unittest discover -s local-lab-big-bang/tests -v
```

Checkouts must match source pins. Tests follow real paths and reject wrong context,
release/evidence or cluster selection, and render the actual Ansible seed. App tests
render ordered values through the existing portal chart, checking disabled output,
synthetic precedence, shared-environment reuse and missing-digest rejection.
Render the cached pinned Big Bang chart with the same ordered `-f` files for lint,
child-value/host review and negative UI override checks; output stays under `/tmp`.
Python is testing only. No generated deployment YAML is committed.

**Offline-ready is not live-ready.** Sources/releases remain suspended, root
prune is false, credentials/identities unprovisioned. Choose target and owners;
complete full four-app renders/dependency inventory and capacity budgets (including
CRDs, databases, PVCs and upgrade reserve), controller hardening, OIDC/RBAC,
network/admission, TLS, secrets and recovery before separate live approval.
Do not install the default Big Bang stack on current VMs. Existing Fleet/Flux
release ownership must not overlap. No full integration, live tenant-denial,
revocation, storage or recovery validation is claimed.

Latest offline evidence: both target builds and pinned Big Bang 3.35.1 lint/render
passed; Headlamp 0.45.0-bb.1 child renders had no ClusterRoleBinding, and a late
unsafe binding override was detected. A synthetic Keycloak-enabled outer render
verified route/KC_HOSTNAME agreement; this is not a full Keycloak deployment or
budget. Both default Ansible walkthroughs had `changed=0`. Cross-repo tests and
portal chart tests passed; all generated output stayed temporary.
