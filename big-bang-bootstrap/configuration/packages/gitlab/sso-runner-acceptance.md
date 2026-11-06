# GitLab named SSO and protected runner completion

This is one coordinated acceptance outcome using the existing modular adapters.
No new tenant access-sync service is implemented. Existing bounded membership
helpers remain unselected; automated tenant lifecycle and full offboarding are
future work. Source review is not approval for live identities, grants or tokens.

## Current evidence and prerequisites

The owner reported a successful independent root login on 2026-11-05. Keep root
outside OIDC and retain its recovery password in the owner-run encrypted USB
workflow. Export selection includes the existing root recovery password; only an
owner-local encrypted export and byte comparison prove archive coverage. Never
print passwords, archive passphrases, PATs or runner tokens in review evidence.
The webservice memory correction was promoted and owner root/named SSO logins were reported. Independent restore and real non-admin GitLab denial remain unverified.

## Named SSO — owner-approved live batch

1. Inspect the existing dedicated client, provider Secret, exact callback and CA.
   Reuse the existing secret; do not rotate or recreate it. The selected app root
   already includes the blocked-signup OmniAuth overlay. Verify rendered/live
   configuration before making another chart change.
2. After independent recovery and realm MFA checks, use `reconcile-client.yaml`
   with its explicit activate scope. It grants no GitLab or realm roles.
3. Corey signs in through Keycloak with fresh MFA. A newly created account stays
   blocked. From a separate root session, inspect its exact numeric GitLab ID and
   `openid_connect` identity `extern_uid` against the verified Keycloak subject.
   Email or group membership alone must never select an account to approve/link.
4. Only with explicit named-account authority approval, approve that exact user
   and assign the native instance-admin flag in GitLab. Preserve root and all
   other users. `verification/native_access.py::verify_platform_admin` checks GET
   evidence for the exact active named administrator; it performs no mutation and
   cannot prove browser MFA. Corey then repeats fresh login and opens Admin Area.
5. Test an independently approved non-admin/blocked identity for denied instance
   administration. If no such identity is authorized, record the test as pending.
   Never impersonate Corey or invent a successful denial result.

Rollback disables only the owned OIDC client/provider integration, retains local
recovery and existing identities/projects, and separately assesses issued sessions
and API tokens. Disabling a client is not immediate universal token revocation.

## One protected platform runner — separately approved live batch

1. Corey selects one private `platform/<project>` acceptance project and exact
   native actor/project IDs. Protect its default branch and tag; disallow force
   pushes. Creating the project, a scoped API credential and persistent registry
   access each needs explicit live approval. No broad shared/tenant runner.
2. Use `reconcile-registration.yaml` prepare: create one paused, locked protected
   project runner, tagged `perkforge-platform`, rejecting untagged jobs. Preserve
   its private receipt and one-time token. An uncertain POST stops, never retries.
3. Use existing runner-profile credential assembly/delivery, exact-host public CA
   delivery, approved namespace pull credentials and reviewed endpoint egress.
   Do not regenerate application credentials or relax TLS/default-deny to proceed.
4. Select the released `local-gitlab-runner` stage through the existing reviewed
   source/stage-selection workflow, after checking its diff retains
   the stable app, SSO and data services. Verify manager identity, API permissions,
   CA and readiness while the native runner is paused; then explicitly activate.
5. Commit only `acceptance/gitlab-ci.example.yaml` to the approved protected
   project through its reviewed workflow. Verify checkout and artifact upload/
   download plus nonroot, dropped capabilities and absent Pod API token.
6. Verify untagged/unprotected jobs cannot use this runner, wrong image/namespace
   overrides are denied and unrelated tenant projects cannot assign it. Observe
   actual CNI allowed/denied egress; a successful job alone proves no isolation.

Pause/drain is the first rollback step; it does not cancel running jobs, revoke
its authentication token or delete identity/data. Verify jobs and Pods are drained
before a separately approved manager change. Preserve original data services.

Completion requires recorded real named MFA/admin access and actual protected
job/denial evidence. Offline fixtures demonstrate guards, not live compatibility.

## Existing Big Bang configuration, without another deployment mechanism

`clusters/local-gitlab-runner/values.yaml` already sets
`addons.gitlabRunner.enabled: true`, `flux.suspend: false` and the exact GitLab
HTTPS URL. Its root inherits the app/SSO/data roots and appends that final values
overlay. The candidate pins chart `0.91.2-bb.3`, one manager and concurrency one,
the manager identity, restricted job namespace, exact build/helper images,
private-registry references and the public CA Secret. Big Bang deploys that chart;
Flux owns its reconciliation. No additional activation playbook or selector is
needed. This MR does not claim to introduce already-merged runner configuration,
and its merge is not a prerequisite to use that existing stage.

Use the established reviewed stage-selection procedure after registration/token,
CA, registry and network preparation. Native registration necessarily calls the
GitLab API to create a project runner identity and receive its one-time token.
The existing adapter handles that operation with a private receipt and uncertain
mutation guard. It does not require a new Kubernetes deployment mechanism.

Remaining live inputs: the approved private project/actor IDs and project path,
a privately supplied authorized API credential, approved pull-credential copies
and endpoint egress. Named account approval/native authority and fresh browser
MFA are owner actions. Merge does not supply or approve those inputs. Keep all
tokens and credentials outside Git, and verify actual function after deployment.

## Current runner execution evidence

Owner-triggered pipeline 3/job 4 passed on worker-2 at 2026-11-05 15:15 UTC using
existing runner ID 1 and protected main commit 8ad6c47d. Checkout, non-root/no-Pod-
API-token/zero-effective-capability assertions and artifact upload passed. The
artifact was independently downloaded and its exact expected bytes verified.
The source-owned init, HOME and placement fixes are active; no permission or
credential expansion was required. See the [runner guide](../gitlab-runner/README.md).
This establishes the basic protected-runner outcome, not the separate negative
runner/CNI cases, independent restore or real non-admin GitLab denial.
