# Phase 6 review packet

This packet is for design review before implementing the remaining lifecycle
and continuous-assessment work. The local VMs are back on the reduced profile;
this review and its proposed follow-up work do not require cluster changes.

## Current Phase 6 position

| Capability | Current state | What remains |
|---|---|---|
| Security test execution | Manual suite runner; live tests have timestamped JSON and Markdown reports | Safe repeatable scheduled execution and documented operational ownership |
| Candidate findings | Failed explicit checks become untriaged candidate records; execution errors are excluded | Persistent, reviewed register and auditable status changes |
| Risk and remediation | Human workflow documented in [Security Findings Workflow](SECURITY-FINDINGS-WORKFLOW.md) | Record-level review, risk decisions, owners, due dates, and closure evidence |
| Evidence | Local ignored evidence directories; reports reference detailed suite output | Retention, integrity, redaction, access, backup, and controlled publication rules |
| Notifications | None | Actionable notification for failures, missed runs, and cleanup errors |
| Tenant lifecycle | Tenant catalog and platform provisioning exist; no safe lifecycle command set | Define and verify suspend/resume/offboard semantics before automation |
| Identity revocation | Keycloak groups and Rancher bindings exist | Test group removal, existing sessions, token expiry, and residual access |

Live enforcement work that may add workload or observability pressure remains
deferred to the ThinkCentres. The local profile capacity guard does not replace
that hardware validation.

## Recommended design to review

### 1. Keep source evidence separate from reviewed findings

- Preserve each run's raw JSON and Markdown evidence as an immutable,
  timestamped run artifact.
- Keep candidate findings generated from the run as a queue, never as an
  automatically confirmed finding.
- A human-reviewed register entry references the candidate and evidence by
  run ID, test ID, artifact path, and optional digest.
- Do not publish raw cluster reports in this public repository. Store
  operational evidence in an access-controlled location; publish only reviewed
  and sanitized synthetic examples.

### 2. Use an append-only review history

Treat the finding's current status as a summary, not the whole audit trail.
Every transition should record the previous and new status, actor, timestamp,
rationale, and references to evidence or change records. Use reviewed Git
changes or a protected internal GitLab project once that service is available;
do not silently rewrite or delete a finding after it has been reviewed.

### 3. Separate assessment from authorization

The engineering workflow may document impact, likelihood, safeguards,
residual-risk rationale, and remediation options. It must not automatically
assign severity, accept risk, or claim that a named control is satisfied.
Risk acceptance belongs to an identified authorized decision maker and needs
a review/expiry date. Keep the organization's approved risk methodology
configurable rather than embedding an assumed DoD/FedRAMP scoring table.

### 4. Schedule only after the execution identity is settled

First run the suite manually on the ThinkCentre cluster and measure run time,
resource impact, cleanup behavior, and evidence volume. Then select cadence and
execution location. A scheduled runner needs a dedicated least-privilege
identity, protected credentials, timeout and cleanup handling, evidence
retention, missed-run detection, and failure notification. Avoid a personal
long-lived admin kubeconfig as a scheduled credential.

For environments requiring CAC, do not automate browser CAC interaction or
weaken authentication to make a scheduler work. Separate API-side technical
checks from attended CAC-dependent UI checks; document the human step and its
evidence. Validate the actual environment's identity and authorization rules.

### 5. Define safe tenant lifecycle behavior before commands

Recommended initial meanings for review:

- **Suspend:** block new tenant changes and revoke tenant access; decide
  explicitly whether existing pods continue, are scaled down, or are
  quarantined. Suspension must not imply data deletion.
- **Resume:** restore approved access and workload behavior from declared
  configuration, then verify tenant boundaries.
- **Offboard:** revoke access first, preserve required evidence and data, then
  require an explicit reviewed destructive step for namespace/PVC deletion.

All lifecycle operations should be idempotent, ownership checked, logged, and
scoped to the tenant catalog. Do not infer namespace ownership from a matching
name alone. Keep break-glass Rancher administrator access independent of tenant
identity changes.

## Decisions for the review list

| Decision | Recommended default | Alternatives / question to resolve |
|---|---|---|
| Findings source of truth | Sanitized structured records with reviewed, append-only transitions | Git in a protected internal project; ticketing system; database-backed GRC tool |
| Operational evidence location | Access-controlled storage outside public Git | Local encrypted archive; private GitLab artifacts; object storage when available |
| Public portfolio evidence | Synthetic, redacted examples only | Decide whether selected machine-readable evidence can be published after review |
| Risk scoring | Use an organization-approved method; leave unassessed until named review | Define a local qualitative scale for this reference lab, clearly labeled illustrative |
| Initial schedule | Choose only after a measured ThinkCentre manual run | Daily, weekly, or change-triggered; avoid scheduling against current memory-constrained VMs |
| Scheduled execution identity | Dedicated least-privilege identity with rotation and audit | CI job identity or a dedicated in-cluster service account, based on tests needed |
| Failure notification | Notify an operator on failed checks, missed runs, and cleanup errors | GitLab issue/MR, email, or monitoring alert after service and authorization choices |
| Suspend behavior | Revoke tenant access and block changes; preserve running workloads until policy says otherwise | Scale down or quarantine immediately; document data/service impact |
| Offboarding | Two-step, evidence-preserving process; destructive deletion requires separate approval | Retention duration and backup requirements need an explicit policy |
| CAC-dependent assessment | Keep CAC UI validation attended; automate only permitted API checks | Environment-specific approved automation, if explicitly supported by the authorizing policy |

## Proposed offline implementation sequence

1. Define a versioned findings-register schema and a validator. Reject invalid
   transitions and missing decision authority; do not calculate risk.
2. Add an explicit import command that copies candidates into a review queue
   idempotently, keyed by run/test identity. It must not confirm findings or
   edit source evidence.
3. Add a transition command that requires actor, timestamp, rationale, and
   required fields for each status change; write an append-only history.
4. Document an evidence retention and sanitization policy with public/private
   boundaries.
5. Specify schedule, identity, alerting, and tenant lifecycle behavior without
   enabling a live schedule or running destructive actions.
6. After hardware arrives, measure and validate the runner, cleanup behavior,
   access revocation, lifecycle operations, and chosen schedule before calling
   these capabilities operational.

## Review checklist

- [ ] Agree on who can confirm, dismiss, risk-accept, and close a finding.
- [ ] Select where the private register and raw evidence live.
- [ ] Set evidence retention, backup, and sanitization requirements.
- [ ] Confirm whether risk scoring should use a provided organizational method.
- [ ] Choose the desired first assessment cadence after hardware measurements.
- [ ] Choose a scheduled execution identity compatible with any CAC boundary.
- [ ] Define what suspension does to access and already-running workloads.
- [ ] Define offboarding retention and the separately approved deletion step.
- [ ] Decide which synthetic, sanitized artifacts are suitable for the public portfolio.

The recommendation table is intentionally a review aid, not a claim that
these policies have been approved or implemented.
