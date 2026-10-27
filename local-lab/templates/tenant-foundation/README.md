# Shared tenant configuration templates

Edit tenant values in `../../tenant-config/tenants/`. These shared Helm templates
replace Python resource construction; do not duplicate them per tenant.

| Source | Defines |
|---|---|
| `values.yaml` | Empty default render and shared quota field ordering |
| `templates/foundation.yaml` | Projects, namespaces, quotas, limits, network boundaries |
| `files/roletemplates.yaml` | Shared Rancher workload roles |
| `files/portal/` | Portal platform RBAC, network and Fleet workspace controls |
| `templates/portal.yaml` | Portal GitRepo, values ConfigMap, admission policies/bindings |
| `templates/_portal-workload-validations.tpl` | Shared Pod/controller CEL checks |
| `templates/_portal-values.tpl` | Values shared by the ConfigMap and review preview |
| `templates/identity-plan.yaml` | Disabled Keycloak client/mapping review data |

From the repository root, with Python requirements and Helm 3.19 installed:

```sh
python3 local-lab/scripts/render-tenant-foundation.py --check
python3 local-lab/scripts/render-tenant-foundation.py --preview-application home/portal --check
```

Use `--write` instead of `--check` to refresh the corresponding output. The Python
entry point validates the catalog, selects the section, invokes only `helm template`,
and checks lifecycle/pruning before writing. Input values are data: no `tpl`, `lookup`,
remote dependencies or hooks. Helm never contacts Kubernetes in this workflow.

This is an **offline rendering chart, not an installable release**. Its default
render is empty; explicit review sections can include non-Kubernetes data. Running
Helm directly bypasses catalog validation and safe-write checks. Generated Fleet
manifests remain the deployment interface. Disabled portal previews are kept outside
Fleet; active/paused output requires an approved digest and a budgeted environment.
See [the integration guide](../../../docs/PORTAL-INTEGRATION.md) for lifecycle and
activation requirements, tests and known enforcement limits.
