# GitLab runner — inactive coordinated candidate

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
stage. No deployment or registration has occurred against the live cluster.

The default-off [runner-stage activation playbook](../../ansible/activate-gitlab-runner.yaml)
selects this concrete configuration through the released local runner root after
checking source/cluster identity and privately prepared credentials/trust. It changes
only the root path with optimistic concurrency guards; native registration and
unpausing remain separate reviewed operations. See the [combined SSO/runner
acceptance](../gitlab/sso-runner-acceptance.md) for exact inputs and live gates.
