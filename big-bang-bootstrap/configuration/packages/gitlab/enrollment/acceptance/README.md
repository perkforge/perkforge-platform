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

Project setup rechecks exact private parent/group and active nonadmin operator,
refuses foreign existing paths, writes intent before POST and exact ID afterward.
CI/shared/group runners/AutoDevOps remain disabled. An uncertain POST or incomplete
verification is MANUAL RECOVERY, not a blind repeat/adoption/delete. `project-ready`
means only project preparation, not source seed, branch, runner or CI readiness.
Native version/field compatibility remains a live gate; synthetic TLS is not proof.

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
