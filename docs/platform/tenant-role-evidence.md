# Daily tenant-role authorization evidence

**Proposed; not implemented, scheduled, or tested against the cluster.**
This is a narrow continuous-authorization check, not a compliance determination
or a substitute for onboarding and revocation acceptance. It depends on an
approved evidence destination ([#22](https://github.com/perkforge/perkforge-platform/issues/22)).
The [role/app matrix](../../big-bang-bootstrap/configuration/authorization/MATRIX.md)
defines intent; [tenant trust boundaries](../tenant-architecture/README.md) identify
enforcement points. The existing [verification guide](../../big-bang-bootstrap/tests/README.md)
distinguishes offline tests from physical acceptance. Network isolation remains
separate ([#44](https://github.com/perkforge/perkforge-platform/issues/44)); this
check does not establish it.

## First check: tenant-viewer read isolation

Use two approved, non-business-data fixture tenant namespaces, each containing
one reviewed inert workload with no secrets. Select namespaces and identities in
adopter configuration, not the verifier code. Use the same pinned verifier in
each environment; Git owns the fixtures, declared policy and the check matrix.

| Test identity | Requested operation | Declared expectation |
| --- | --- | --- |
| Viewer for fixture tenant A only | Read the named workload in A | Allow |
| The same viewer | Read the named workload in B | Deny |
| Viewer for fixture tenant B only | Read the named workload in B | Allow |
| The same viewer | Read the named workload in A | Deny |

The paired own-tenant reads also establish that both objects exist. Use the
actual intended identity and native API authorization, not a privileged user's
impersonation or a successful login as a substitute. Read only the named
synthetic objects; discard their bodies and record status only. Keep the test
identities separate from human users and grant only the reviewed test role
through the same enforcement path the check is meant to exercise. If representative
authentication cannot be automated without weakening it, mark that coverage
blocked; a service-account check is not proof of human/OIDC access.

## Run and evidence contract

- **Deterministic daily schedule.** After separate activation approval, one
  script-only Hermes cron job invokes the pinned phase with no agent, prompts,
  detached work, or job-defined destinations. Use the approved target, exact
  read checks, bounded timeout and overlap guard. Use separately approved,
  expiring scoped credentials via the existing protected mechanism; fail closed
  if missing. Do not use delete, write, exec, escalation, real tenant data or
  secret-value endpoints.
- **Compare policy to reality.** Select immutable deployed platform and
  enrollment revisions and the reviewed test matrix, rather than assuming that
  current development-branch policy is deployed. Require valid authenticated
  identities and a complete run. Treat native expected authorization denial as
  a pass only when distinguishable from authentication failure and when the
  matching fixture precondition passed. Not-found is not denial.
- **Record only sanitized findings.** One versioned manifest per target/window:
  run ID, scheduled and observed UTC times, immutable revisions and verifier
  digest, fixture/role and operation labels, expected and observed outcomes
  and a bounded reason code. No credentials, usernames, raw logs, API bodies,
  live resource details or model output. Write atomically to the approved
  private evidence store with restricted access; keep only the retention
  period approved under #22 (proposed initial 90 days, do not enable without
  approval). Do not send raw evidence to chat.
- **Keep outcomes distinct.** `pass`: complete and all rows agree;
  `fail`: an authoritative allow/deny disagreed; `error`: a prerequisite,
  authentication, fixture, transport, verifier, or evidence write failed;
  `missed`: the daily window ended without a fresh run receipt. Record confirmed
  mismatches even if a separate row errored. Deduplicate by target/window, and
  never reuse yesterday's pass. An independent freshness check must be able to
  report a missed run even if Hermes or the check is down.

## Acceptance before activation

1. Offline synthetic tests cover expected allows/denials, unexpected grants,
   unexpected denials, 401/not-found/timeouts, missing credentials, missing
   receipts, overlapping runs, and rejection of credential-shaped output.
2. Review the rendered identities, immutable source pins, target, exact API
   scope, schedule, evidence store access/retention and alert recipient. No
   activation, grant, or delivery is implied by this document.
3. With separate approval, observe a fixture-only run on the chosen target,
   verify all four rows and the sanitized stored receipt, then verify that a
   missed window would alert once. Label this evidence for the tested role and
   enforcement point only; expand to another role or app in a reviewed change.
