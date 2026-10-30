# Phase 6 review packet

This packet is for design review before implementing the remaining lifecycle
and continuous-assessment work. The local VMs are back on the reduced profile;
this review and its proposed follow-up work do not require cluster changes.

## Current Phase 6 position

| Capability | Current state | What remains |
|---|---|---|
| Security test execution | Manual suite runner; live tests have timestamped JSON and Markdown reports | Safe repeatable scheduled execution and documented operational ownership |
| Candidate findings | Failed explicit checks become untriaged candidate records; execution errors are excluded | Team-backed system of record and multi-user audit protections |
| Risk and remediation | Human workflow and local private register record review, rationale, authority, owners, due dates, and retest transitions | Team review/approval integration, controlled backup, and retention |
| Evidence | Local ignored evidence directories; reports reference detailed suite output | Retention, integrity, redaction, access, backup, and controlled publication rules |
| Notifications | None | Actionable notification for failures, missed runs, and cleanup errors |
| Tenant lifecycle | Optional catalog state `active`, `suspended`, or `offboarding`; project binding reconciliation removes only exact catalog-owned tenant PRTBs for inactive states and restores them on resume | Live revocation/session behavior; pause tenant application GitOps; safe staged data/PVC decommission |
| Identity revocation | Keycloak groups and Rancher bindings exist | Test group removal, existing sessions, token expiry, and residual access |

Live enforcement work that may add workload or observability pressure remains
deferred to the ThinkCentres. The local profile capacity guard does not replace
that hardware validation.

## Recommended design to review

### 1. Keep source evidence separate from reviewed findings

- Preserve each run's raw JSON and Markdown evidence unchanged as a timestamped
  run artifact.
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

- **Suspend:** the implemented initial behavior removes the tenant's
  catalog-owned Rancher project role bindings. Existing workloads continue;
  this does not pause tenant GitOps or provide network/runtime quarantine.
  Suspension does not delete data.
- **Resume:** returning the catalog state to `active` allows the binding
  reconciler to restore approved access. The local script verifies catalog
  ownership but does not yet verify user session revocation or browser access.
- **Offboard:** currently acts as suspension and retains the Project,
  namespaces, workloads, and volumes. Destructive deletion is not implemented;
  use a separate reviewed process after evidence and data-retention decisions.

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

1. Review and accept the local register semantics; decide where multi-user
   review, protected history, backups, and retention should live.
2. Validate lifecycle reconciliation against a disposable tenant on the
   ThinkCentres, including real binding revocation, new login, and existing
   session behavior. Test that tenant application Fleet changes are blocked
   before calling suspension complete.
3. Measure manual assessment runtime, resource impact, cleanup behavior, and
   evidence volume on the ThinkCentres; then settle schedule, least-privilege
   execution identity, retention, and alerting.
4. Implement the approved schedule and notification integration. Keep CAC UI
   tests attended unless the target environment explicitly approves automation.
5. Define and validate an approved offboarding/data-destruction procedure;
   preserve evidence and require an explicit destructive action.

## Review checklist

- [ ] Agree on who can confirm, dismiss, risk-accept, and close a finding.
- [ ] Decide whether the local private JSON register is adequate for this lab or whether a private GitLab/ticketing system is needed.
- [ ] Set evidence retention, backup, and sanitization requirements.
- [ ] Confirm whether risk scoring should use a provided organizational method.
- [ ] Choose the desired first assessment cadence after hardware measurements.
- [ ] Choose a scheduled execution identity compatible with any CAC boundary.
- [x] Define the initial suspend behavior: remove tenant Rancher project bindings; leave existing workloads running.
- [ ] Decide whether suspension should also pause Fleet app reconciliation or stop workloads.
- [ ] Define offboarding retention and the separately approved deletion step.
- [ ] Decide which synthetic, sanitized artifacts are suitable for the public portfolio.

The recommendation table is intentionally a review aid, not a claim that
these policies have been approved or implemented.
