# Home portal — catalog-owned application

Home is the existing protected household tenant. Portal is
`applications.portal` in [`tenants/home.yaml`](../local-lab/tenant-config/tenants/home.yaml),
alongside the existing Nextcloud environment. It is not another tenant or Project.
The current portal lifecycle is **disabled**, with no approved image or namespace
allocation. Merging this change emits no portal objects into active Fleet output
and leaves all 16 existing generated foundation files byte-for-byte unchanged.

## One source of truth and renderer

- `local-lab/tenant-config/tenants.yaml` remains the explicit tenant index.
- `tenants/home.yaml` owns portal lifecycle, issuer/client/audience, exact origin,
  Secret name/key, service identities, immutable tenant revision and image approval.
  Home groups and the catalog cluster version are inherited, not independently stored.
  No secret values, admin credentials or tokens belong in the catalog.
- `local-lab/scripts/render-tenant-foundation.py` validates the complete catalog and
  owns ordinary active rendering, writing/checking, and explicit application previews.
  `portal_application.py` is a pure helper, with no CLI, separate input file, apply
  command, network client or credential generation. Other catalog consumers retain
  their existing behavior; this does not run Keycloak provisioning.
- `local-lab/templates/tenant-applications/portal/` contains platform renderer inputs.
- `local-lab/tenant-config/generated/home/portal/` contains committed **review
  artifacts**, regenerated with `--preview-application home/portal`. They are outside
  active Fleet paths and never loaded as tenant inputs. These are outputs, not a
  second configuration source or activation switch.
- For a future explicitly budgeted active/paused portal, ordinary foundation output
  includes its namespace/quota/restricted Pod Security in Home and application
  controls at `tenants/home/applications/portal/resources.yaml` within the existing
  foundation bundle. Existing protected-namespace default-deny owns that policy;
  the app helper adds DNS only, without duplicate policy ownership.

The old optional directory, standalone contract/renderer and proposal entry are
retired. The tenant repository still owns only application Helm/Fleet definitions.
Its approved ConfigMap reference is unchanged by this refactor.

## Application lifecycle: preservation before convenience

This is an application lifecycle under Home; it does not repurpose the older
whole-tenant lifecycle metadata or disable Home/Nextcloud.

| State | Meaning | Ordinary foundation output |
|---|---|---|
| `disabled` | Never provisioned; no allocated portal namespace | No portal resources |
| `active` | Explicitly reviewed application with approved digest and budgeted Home namespace | All controls/configuration; chart enabled, immutable tenant GitRepo unpaused |
| `paused` | Retain a provisioned application while stopping Git reconciliation | Same resource identities and enabled configuration; GitRepo paused; workloads are **not** scaled down or deleted |

Active/paused require a real-format reviewed image digest and an environment
allocation for `tenant-home-portal` that fits Home's aggregate budget. No allocation
or budget increase is included in the current catalog. Unknown states and a
`disabled` entry with an allocated namespace are rejected. A previously generated
application cannot be removed simply by deleting its entry or switching to disabled:
the writer refuses stale application files and removal of application resource
identities, **before any writes**. This covers directory and legacy combined-file
outputs. Use paused to preserve it; decommission/data deletion requires separate
review and is intentionally not implemented as a generic switch.

This protects the generator's tracked output, not arbitrary manual Git edits,
out-of-band `kubectl`, controllers or cluster administrators. It cannot infer live
history when generated inventory was discarded. Before any transition, inspect
actual resources and ownership under separately authorized operational review.

## Identity wiring and runtime checks

The application preview includes an immutable platform-owned ConfigMap named
`tenant-home-portal/portal-platform-values`, containing non-secret Helm values.
Tenant Fleet `helm.valuesFrom` reads its `values.yaml` key; the scoped deployer has
only named ConfigMap **get**, not mutation. The chart maps values to `OIDC_ISSUER`,
`OIDC_CLIENT_ID`, `OIDC_AUDIENCE`, origin and the operator-managed
`portal-oidc/client-secret` reference. No Secret object/value is generated.

`generated/home/portal/identity-plan.json` is review data for disabled confidential
browser/API clients, exact callback, S256, five-minute tokens, audience/group/role
mappers and required limited role-scope mapping. It is not a realm backup or an
apply operation. No group members are granted roles automatically and no client,
key or secret is created. Current Keycloak is HTTP/paused; trusted HTTPS remains
separately authorized future work.

Helm values precedence is not security. Generated native admission policies check
actual Deployment/ReplicaSet templates and final Pods, including ephemeral-container
updates: exact identity environment and Secret reference, unique env entries,
platform runtime SA without token automount, one approved image/container, and
restricted security settings. They reject envFrom, command/args/lifecycle/exec-probe
injection, init/sidecar/ephemeral containers, volumes/token projection, other secrets,
host access, interactive modes and custom DNS. Service exposure stays ClusterIP.
The deployer write surface is restricted to Deployment/Service in the exact namespace;
scale/exec/token subresources and security-control writes are denied.

Policies select `request.namespace`, not tenant-editable labels. The deployer policy
also matches its principal across namespaces. No controller-Pod bypass is added.
With the current missing image, preview image validation is literally `false`;
there is no fake deployable digest. Tests use a synthetic digest in memory only.

An app can read its own low-privilege client secret; compromised approved code or
platform/node administrators can leak it. Configuration does not establish trust
in arbitrary tenant code. Future privileged APIs must independently validate
issuer/signature/audience/client, roles, tenant/resource access and the operation
outside tenant-editable trust configuration. No Keycloak/GitLab admin credentials
or capabilities are provided here.

## Offline verification and candidate-pair testing

Install the pinned `local-lab/tests/portal-cel/requirements.txt` in an isolated Python
environment; use Go1.27.3 and Helm3.19. No container, live provider or cluster is needed.

```sh
python3 local-lab/scripts/render-tenant-foundation.py --check
python3 local-lab/scripts/render-tenant-foundation.py --preview-application home/portal --check
python3 -m unittest discover -s local-lab/tests -v
python3 local-lab/tests/validate_portal_schemas.py
(cd local-lab/tests/portal-cel && GOMAXPROCS=1 GOMEMLIMIT=256MiB go test -p=1 ./...)
```

Use `--preview-application home/portal --write` to refresh review artifacts. Ordinary
`--write` continues to own the existing foundation bundle; it emits no disabled
portal resources. Preview destinations under active Fleet paths are rejected.

CI checks the platform feature candidate and the **exact tenant SHA from Home's
application entry**, not main or a moving tenant branch. With separate review checkouts:

```sh
tenant_pin=$(python3 -c 'import sys; sys.path.insert(0,"local-lab/scripts"); import portal_application; print(portal_application.load_contract()["tenantRevision"])')
git clone --no-checkout https://github.com/perkforge/perkforge-tenant-portal.git ../tenant-review
git -C ../tenant-review checkout --detach "$tenant_pin"
export PORTAL_CHART_DIR="$(cd ../tenant-review && pwd)/bundles/portal/chart"
(cd local-lab/tests/portal-cel && GOMAXPROCS=1 GOMEMLIMIT=256MiB go test -p=1 -count=1 ./...)
```

The Go suite executes generated CEL using Kubernetes1.36.5 admission libraries,
including real-chart negative overrides when PORTAL_CHART_DIR is supplied. Python
tests cover catalog compatibility, inherited ownership, active/paused identity
retention and no-prune behavior. Native/Fleet schemas are pinned to Kubernetes1.36.5
and Fleet0.16.0 with unknown-field rejection and IntOrString handling. These are
**test targets**, not a fresh assertion of installed versions. Rancher FleetWorkspace
schema, live API defaulting/type-check status, webhook order, CNI and controller
behavior remain unverified. No test requires merging or enabling live Fleet.

## Fleet semantics and remaining activation gates

Fleet0.16 [`install.go`](https://github.com/rancher/fleet/blob/v0.16.0/internal/helmdeployer/install.go)
loads explicit ConfigMap namespace/key through the configured deployment client;
missing object/key fails. [`getCfg`](https://github.com/rancher/fleet/blob/v0.16.0/internal/helmdeployer/deployer.go)
uses the requested deployer identity. Template-only mode skips cluster lookups, so
offline Helm checks feed the same generated values explicitly. Source precedence
can be changed by tenant code; admission supplies enforcement. Fleet0.16 uses Helm4
internally; installed Fleet/Helm behavior must be checked before activation.

**Helm release-Secret storage remains unresolved.** The deployer gets no Secret
rights; do not add broad Secret access to make installation succeed. Resolve and
verify release storage/impersonation through platform review. The older
`allowNamespaceCreation` field is absent from Fleet0.16's schema; new output relies
on actual RBAC/admission, and existing Nextcloud configuration is untouched.

Before activating: review fresh capacity and a Home budget/allocation; approve and
scan a real image; verify installed APIs and admission denial after all mutating
webhooks; configure trusted HTTPS Keycloak/client/role-scope/member mappings and
secure secret delivery; approve exact internal TLS ingress/identity egress (current
policies allow DNS only); resolve Fleet storage and test CNI/controller boundaries.
Install/verify controls before secrets/workloads. A catalog active transition is a
future explicit deployment decision, not something performed by this change.
