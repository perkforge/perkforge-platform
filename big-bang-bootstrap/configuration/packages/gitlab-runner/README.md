# GitLab runner — gated deployment

See [the coordinated outcome](../gitlab/coordinated-outcome.md) for scope, capacity,
server-side project registration, protected credentials, isolation, outstanding
wiring and real acceptance. This directory does not register or deploy a runner.
The default-deny/DNS-only job namespace is deliberately unusable until reviewed
endpoint egress is supplied. Manager installer delegation is prepared with namespace-only object permissions;
real Helm/manager/job authorization remains unverified.
Dormant activation roots exist but none is promoted. Before selecting the runner
stage, register through the running GitLab API, assemble/deliver the separate
runner credential profile, and deliver the runner CA Secret in gitlab-runner
using its exact hostname.crt key. App credentials are an earlier independent
stage.

Local observation, 2026-11-05: runner ID 1 was registered paused/locked/protected
with the released 600-second cap. Its one-time token is safely in the created
receipt; the legacy format guard stopped before the standalone token handoff.
The routable-v1 compatibility correction must be reviewed/released before
resuming that receipt. Never re-register or reset it merely to retry this step.
No manager deployment, unpause or real job acceptance has occurred.
