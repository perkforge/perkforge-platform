# One-shot GitLab bootstrap and exact-record custody

Default-off source; **not activated or native-mint accepted**. A plan or this
coordinator does not authorize its privileged execution.

Before any apply, the operator must have the exact informed native/custody
approval and a reviewed, runnable runtime/foundation bundle with its remaining
activation steps and expiry budget established. These are operator prerequisites,
not inferred from passing a JSON flag or from the presence of this source. The
coordinator proves its exact custody preflight; it does **not** prove cluster
admission, scheduling or workload readiness. Do not issue credentials early while
those prerequisites are still unresolved.

- `bootstrap-gitlab.py validate TOKEN RECEIPT INPUTS_JSON` validates literal
  selection/private paths without native or custody requests. Bare is inert.
- `apply` is a one-time attempt under a native exclusive lock. Existing attempt
  receipts require review; there is no blind bootstrap retry or foreign adoption.
- The Python host coordinator is the only entry. Do not run the Ruby module as a
  token-printing script. Its native response is captured only in a process pipe,
  parsed in host memory and never emitted as tool output or written to a log.

## Exact operator precondition

The OpenBao operator must be separately provisioned and approved. No operator is
created here. It must have only `tenant-identity-bootstrap-gitlab-v1`, no default,
root or identity policy, nonrenewable remaining TTL between15 and60 minutes, and
an ACL body byte-identical to the accompanying HCL. Native policy inspection is
checked before minting and each secret write. No root-token fallback is present;
earlier approval for unrelated records is inapplicable.

The ACL permits read/create/update only on the two stated GitLab data records,
read of their metadata, and self/policy inspection. Within those two records its
native update authority is broader than the coordinator's create-only CAS0
workflow. No Keycloak secret, other record, policy write or token issuance
capability is granted. This source does not retire a bootstrap root credential.

## Native actions requiring specific approval

- Pin the target GitLab namespace and toolbox Pod UIDs, native19.4.2 version,
  configured HTTPS host, and one selected active administrator's exact native ID
  plus immutable OIDC subject. No ID1, username or email inference.
- Require Admin Mode disabled and legacy token issuance permitted; never add an
  unapproved token scope or change instance settings to make issuance work.
- Refuse an existing top-level tenants path and any active default integrations.
- Native Groups::CreateService creates private `tenants`, automatically adds the
  selected human as parent Owner, and may perform native audit side effects. The
  Flux foundation, not bootstrap, will create the tenant child group.
- Create a native parent group access-token bot with api/Owner. It inherits
  authority across the tenants subtree. It is not a one-child-only writer.
- Create a separate administrator-owned read_api token. This has broad instance
  read authority; no self_rotate/admin_mode/api/sudo scope is added here.
- Explicit dated expiry must leave between1 and48 hours until UTC midnight at
  execution. Dates do not mean “24 hours after creation.” The native routines
  can send token-created/revoked notifications and create audit records.
- Native resource-token creation failure may schedule cleanup of its newly
  created bot through the installed service. This is not permission to delete
  existing users. Successful token revocation retains the bot/parent membership.

## Custody and failure outcomes

- Both exact metadata paths must be absent before issuing native tokens.
- Each new secret uses CAS0, then exact version1/data readback. Never overwrite a
  foreign existing record. Stored fields include token, setup ID, native token
  ID and explicit expiry. Runtime consumers select only their token property.
- Protected receipts fsync both file and parent directory after create/replace.
  A protected nonsecret receipt records NativeRequested before execution. Lost
  execution/result cannot be called rollback or automatically retried; native
  state may exist and needs manual inspection.
- If custody write/readback fails after a verified mint response, revoke only the
  exact newly owned tokens using native services, checking setup description,
  actor/resource ownership before revocation. Record revocation uncertainty.
- A failed response can follow a successful KV write. Preserve such records,
  including now-revoked values; do not delete or mark all effects undone. The
  receipt's stored list means verified readbacks, not exhaustive possible writes.
- Preserve the new parent and bot membership. No parent/user deletion, role
  rollback or general token cleanup is performed.
- GitLabCustodyVerified is not deployment, Keycloak custody, client activation,
  native first-login approval, tenant membership or platform-admin synchronization.
  Those remain separate guarded operations/acceptance gates.

## Evidence limits

Host tests use synthetic TLS for exact ACL/TTL checks, CAS response loss,
readback drift and redaction, with a fake native subprocess for mint/revoke.
The installed toolbox Ruby interpreter only syntax-checks the module, without
Rails, database initialization or service calls. Pinned service source has been
inspected for signatures, response keys, side effects and cleanup, but a Ruby
syntax check is not a native bootstrap acceptance test.
