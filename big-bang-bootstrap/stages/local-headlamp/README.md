# Headlamp first package stage

Selects only Big Bang → Headlamp, using the reviewed namespace/installer RBAC and private pull-secret wiring. Initial service is private ClusterIP; no ingress, identity user grants, storage, OpenBao or tenant enrollment. Chart/Flux versions remain pinned.

Configure the worker-node placeholder or reviewed placement policy in `values.yaml`, inspect the complete render and actual cluster headroom, then obtain approval for `ansible/headlamp-foundation.yaml` and named registry Secret delivery. Seed/root activation is separate. Keep UI service-account grants empty and unsafe token fallback disabled.

Verify source/HelmRelease and Pod readiness, exact image, Service endpoints and HTTP health. Record events, failures and resource observations locally without credentials. On instability suspend this stage before scaling its new workload to zero; do not uninstall existing services or delete data.
