# Finite tenant identity phases (source component, not activated)

- Explicit Flux declaration revision/retry generation selects one attempt. No
  CronJob, polling, automatic first-login callback or continuous offboarding.
- Foundation remains the reviewed native group adapter. Its successful current
  attempt writes a private sibling `foundation-result.json`: schema1, phase
  GroupReady, context, invocation, source_revision, platform_revision, parent_id,
  group_id and captured_at. Membership requires exact bindings and age<=5min;
  an old same-code group receipt alone is insufficient. The fixed packaging
  phase may write this result only after native foundation exit0/readback.
- `run-attestor.sh --apply INPUTS_JSON PRIVATE_WORK_DIR` reads only the approved
  Keycloak client and GitLab admin-owned read-only token. It publishes one
  bounded observation to a precreated exact-UID ConfigMap with resourceVersion
  and desired-attempt JSON Patch tests. It cannot approve/create GitLab users.
- `run-memberships.sh --apply INPUTS_JSON PRIVATE_WORK_DIR GROUP_RECEIPT` receives
  only the parent-group writer token and issuer observation. It invokes the
  reviewed native membership adapter, preserving per-subject ownership receipts.
- Bare/default execution is inert; `--validate` makes no native requests. Inputs
  are duplicate-key-free literal JSON validated before Ansible interpretation.

## Runtime gates still required

- Separate attestor/writer credentials and namespaces; exact image/source pins,
  admission, ESO custody, network permissions and native executor acceptance.
- Exact-name ConfigMap GET/PATCH is not field-level restriction. Admission must
  prevent issuer metadata/desired-attempt changes and foreign receipt mounts.
  GitOps owns desired metadata, not dynamic observation data. Bootstrap records
  the stable ConfigMap UID; no create/delete permission is assumed here.
- Fixed packaging helper `/opt/perkforge/bin/refresh-identity-evidence` reads only
  the issuer-controlled mount and privately stages/validates the envelope. The
  local phase fixture substitutes a synthetic projection copier, not evidence
  that the Kubernetes trust boundary is deployed.
- Whole-context `trigger.lock` serialization spans the membership phase using
  the reviewed native Linux owner/ancestor/inode proof. The standalone wrapper
  acquires it with no-fork flock; packaging may supply its proven ancestor owner
  in PERKFORGE_PHASE_LOCK_OWNER. Foundation must use this same context lock.
  It remains separate from the adapter's `gitlab-group.json.lock`.
- Native Keycloak fine-grained reader permissions are not configured by this
  component. Recovery verification is an explicit declaration prerequisite, not
  synthesized from an admin account or secret's existence.

## Bounded outcomes

- The invocation digest includes the selected revisions, contract hash, exact
  group IDs, receipt UID and retry generation/explicit predecessor. Phase name
  is excluded so attestor and writer share the same attempt identity.
- First publication requires empty receipt data. A later publication requires
  the explicitly declared predecessor. Replaying an already published attestor
  attempt refuses overwrite; manual retry needs a new reviewed attempt. Flux
  must retain completed desired Jobs, not TTL-delete them into recreation loops.
- Two matching Keycloak reads remain a non-atomic observation. Evidence expires
  after five minutes; there is no instantaneous cross-system revocation claim.
  A writer pins the entire initial observation and refuses changed content even
  if UID and invocation still match. Before each operation it refreshes from
  the fixed mount and validates freshness and equality again.
- Pilot cap: three subjects across the union of current desired members and all
  owned grant receipts (including retained revoked receipts). Larger/history
  sets stop before native writes; this is not a scalable lifecycle claim.
- Missing native identity: PendingFirstLogin. Native account awaiting manual
  approval: PendingAccountApproval. No inferred email/account linking.
- Role or native-ID replacement remains PendingRoleChange, with no replacement
  grant. Stale ambiguous GrantPending ownership requires manual recovery; no
  automatic extension of its five-minute recovery window.
- Removal, disabled identity or missing/blocked native identity can revoke only
  an exact prior-owned direct grant. Descendant/project/inherited access is not
  deleted. Pending identity remains pending even if an old grant was revoked.
- NoDesiredMembers is an empty valid roster result, not positive grant proof or
  a positive membership readback. Group readiness is separately bound to the
  fresh foundation result. The real Portal roster was empty at investigation.
- Result JSON exposes only fixed stages/categories and bounded counts. Private
  per-subject results and existing ownership receipts preserve partial outcomes.
  A failed native operation may have written before its response was lost:
  PartialFailure never means rollback. No raw API bodies/tokens are emitted.

## Evidence and limits

Actual Ansible/local TLS fixtures cover attestor empty/pending/verified cases,
UID/CAS/stale-attempt refusals; membership three-subject grant, identical-attempt
repeat without duplicate grants, pending role changes, owned revocation,
explicit recovery gate and mid-batch observation mutation refusal. They use no
real accounts. Runtime image/issuer admission/Flux dependency generation and
native delivery remain separate acceptance gates. Existing recovery acceptance
is documented in the established GitLab runbooks; no new recovery test is
implied by source fixtures.
