# Attestation-consuming group membership writer

Source component only. Not a running reconciliation controller, account provisioner,
identity linker, or authorization for new human grants.

- `run-membership.sh --apply WRITER ATTESTATION GROUP_RECEIPT INPUTS GRANT_RECEIPT`
  uses one group writer credential. It never receives or calls the admin reader.
- Literal protected JSON is validated before Ansible. Full path guards and the
  existing stable group receipt lock cover the whole native transaction.
- Grant/inspection requires the attestor's exact schema-1 `IdentityVerified`
  receipt, same origin/context/immutable subject/source/native ID, captured within
  five minutes and not in the future. The account must still be active natively.
- Inputs must originate from the independently verified current canonical
  Keycloak entitlement snapshot. Identity attestation alone grants no role.
- Runtime authenticity is a mandatory external boundary: only the isolated
  attestor may write the exact receipt ConfigMap; admission must pin the writer's
  image, command and mounts to that object. The fixed executor stages its bytes
  into private regular files. The five-minute freshness window is bounded
  evidence, not continuous proof against identity unlink/relink during that window. Arbitrary Portal/user-uploaded JSON is not an
  accepted authority. This source is not ready for runtime activation until that
  issuer-only delivery boundary and canonical snapshot are implemented and tested.
- Writer acceptance checks native bot/active/non-admin status, only `api` scope,
  direct Owner membership in the exact receipt parent, and the exact token ID
  through that parent group access-token endpoint. No arbitrary PA PAT.
- Roles are only tenant-admin/Owner50, tenant-developer/Developer30 and
  tenant-viewer/Reporter20. No PA-wide rights are inferred from tenant ownership.
- An existing direct grant cannot be silently adopted. A protected `GrantPending`
  intent is recorded before POST, permitting exact retry/readback after an
  uncertain native response. Pending intent is valid for at most five minutes
  and never from the future; older intent fails before API access for reviewed
  manual recovery, even when native membership might be absent. A concurrent
  external identical grant during that bounded uncertainty window cannot be
  distinguished by GitLab membership metadata alone. `Granted` follows verified direct/effective access.
- Revocation uses the prior owned grant receipt, so blocked/missing first-login
  identity does not prevent removal. It removes only direct group membership;
  a prior Revoked receipt cannot authorize a later external regrant.
  Inherited or descendant/project access is not silently changed. Remaining
  effective access returns failure and does not claim offboarding complete.
- Grant receipts have fixed per-subject names alongside the group receipt.
  They retain source revision and native binding. Readback failure never writes
  an apparently successful new outcome. Receipt persistence failure after a
  native write remains a partial failure, not rollback or success.

The synthetic TLS fixture exercises actual Ansible and native API shapes, not
live accounts or the issuer-only Kubernetes transport. No production memberships
or credential scopes were changed by these tests.

## Remaining integration gates

- This component handles exact-role grant/revoke, not a complete role-change
  workflow. A different desired role fails closed against the protected old
  receipt, including a revoked old-role receipt. Report PendingRoleChange until
  an explicit reviewed prior-role transition and its orchestration exist.
- MembershipReady may only follow current canonical entitlement selection and
  this invocation's verified native readback. GroupReady, IdentityVerified and
  Job Complete are not equivalent to full tenant onboarding.
- Arbitrary Keycloak changes do not trigger this source by themselves. Only the
  approved explicit enrollment revision trigger can invoke a future runtime.
