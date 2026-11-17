# Portal acceptance runner staged selection

Additive overlay inherits local-identity-onboarding unchanged. Both new
reconcilers and the manager HelmRelease start suspended. No selection is deployment.

Bootstrap foundation is NOT reconciled by Flux. The owner establishes reviewed
namespaces/SA/RBAC separately; never grant namespace creation or RBAC mutation to
platform-reconciler. setup/source-ownership.yaml allows only named existing
runtime CRs/network policies and suspended manager source/release get/update/patch.
It grants no Secret access, resource creation/deletion, or RBAC escalation.
Precreate manager GitRepository/HelmRelease suspended before granting adoption.
Before runtime, establish approved exact Bao policy/role/custody and public CA,
precreated target ownership and registry pulls. Before manager, verify ESO delivery,
rendered chart, network paths and manager capacity. Native runner stays paused and
project CI disabled throughout this foundation batch.

Only runtime uses postBuild. Precreate private flux-system ConfigMap
portal-runner-endpoints with exactly RUNNER_ROUTE_HOST_CIDR and RUNNER_API_HOST_CIDR
(single-host CIDRs from approved renderer inputs). No root-wide substitution is
allowed. Physical topology stays out of Git. Current target ports are API6443 and
Traefik8443; source changes required for a different deployment. GitLab and artifact
host must share the reviewed ingress route; otherwise do not use this fixed overlay.

No blanket prune, force, token data, direct workloads, runner unpause, or pipeline
execution is introduced. Suspended child readiness is not successful deployment.
