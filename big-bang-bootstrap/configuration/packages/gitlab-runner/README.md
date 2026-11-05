# GitLab runner

Big Bang deploys the pinned runner chart; Flux reconciles it. Shared Ansible owns
native registration, private credential assembly/delivery and endpoint policy
preparation. Environment inputs select the GitLab origin, public CA, native actor
and project IDs, private file locations and reviewed network endpoints. There is
no separate deployment script or tenant access-sync service.

## Current state and morning handoff

Observed 2026-11-05: one manager is Ready, runner ID 1 is online/unpaused and
locked/protected, rejects untagged work and is assigned only to the private
`platform/runner-acceptance` project. Root/umbrella/runner reconciliation passed.
The init-permissions capability correction is released and deployed in v0.18.3.
The owner retry and fresh pipeline both passed Pod admission, image pulls and
container startup. Both then failed checkout: Git could not lock `//.gitconfig`
under the forced non-root UID. This is filesystem ownership, not missing RBAC.
The pending shared runner environment sets `HOME=/tmp`, an existing writable
per-container ephemeral directory, so Git global configuration avoids `/`.
Non-root UID, dropped capabilities, restricted admission and credentials remain
unchanged. An exact pinned helper-image test reproduced HOME=/ denial under UID
1001/drop ALL; HOME=/tmp passed Git global configuration and a harmless local
clone. This does not prove live GitLab checkout, TLS or artifact upload.

Both morning job Pods also scheduled on the control plane: the node is untainted
and the executor had no placement constraint. The pending shared configuration
requires both standard `node-role.kubernetes.io/control-plane` and legacy
`node-role.kubernetes.io/master` labels to be absent on eligible job nodes. It
uses required affinity, not a preference or physical hostname/storage label.
Job-variable node-selector overrides stay disabled. Providers must expose their
control-plane nodes with these standard labels, or adapt the reviewed placement
contract before use; managed clusters with no schedulable control plane need no
custom worker label. A lack of eligible capacity leaves jobs Pending rather than
falling back to a labeled control-plane node. The manager placement is unchanged. A green manager is not proof that checkout or a complete job passed.

After owner review/merge, select the verified corrected immutable source using
the existing stage-selection procedure, retain `local-gitlab-runner`, and verify
that Flux updates the manager ConfigMap with `HOME=/tmp` and rolls the Deployment. Do not edit the
live ConfigMap or generated runner config. Wait for manager/child/root readiness,
then retry the failed job in the project UI. The owner performed the morning attempts described above; no further retry or
live workaround was performed while preparing this correction.

Verify checkout and artifact upload/download, nonroot execution, dropped
capabilities and no mounted Pod API token. Record actual results; do not call the
runner accepted on render tests alone. Untagged/unprotected/unrelated-project
rejection, disallowed-image/override checks, CNI allowed/denied egress and safe
pause/drain remain separate outstanding acceptance cases. The current baseline
file does not implement all those negative cases.

## Source audit of the manual rollout

Read-only live/source comparison on 2026-11-05 found:

| Rollout operation | Durable owner / reproduction input | Verified boundary |
| --- | --- | --- |
| Foundation namespaces, identities, quota, RBAC, deny/DNS policies | `prerequisites/` via approved foundation delivery | All 12 runner foundation objects match authored fields; no additional cluster permission |
| Native runner creation/resume/unpause | `reconcile-registration.yaml`, actor/project/branch inputs and private receipt | Existing ID 1 retained; no duplicate or token reset |
| Token and Registry1 copies | GitLab `prepare-credentials.yaml`, `prepare-registry.yaml`, `deliver-credentials.yaml` with separate runner/registry profiles | Three private manifests match live immutable Secrets; delivery repeats changed zero |
| Public CA | GitLab `deliver-public-ca.yaml`, exact origin/file/hash and runner stage | Public certificate matches live immutable Secret; no signing key copied |
| Endpoint policies | GitLab `prepare-runner-network.yaml`, reviewed host routes and actual ingress/API ports | Both applied policies match generated output; physical endpoints remain private environment inputs |
| Manager/chart configuration | `candidate-values.yaml` plus selected cluster runner overlay | Live TOML and all authored Deployment spec fields match the pinned render before the pending HOME/placement correction, allowing API omission of empty strings |
| Namespace adoption fix | Big Bang exact-name Namespace post-render filter | Foundation ownership retained; no Namespace RBAC added |
| Runtime source/stage handoff | Existing Flux seed selection, source UID/ref and root path guards | Reviewed merged commit and runner root selected; release-tag reconciliation is still due |
| Test-project CI commit | `acceptance/gitlab-ci.example.yaml`, owner-reviewed private project MR | Owner merged exact reviewed file; protected branch unchanged; first job failed admission |

No untracked workload patch, credential rotation, new runner identity or relaxed
Pod policy was found in this runner audit. Native project/branch/runner objects,
credentials, generated policies and source selection are intentionally runtime
state: a checkout alone does not recreate them. Reproduction requires the approved
environment inputs and private receipt/credentials. Policy generation itself does
not deliver policies; inspect existing ownership/spec, create only absent exact
objects and read back before selecting the stage. Stop on foreign/different state.
The temporary root-password Git askpass helper was removed; no new PAT was made.
The source was deliberately selected by tested merge commit under owner approval;
reconcile to the verified release tag when available. This audit does not prove
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
