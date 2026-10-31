# Add or configure a Big Bang application

## Choose its owner and source

The pinned umbrella is Big Bang 3.35.1 (`big-bang-bootstrap/configuration/packages/bigbang/source.yaml`). Inspect that release's actual catalog/schema first. Built-in packages such as Headlamp, Keycloak and Mimir use `addons.<name>` here; other catalog components may have different keys. Custom packages use Big Bang's `packages` mechanism, not a competing standalone release owner.

Current `clusters/local/kustomization.yaml` selects Headlamp and Keycloak. `configuration/packages/openbao/` is an unselected custom-package definition referencing official chart 0.30.6; its ConfigMap feeds the umbrella, which generates the source/release. It does not install everywhere. Longhorn and Rancher are also optional, unselected inputs with child releases explicitly suspended; see their package READMEs. Keep absent packages absent: a nonempty custom-package map can cause Big Bang to generate a wrapper source even when an entry is disabled.

## Select and supply values

1. For a target-only override, edit `big-bang-bootstrap/clusters/<name>/values.yaml`. For reusable authored package settings, use `configuration/packages/<name>/values.yaml` and a small `kustomization.yaml` generating a named ConfigMap in namespace bigbang.
2. Select that package directory in the target's `kustomization.yaml`. Wire its ConfigMap/key into `configuration/packages/bigbang/release.yaml` valuesFrom if it is a new input. Merely adding a file does not make Helm consume it. Keep tenant apps in enrollment/application Git, not privileged platform packages.
3. Keep pins explicit and use the existing release process. No generated child YAML or vendored charts in deployment source.

For example, this is the verified umbrella key for Mimir 6.2.1-bb.1:

```yaml
# clusters/<name>/values.yaml — selection example, not activation approval
addons:
  mimir:
    enabled: true
```

This overrides its disabled shared value. It does not provide reviewed storage/object-store, resource sizing, registry access, network/metrics ingestion or installer permissions. Kafka ingest is optional. Do not enable Mimir on the current cluster as part of reading this guide.

## Understand merge order

`clusters/<name>/kustomization.yaml` generates `values-cluster` from `values.yaml`. An alternate filename can retain the expected key with `files: [values.yaml=custom-values.yaml]`.

The release currently merges: chart defaults → values-shared → values-headlamp/values.yaml → values-headlamp/oidc.yaml → optional values-rancher → optional values-longhorn → optional values-openbao → optional values-keycloak/values.yaml → optional values-keycloak/database.yaml → values-provider → values-impact → values-cluster. Later conflicts win; lists replace. There is no inline spec.values or automatic environment layer. Profile invariants still need validation against late overrides. A domain change does not automatically rewrite explicit routes, issuer/callbacks or certificates.

## Review prerequisites and validate

Namespaces, scoped installer RBAC and retained storage are in `configuration/packages/{bigbang,headlamp,keycloak}/prerequisites/`. Ansible applies common Big Bang then selected package resources. The current installers cannot create arbitrary namespaces or install every catalog app; new packages require reviewed prerequisites and tests, not broader wildcard permissions. Keep credentials external and approve delivery to named Secrets separately. Reuse package NetworkPolicies/mesh integrations after inspecting their render before adding custom policies.

```sh
kubectl kustomize big-bang-bootstrap/clusters/local
ansible-playbook -i big-bang-bootstrap/configuration/ansible/inventory.yaml big-bang-bootstrap/configuration/ansible/headlamp-prerequisites.yaml --syntax-check
```

Kustomize only assembles umbrella inputs. Use the [configuration/render suite](../../big-bang-bootstrap/tests/README.md) with pinned sources and verified dependency checkouts for the full child inventory, images, requests/limits/PVCs, permission coverage and omitted packages. Update checksummed test fixtures when deliberately changing chart pins. Existing selected-package tests reject an unreviewed Mimir addition: extend them with its actual child render and prerequisites first. Budget infrastructure/Rancher systems and startup peaks separately. Offline renders do not prove startup, persistence or access.

Longhorn uses the official charts Git tag; Rancher declares one explicit upstream
HelmRepository beside its values input to avoid replacing another custom package's
helmRepositories list. Big Bang remains the single HelmRelease owner. Rancher's
required external bootstrap values Secret is appended by the outer post-renderer;
never put bootstrap credentials into a tracked values file.
