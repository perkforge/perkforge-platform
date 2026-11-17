# Tenant acceptance preparation (inactive)

Selected first pilot: private `tenants/portal/platform-acceptance`, latest pipeline
failure/recovery using existing Portal incident destinations. No migration,
deployment credentials, CI execution, event send or offboarding in this component.

`run.sh` defaults inert. `--validate TOKEN RECEIPT INPUTS.json` validates literal
JSON and private paths without authentication/lock creation. `--project` runs the
native Ansible project foundation under a verified exclusive native lock.
`--runner` prepares only a NEW paused project runner; no activation/assignment API
is present. Existing platform runner source is unchanged. Input scope must match
selected operation. Token/receipt/input arguments contain paths, not secrets.

Required input keys: gitlab_acceptance_run (literal true), gitlab_acceptance_scope
(tenant-acceptance-project-v1 or tenant-acceptance-runner-v1),
gitlab_acceptance_context, gitlab_acceptance_origin, gitlab_acceptance_ca,
gitlab_acceptance_source_revision (40hex), gitlab_acceptance_group_receipt and
gitlab_acceptance_actor_id (positive native ID). Runner also requires
 gitlab_acceptance_project_receipt and gitlab_acceptance_runner_directory.
No additional vars, templates/lookups, namespace/path/tag/image overrides accepted.
Use canonical context and protected source-owned group receipt, not untrusted UI
input. Selected source revision cannot silently change an existing project receipt.

Both operations require the source-established parent Owner group-token writer:
exact active nonadmin bot ID, token-self active/not revoked/exact `api` scope,
expiry strictly after the current UTC date, exact parent direct Owner membership
and parent access-token ID/user/scope/expiry readback. This token has authority
across the tenants subtree, not only this selected project. Native API permission
checks still govern each operation; no fallback actor or scope changes. The pinned
19.4.2 global API `api` scope also covers the user/runners route; its additional
`create_runner` scope is an alternative, not a silently added requirement.

Project setup rechecks exact private parent/group and active nonadmin operator,
refuses foreign existing paths, writes intent before POST and exact ID afterward.
CI/shared/group runners/AutoDevOps remain disabled. An uncertain POST or incomplete
verification is MANUAL RECOVERY, not a blind repeat/adoption/delete. `project-ready`
means only project preparation, not source seed, branch, runner or CI readiness.
The source requires native version19.4.2 (or19.4.2-ee). Actual field/permission
compatibility remains a live gate; synthetic TLS is not proof. Initial project
default_branch is null; seeding/protection is a separate reviewed operation.
Receipts use native Ansible atomic replacement, not a proven power-loss-durable
transaction; preserve uncertain effects for manual recovery.

Runner preparation requires that separately reviewed repository seeding and main
protection already exist while CI remains disabled. It checks exact private
project namespace/parent, no other assigned runner, protected main/no force push,
new runner exact project-only binding, unique derived tag, locked, no untagged,
ref_protected, paused, timeout600. Its one-time authentication token is saved only
in its private runner receipt/token. This is the existing custody pattern, not
OpenBao delivery or an authorized credential mint. No runner1 expansion.

Future batch: reviewed initial seed with source/native commit hashes; separate
manager/job namespace and API-free job SA; restricted images/nonroot/zero caps;
exact GitLab/registry/artifact egress; scoped Bao/ESO record; resource/I/O preflight;
manager isolation; explicit runner/CI activation and bounded manual success,
labeled failure, recovery. Big Bang/Flux remains manager owner. Do not directly
apply workloads. Token expiry/custody and actor permissions must be checked just
before approved native setup. No broad human/admin token fallback or silent remint.

Smoke source should test sanitized context/role fixtures, nonroot/no token/zero
caps and a tiny deterministic artifact, with an allowlisted success/failure test
parameter. No arbitrary shell/environment dump/package install/deployment. Latest
incident semantics intentionally do not promise every between-poll transition.

Run: `PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest security.test_tenant_acceptance_preparation -v`.

Source contract references: pinned `lib/api/user_runners.rb`, `lib/api/api_guard.rb`
and `lib/api/api.rb` at GitLab19.4.2; existing platform membership writer checks
provide the parent-bot provenance pattern. No new actor creation is in this adapter.

## Bounded seed and main protection (inactive)

`run.sh --seed TOKEN SEED_RECEIPT INPUTS.json` uses the same literal/private input
and native lock checks, with scope `tenant-acceptance-seed-v1` and required
`gitlab_acceptance_project_receipt`. All other common inputs retain their meaning.
The existing project receipt is read-only; use a separate private seed receipt.
Only source-owned `.gitlab-ci.yml`, `README.md` and `smoke.py` are created in one
native commits API call. Source revision and exact rendered content hashes bind
the seed receipt. There is no caller content, author-identity override, repo import,
file update/delete or force push. A preexisting branch/protection without this
helper's final receipt is refused, including a project seeded by another actor.

The project must remain private, empty initially, with CI/shared/group runners and
AutoDevOps disabled. The seed commit also uses `[skip ci]`; the fixed workflow
permits only a later manual web pipeline on protected main. Its single smoke
outcome is `success` or `failure`, never a shell argument. The pinned approved
image runs only the fixed smoke script: nonroot, zero effective capabilities,
no Kubernetes token at the standard mount, one exclusive tiny fixed artifact.
These are smoke checks, not proof arbitrary credentials are absent or the runner
is isolated. No image is pulled or pipeline executed by this setup helper.

After exact native commit/tree/file/default-branch readback, main is protected
with push/merge access level40 (Maintainers, including inherited Owners) and force
push disabled. An automatically created default-main rule is accepted only after
this helper's own verified seed and only when it exactly matches the requested
non-inherited role-only policy. Foreign, wildcard, user/group/deploy-key access
is not repaired. If no rule exists, one POST creates it; no PATCH/delete is used.
Fresh commit and CI-disabled readbacks precede `SeedReady`. Repeating a final owned
receipt performs only reads and requires identical commit/content/protection ID.

Intent precedes either native POST. Lost response, incomplete verification or
protection failure leaves pending evidence and requires manual recovery, never
blind retry/adoption or credential remint. Local Ansible atomic writes are not a
power-loss-durable transaction; native concurrent writers cannot be locked by the
local receipt lock. Native permission checks and final readbacks narrow effects,
not a claim of cross-service atomicity. Activate only under an exact approved
project/source/protection batch; runner preparation/activation and CI runs remain
separate. API compatibility must be verified against the installed19.4.2 service.
Pinned source: `lib/api/commits.rb` and `lib/api/protected_branches.rb` at
https://gitlab.com/gitlab-org/gitlab/-/tree/v19.4.2-ee.

Synthetic test: `PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest security.test_tenant_acceptance_seed -v`.
It proves API/guard behavior against a local HTTPS fixture, not native GitLab,
runner, CI, delivery or recipient access acceptance.

## Pinned current-user representation

For authenticated unfiltered `GET /api/v4/user` only, GitLab19.4.2 selects
`UserWithAdmin` when `current_user.admin?` is true and `UserPublic` otherwise.
The former exposes `is_admin` unconditionally; the latter omits it. Therefore
this exact endpoint on the already checked version accepts absence or literal
`false`, and rejects true/null/string/numeric values. This is not permission to
treat omitted admin fields on `/users/:id`, lists, another version or another
provider as nonadmin. Active bot/native ID, token-self/api/expiry, and exact parent
Owner/token ownership checks remain required before any write.

Pinned native source: [current-user route](https://gitlab.com/gitlab-org/gitlab/-/blob/v19.4.2-ee/lib/api/users.rb),
[admin entity](https://gitlab.com/gitlab-org/gitlab/-/blob/v19.4.2-ee/lib/api/entities/user_with_admin.rb),
[public entity](https://gitlab.com/gitlab-org/gitlab/-/blob/v19.4.2-ee/lib/api/entities/user_public.rb).
Synthetic TLS uses the native absent-field representation; focused actual-Ansible
assertions cover explicit false and malformed/privileged values. No native setup
or new authority is implied by this compatibility correction.
