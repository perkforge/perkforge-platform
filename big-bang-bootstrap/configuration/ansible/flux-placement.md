# Optional Flux controller placement

Default bootstrap still renders the pinned Big Bang Flux prerequisites unchanged.
An explicit `flux_kustomize_node_selector` mapping creates a sibling overlay that
changes only kustomize-controller placement. It preserves images, resources,
arguments, permissions, service account and the existing Linux node selector.
No target hostname is built into the source. For the physical cluster the reviewed
candidate is `{'node-role.kubernetes.io/control-plane': 'true'}`. Other environments
leave the variable empty or select their own supported role label.

For an already running cluster, do not rerun bootstrap. Prepare the overlay offline,
compare the rendered Deployment against live intent, and use a separately approved
maintenance window to apply only its reviewed scheduling field. Do not apply the
entire prerequisite bundle or delete a pod to force rescheduling. Keep the explicit
placement input in the operator's environment configuration for future bootstrap.

Check matching nodes are schedulable and taints tolerated; compare requested CPU
and memory, not just utilization. The current candidate reserves the same 300m/
600Mi on a matching control-plane node and releases that reservation from a worker.
The one-replica RollingUpdate has one surge pod; expect a short leadership handoff
and possible reconciliation delay, not an application restart. Wait for readiness
and reconcile health before proceeding with logging. If scheduling fails, diagnose
and fix forward without changing resources, grants, CSI placement or unrelated apps.
No live maintenance command is run by preparing this source overlay.

## Optional Helm controller capacity profile (#442)

`flux_helm_capacity_overlay: true` additionally requires an explicit integer
`flux_helm_cpu_request_millicores` (250–900) and `flux_helm_node_selector` mapping.
These guardrails are not evidence that every allowed request is adequately sized.
Defaults remain off. The sibling capacity overlay preserves pinned vendor files
and composes with the optional kustomize-controller overlay. It changes only the
Helm controller CPU request, explicit node selector and strategy to Recreate;
replicas, memory, limits, image, arguments, probes and RBAC remain unchanged.

The observed three-day one-minute Helm-controller CPU peak was 208m (five-minute
peak 89m), versus a 900m request. A proposed 500m request retains over twice that
observed peak, but sampled history does not establish startup/recovery load safety.
The controller is bootstrap-owned, not a workload owned by cluster-root; merely
promoting a platform release will not apply this overlay. Do not replay bootstrap.

For the reviewed physical layout, select the existing worker label
`storage.perkforge.io/worker: 'true'` (with `kubernetes.io/os: linux`) and 500m.
Recreate intentionally pauses Helm reconciliation while the sole controller
terminates and starts; existing applications keep running. Its termination grace
is 60 seconds, not a completion SLA. There is no surge Pod or control-plane move.
A worker selector does not permanently pin a host: re-evaluate actual placement
and free resources immediately before a separately approved deployment.

With the exporter reduction deployed, observed worker reservations were
5785m/5740m of 6000m. Replacing the worker-2 controller at 500m would release 400m
there, leaving 660m. Worker-1 has only 215m free and cannot accommodate that
controller, so worker-2 is the only currently fitting worker after termination.
A 600m job leaves just 60m; a separate 100m runner manager cannot also fit there.
Account for actual Pod/init-container requests and overhead, memory, taints,
selectors, and other pending work; place the manager through its reviewed policy
on a different fitting node or free more capacity. This is not N+1 headroom.

Before execution, approve the exact controller replacement/pause and verify no
Helm operation is active, all existing releases are healthy, the intended worker
has enough CPU/memory, and the rendered Deployment differs from live only in
the three reviewed fields. Apply only that reviewed controller Deployment through
the bootstrap owner procedure, never the entire prerequisite bundle. Preserve
all other live metadata and do not alter grants. Afterward verify one Ready
controller on the intended worker, unchanged limits/memory/RBAC, healthy releases
and reconciliation, no new restarts or sustained throttling, then recalculate
capacity before admitting the runner.

Rollback must also avoid a surge deadlock. Stop the separately approved test job
and verify worker-2 has 660m free while the 500m controller remains. Restore the
900m request **keeping Recreate and the worker selector** for this replacement:
terminating the 500m controller frees 1160m, enough for its 900m predecessor.
Verify Ready and reconciliation before any further change. Restoring the original
RollingUpdate strategy at the same time would need 900m free for a surge Pod,
which the observed workers do not have. Removing the worker selector changes
the Pod template and can trigger another rollout or control-plane relocation;
keep it until a separately reviewed restoration has adequate surge capacity and
placement checks. Distinguish restored CPU capacity from complete policy rollback.
No live application, pause, rollback or runner activation is authorized by
preparing this source.
