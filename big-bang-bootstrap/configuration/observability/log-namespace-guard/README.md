# Native namespace log-ownership lifecycle guard (inactive)

For #218/#38. This default-off Ansible renderer makes one native
ValidatingAdmissionPolicy and Binding per registered runtime namespace. It closes
the namespace-name reuse window in the Loki epoch mapping without a controller:
while the guard exists, CREATE and DELETE of that exact Namespace are denied;
UPDATE (including status/finalize) must retain the expected immutable UID and
`platform.perkforge.io/log-context` / `platform.perkforge.io/log-scope` annotations.
It does not grant tenant access, change RBAC, or infer ownership from pod labels.
An administrator capable of changing admission policy can bypass the guard; this
is not a defense against a trusted platform administrator changing policy.

## Inputs and custody

Use the existing reviewed `paas_context` as `log_context`, one exact entry from
its `kubernetes.runtime_namespaces` as `log_namespace`, an independently verified
`log_namespace_uid`, and the reviewed immutable ownership epoch `log_scope_id`.
Supply a fresh read-only Namespace object as `log_namespace_observed` and the
source owner's nonempty label subset as `log_namespace_owner_labels`. Neither a
Namespace name nor a caller-supplied context is proof of ownership: the operator
must verify them against the selected authoritative enrollment release and exact
runtime object before approval. Control namespaces, wrong UID, terminating
objects, missing owner labels and conflicting ownership annotations fail closed.
Never reuse an epoch after ownership transfer. No production UID is in this source.

`log_namespace_guard_render=true` and a fresh absolute `log_guard_output` produce
`policy.yaml` and `namespace-patch.json`, mode0600 in a new0700 directory. Default
and `--check` do not read a cluster, render, or call an API. There is no live
entrypoint. Generated target state belongs in protected environment-owned
foundation inputs, not the reusable image/chart. Review and durably own these
policies with the existing platform foundation workflow, outside tenant-controlled
resources. Do not silently prune or replace a guard as a side effect of enrollment
or remove it merely because a tenant namespace was omitted from discovery.

The JSON Patch tests UID, resourceVersion, and (when present) the complete prior
annotation map, then adds the two keys while preserving every existing annotation.
ResourceVersion protects absence of the map too. It changes no labels, PSA,
finalizers, spec, or owner reference. A stale patch must fail and be re-rendered
from fresh approved metadata, not retried without its tests. Existing identical
annotations are permitted; different owner/epoch annotations are never adopted.

## Foundation SSA compatibility

The current Portal enrollment foundation owns the Namespace names and PSA/runtime
labels, not these new annotation keys. Its normal server-side apply merges those
existing labels and leaves separately managed log annotations intact. The initial
patch must use a dedicated field manager (for example `log-namespace-guard`) and
must not take over the entire Namespace via a replacement apply. The VAP also
allows unrelated label/annotation/finalizer updates that retain the binding, so
ordinary reconciler updates remain possible. A client-side/full-object update
that drops the binding fails deliberately. A future enrollment manager claiming
or removing these keys must be fixed in source, not given a policy bypass.

## Exact activation batch requiring confirmation

For each reviewed namespace, approve only:
1. Create/update its named `log-ownership-<namespace>` VAP **unbound** first; verify
   observed generation and empty `status.typeChecking.expressionWarnings`. Schema
   dry-run alone is not CEL runtime proof. Refuse any pre-existing foreign policy
   or Binding with that name; pin UID/resourceVersion for same-owner updates.
2. While the policy remains UNBOUND and tenant access remains off, apply the
   generated additive Namespace JSON Patch with its tests and dedicated field
   manager. Read back exact UID/context/epoch and all prior labels. Refetch and
   verify the UID again immediately before binding; never adopt a replacement.
3. Bind only that policy with validationActions Deny after metadata is verified.
   Verify admission propagation using server-side dry-runs before tenant query
   access exists. Seeding before binding avoids transient namespace status denial.
4. Dry-run initial/unchanged ownership updates, unrelated metadata and existing
   foundation SSA successfully; dry-run annotation removal/epoch change, DELETE,
   and UID mismatch denied. CREATE on an extant name may only return AlreadyExists:
   that is NOT admission denial proof; use the offline native CEL CREATE fixture
   or a separately approved disposable policy fixture, never delete the runtime
   namespace to test it. Verify other namespaces are outside policy match scope.
5. Only then align collector name→epoch routing and gateway read/write scopes and
   perform real Loki/Grafana cross-scope/spoofed-header/pod-annotation denials.
   Tenant access stays off until all authorization and stale-session gates pass.

These are scoped admission changes and require action-time approval. This PR
applies none of them. Keep durable policy ownership and source review separate
from manually observing metadata; no untracked one-off authorization grant.

## Revocation / ownership transfer (ordered, never automatic)

First revoke old tenant query credentials and Grafana/IdP membership/session/token
access with verified denial of old cookies/tokens. Stop collection for the name
and remove its old routing assignment; wait for the reviewed collector config
and in-flight old partition writes to settle. Preserve historical old-epoch logs
for platform-only retention, never expose them to the new owner. Only after this
fail-closed state is proven may an explicitly approved operator retire the exact
Binding/policy, delete/recreate the namespace or transfer ownership, and allocate
a NEW epoch. Verify the new UID and authoritative context; install/verify the new
guard and metadata binding, then new collector/gateway config and negative tests,
then enable the new reader. Do not reassign owner in place with the old epoch.
The guard prevents ordinary namespace deletion/recreation, not credential/session
revocation or tenant membership changes: those remain independent required gates.

## Evidence and remaining gate

Four real offline Ansible tests cover inert defaults/check, exact resources,
additive CAS, stale/foreign/terminating inputs, no overwrite and no annotation
adoption. `tests/log_namespace_cases.py` emits the rendered expression and eleven
positive/negative lifecycle cases. The existing pinned Kubernetes1.36 CEL harness
has `TestLogNamespaceGuard`; run from `tests/security/cel` with
`LOG_NAMESPACE_CASE_SCRIPT` set to the absolute fixture script path. It compiles
and evaluates the actual rendered expression, including CREATE/DELETE denial.
The existing CI job includes this test when its already-paused workflow is resumed;
this change does not unpause it. Local Go is unavailable, so native compilation
is pending. Both synthetic manifests passed Kubernetes server-side dry-run structure validation without persistence; that does not compile/evaluate bound admission. No live policy installation or actual admission/SSA claim is made.
