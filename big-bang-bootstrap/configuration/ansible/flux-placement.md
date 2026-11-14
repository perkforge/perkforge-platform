# Optional Flux controller placement

Default bootstrap still renders the pinned Big Bang Flux prerequisites unchanged.
An explicit `flux_kustomize_node_selector` mapping creates a sibling overlay that
changes only kustomize-controller placement. It preserves images, resources,
arguments, permissions, service account and the existing Linux node selector.
No target hostname is built into the source. For the physical cluster the reviewed
candidate is `{'node-role.kubernetes.io/control-plane': ''}`. Other environments
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
