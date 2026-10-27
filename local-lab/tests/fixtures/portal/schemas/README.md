# Offline schema provenance

Kubernetes v1.36.5 definitions used by generated portal resources were extracted
without modification from `api/openapi-spec/swagger.json` at:
https://github.com/kubernetes/kubernetes/blob/v1.36.5/api/openapi-spec/swagger.json

Fleet v0.16.0 GitRepo, Policy and BundleNamespaceMapping schemas were extracted
without modification from:
https://github.com/rancher/fleet/blob/v0.16.0/charts/fleet-crd/templates/crds.yaml

Both upstream projects are Apache-2.0 licensed. Only reachable native definitions
and the three used Fleet schemas are retained to keep offline checks small. The
Rancher management FleetWorkspace uses the repository's existing convention; its
schema is not included. Schema checks supplement Kubernetes CEL execution tests;
they do not replace live admission ordering, controller identity or CNI tests.
