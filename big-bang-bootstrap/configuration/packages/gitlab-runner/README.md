# GitLab runner

Big Bang deploys the pinned runner chart; Flux reconciles it. Shared Ansible owns
native registration, private credential assembly/delivery and endpoint policy
preparation. Environment inputs select the GitLab origin, public CA, native actor
and project IDs, private file locations and reviewed network endpoints. There is
no separate deployment script or tenant access-sync service.

## Current baseline acceptance

Observed 2026-11-05 15:15 UTC: [pipeline 3](https://gitlab.perkforge.home.arpa/platform/runner-acceptance/-/pipelines/3)
and [job 4](https://gitlab.perkforge.home.arpa/platform/runner-acceptance/-/jobs/4)
succeeded on worker-2 with the original runner ID 1. Main commit 8ad6c47d was
checked out, all script checks passed, and artifact upload returned 201. An
independent download verified the exact expected acceptance/result.txt bytes
(SHA-256 `25965b80085da91397bb9733abba68711dedb6a5e75e984e39085769ff940b74`).
The checks establish non-root execution, no default mounted Pod API token and
zero effective capabilities. The job Pod was cleaned up normally. Manager is
Ready without restarts and root/umbrella/runner reconciliation is healthy.

The earlier init-permissions admission and non-root //.gitconfig errors are
superseded by this real result. Shared source supplies drop ALL for init/build/
helper, HOME=/tmp and required node affinity excluding standard control-plane/
legacy master labels. This avoids physical hostnames/storage-label coupling;
providers exposing control-plane nodes must supply standard role labels or adapt
the reviewed contract before use. No eligible worker means Pending, not fallback
to a labeled control-plane node. Node-selector overrides remain disabled. Manager
placement is separate from job placement. No root/chmod workaround or broader
RBAC was used. Root recovery and existing project/branch protection remain intact.

This completes the basic protected-job/checkout/artifact outcome. It does not
prove every untagged/unprotected/unrelated-project denial, disallowed image or
override case, CNI allowed/denied egress, safe pause/drain or independent restore.
Those negative/recovery cases remain outstanding; the baseline CI file does not
implement them. Tenant runner enrollment and tenant access synchronization remain
deferred. Preserve the existing runner receipt/token on every reconciliation.

## Source audit of the manual rollout

Read-only live/source comparison on 2026-11-05 found:

| Rollout operation | Durable owner / reproduction input | Verified boundary |
| --- | --- | --- |
| Foundation namespaces, identities, quota, RBAC, deny/DNS policies | `prerequisites/` via approved foundation delivery | All 12 runner foundation objects match authored fields; no additional cluster permission |
| Native runner creation/resume/unpause | `reconcile-registration.yaml`, actor/project/branch inputs and private receipt | Existing ID 1 retained; no duplicate or token reset |
| Token and Registry1 copies | GitLab `prepare-credentials.yaml`, `prepare-registry.yaml`, `deliver-credentials.yaml` with separate runner/registry profiles | Three private manifests match live immutable Secrets; delivery repeats changed zero |
| Public CA | GitLab `deliver-public-ca.yaml`, exact origin/file/hash and runner stage | Public certificate matches live immutable Secret; no signing key copied |
| Endpoint policies | GitLab `prepare-runner-network.yaml`, reviewed host routes and actual ingress/API ports | Both applied policies match generated output; physical endpoints remain private environment inputs |
| Manager/chart configuration | `candidate-values.yaml` plus selected cluster runner overlay | Live TOML and all authored Deployment spec fields match the pinned render after the reviewed HOME/placement correction, allowing API omission of empty strings |
| Namespace adoption fix | Big Bang exact-name Namespace post-render filter | Foundation ownership retained; no Namespace RBAC added |
| Runtime source/stage handoff | Existing Flux seed selection, source UID/ref and root path guards | Published v0.18.4 and runner root selected; tagged source/root Ready, accepted manager unchanged |
| Test-project CI commit | `acceptance/gitlab-ci.example.yaml`, owner-reviewed private project MR | Owner merged exact reviewed file; protected branch unchanged; first job failed admission |

No untracked workload patch, credential rotation, new runner identity or relaxed
Pod policy was found in this runner audit. Native project/branch/runner objects,
credentials, generated policies and source selection are intentionally runtime
state: a checkout alone does not recreate them. Reproduction requires the approved
environment inputs and private receipt/credentials. Policy generation itself does
not deliver policies; inspect existing ownership/spec, create only absent exact
objects and read back before selecting the stage. Stop on foreign/different state.
The temporary root-password Git askpass helper was removed; no new PAT was made.
The source was initially selected by tested merge commit under owner approval;
it is now reconciled to verified published v0.18.4 with the accepted manager Pod
unchanged and zero restarts. This audit does not prove
independent restore, broad network isolation or every prior app operation.

## Adding or recovering a runner

1. Choose the trusted private platform project and native actor/project IDs.
   Protect its default branch against force pushes. Obtain explicit approval for
   new persistent credentials/access; never reuse a tenant identity implicitly.
2. Supply the existing registration playbook with operation `prepare`, scope
   `gitlab-runner-prepare-v1`, verified recovery, HTTPS origin/CA, project path and
   branch, API credential file and a unique owner-only private directory. The
   current contract accepts `platform/<project>` and the pinned server version;
   it is not arbitrary tenant enrollment.
3. Prepare creates paused, locked, protected and tagged, with untagged work off
   and a 600-second cap. Keep the durable creation receipt and one-time token.
   On retry use the same receipt/directory; uncertain creation must stop. Never
   re-register/reset to recover a local validation or delivery error.
4. Assemble/deliver the runner profile, exact-host public CA and separately
   approved Registry1 copies to manager/job namespaces. Reuse matching immutable
   Secrets; do not silently overwrite them or regenerate application credentials.
5. Prepare/review/deliver endpoint policies, verify foundation permissions and
   job quota, then select the existing reviewed Big Bang runner stage. Keep
   autoRegister off, namespace creation off and the chart pinned.
6. Verify manager readiness and authenticated contact for the expected native
   runner ID. Use operation `activate`, scope `gitlab-runner-activate-v1`, with
   actual manager/recovery verification. A registration response alone is not
   manager verification. Repeat should report zero changes.
7. Run the reviewed protected-branch baseline and the separate negative cases;
   preserve the receipt, project IDs and credential custody in owner-only records.

The shipped stage deploys one manager for one registered project runner. Increasing
manager replicas does not create an independent runner or tenant boundary. A
second independent project/tenant runner needs its own reviewed source instance,
identity/receipt, Secret references, namespace/RBAC/quota/policy boundaries and
activation approval; that multi-instance feature is not implemented here. Do not
reuse this single stage to overwrite the existing token or adopt another runner.

For maintenance use operation `pause`, scope `gitlab-runner-pause-v1`, then verify
no running jobs/Pods before changing the manager. Pause does not cancel jobs,
revoke tokens or delete identities/data. Keep original data services and recovery
access separate. See [coordinated acceptance](../gitlab/sso-runner-acceptance.md).
