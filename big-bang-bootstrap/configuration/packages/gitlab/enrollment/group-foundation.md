# Exact tenant group foundation step

`ensure-groups.yaml` is one reusable platform-owned enrollment step for #334,
not the enrollment controller, user lifecycle or event processor. Default and
check mode read no credentials, contact no APIs and write no receipt. An explicit
run can create only `tenants` and `tenants/<canonical-context>` as private groups,
with native access requests disabled. It never creates projects/users, links
accounts, grants memberships, changes existing group settings, deletes groups or
runs pipelines. Native GitLab 19.4.2/19.4.2-ee is required.

## Protected executor inputs

- `gitlab_group_run: true` and scope `gitlab-enrollment-group-foundation-v1`.
- Literal canonical `gitlab_group_context` from the reviewed platform enrollment,
  not a request payload or inferred app folder.
- `gitlab_group_source_revision`: exact lowercase 40-character reviewed enrollment
  revision. This is supplied provenance, not a signature or ownership attestation.
- `gitlab_native_origin`, verified public CA and existing private token file.
  HTTPS only, no redirects/proxy/netrc, no token in arguments or output.
- `gitlab_group_receipt_file`: owner-only regular0600 file in a canonical private0700
  directory. Never supply untrusted browser receipt bytes. Use the source `run-groups.sh --apply TOKEN_FILE RECEIPT_FILE INPUTS_FILE`
  launcher: native nonblocking flock spans the complete Ansible transaction.
  The Linux verifier checks that the no-fork lock-owning PID is an ancestor
  of this invocation and owns the exact inode in `/proc/locks`, with its native
  descriptor still open. Observing another process holding a lock is insufficient;
  copied-owner-PID direct invocations fail. Direct live play invocation is refused. This is a local
  executor lock, not distributed locking across multiple machines.
- `gitlab_group_expected_parent_id`: an explicitly inspected existing `tenants`
  parent ID, or zero when absent. Existing unmatched parent/child paths fail closed.
- `gitlab_group_allow_parent_create: false` by default. Missing parent creation
  requires its own explicit reviewed bootstrap authority; a token scoped to a
  nonexistent parent cannot create that parent. No new credential is created here.

Complete ancestry and leaves are checked for ownership, write modes and symlinks;
a root-owned sticky temporary ancestor is allowed only above a private owner directory.
No existing path is chmodded. The lock contains no secrets.

`run-groups.sh --validate TOKEN_FILE RECEIPT_FILE INPUTS_FILE` validates the same
private paths without authentication, API calls, receipt or lock creation. It is
only a point-in-time path check; apply revalidates and locks the transaction.

Use a protected **JSON-only** input file, never secret command-line values.
The launcher rejects duplicate/unknown keys, internal facts, Ansible connection
settings and credential-path overrides before Ansible. Primitive types and literal
field grammars reject Jinja/lookups before Ansible can evaluate any supplied value. Allowed keys are only the
seven `gitlab_group_*` intent fields listed above (excluding receipt_file),
`gitlab_native_origin` and `gitlab_native_ca_file`; token/receipt paths are positional. The executor supplies
only the approved token capability; input flags and a receipt do not grant it.
Parent Group Owner credentials can carry inherited authority over all descendants,
not only one tenant. Do not call that a one-child grant or equate a human PA's
visibility with permission to provision an instance-admin service credential.
Identity inspection for another user's OIDC `identities` is separately privileged
in pinned GitLab; this foundation step does not call user APIs or solve that gate.

## Ownership, status and retry

Both exact paths are inspected before any creation. Existing objects must match
reviewed native IDs, full paths, parent relationship and private visibility. Before
each creation, the path is re-read; native conflict/redirect/error aborts rather
than adopting a competing object. Successful writes are read back by numeric ID.
The exact receipt is atomically updated after verified parent and child phases:

`schema, origin, context, source_revision, previous_revisions, parent_id, group_id, stage`

Stages are `pending`, `parent-ready`, `group-ready`. Group-ready means only the
native private group passed readback. It does **not** mean users, membership,
Portal status publishing, automatic triggering, pipelines or notifications are
ready. API failure cannot become an empty authoritative membership list.

A child-create failure retains the parent receipt and permits an exact inspected
retry without recreating it. An uncertain request or receipt-write failure can
leave a created group unreceipted; the next run refuses it. Inspect and reconcile
that ownership explicitly instead of deleting it, overwriting the receipt or
assuming a matching name proves ownership. No rollback/data deletion occurs.

A changed source revision is rejected before authentication unless the protected
`gitlab_group_previous_revision` equals the receipt's exact current revision and
the previous group-ready IDs are present. Both existing objects must then pass
fresh native readback with unchanged IDs/path/private/parent. Only afterward does
the helper update source_revision and append the previous revision to a bounded
private history. Wrong prior revision or failed ownership leaves the old revision
binding intact. Previously recorded revisions cannot be reselected. At 32 history
entries, same-revision retries remain valid but a new transition requires explicit
custody/archive review; no unbounded growth or discarded anti-rollback history.
The caller must use one stable context-specific receipt/lock path across source
revisions, not evade CAS by choosing a new filename. This is guarded source
transition, not a continuous enrollment watcher or permission to change identity.

Existing group settings outside the verified boundary and effective memberships
are separate reconciliation concerns. Receipt protection is local ownership, not
cryptographic authentication; a trusted executor and live ID readback remain
required. Concurrent external administrator edits are not an atomic transaction.

## Verification

`security.test_gitlab_group_foundation` runs this actual Ansible playbook against a
synthetic local HTTPS API: default/check no contact, explicit parent bootstrap,
create/readback/repeat, existing approved parent, foreign parent/child rejection,
private/ID/path/parent drift, source revision refusal, partial child failure and
retry, native conflict, private-token checks, receipt symlink refusal and output
redaction. No real GitLab state or credential is used. This is protocol/guard
coverage, not deployed capability, RBAC proof or completed #334 acceptance.
