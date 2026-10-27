# Offline schema provenance

Kubernetes v1.36.5 definitions used by generated portal resources were extracted
without modification from `api/openapi-spec/swagger.json` at:
https://github.com/kubernetes/kubernetes/blob/v1.36.5/api/openapi-spec/swagger.json

The native Fleet revision also includes Namespace, ResourceQuota and LimitRange
Ingress, and their reachable definitions from that same Kubernetes source.

Fleet v0.16.2 GitRepo, Policy and BundleNamespaceMapping schemas were extracted
without modification from:
https://github.com/rancher/fleet/blob/v0.16.2/charts/fleet-crd/templates/crds.yaml

Fleet source commit: `14b1cd93eea8772b3abcf1b3786c254233ac149a`.
The 0.16.2 Policy schema includes `allowNamespaceCreation`; unlike the previous
0.16.0 schema, this matches the installed controller.

Both upstream projects are Apache-2.0 licensed. Only reachable native definitions
and the three used Fleet schemas are retained to keep offline checks small. The
Rancher management FleetWorkspace uses the repository's existing convention; its
schema is not included. Schema checks supplement Kubernetes CEL execution tests;
they do not replace live admission ordering, controller identity or CNI tests.
