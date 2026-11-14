# Mattermost: inactive Big Bang candidate

Reviewed 2026-11-08 for MR #116. Both packages remain disabled and suspended,
absent from all cluster roots. Rendering this candidate does not authorize rollout.

## Current package and native values

The selected Big Bang **3.35.1** release is the version authority. The candidate
contains no package Git/tag or image-version override. Its defaults select
Mattermost **11.11.0-bb.0** (app 11.11.0) and operator **1.25.9-bb.1**.
Checksummed test fixtures match those release values; a regression checks equality.
Newer independent package releases are not selected by this MR.

The candidate uses native `addons.mattermost` and `addons.mattermostOperator`
values and inherited chart defaults. Bundled PostgreSQL/MinIO/Elasticsearch are
disabled. External `mattermost-database` and `mattermost-filestore` Secret
references remain; endpoints are unconfigured until operator preparation.
Native registry references are wired for the app CR, operator and readiness Job;
namespace-specific `private-registry` delivery remains a prerequisite. No registry
credential is created or read.

The exact renders contain eight Mattermost objects and eight operator objects,
including three CRDs. Both installer identities live in `bigbang`, separate from
the runtime operator. No cluster-admin binding is added.

## Remaining deployment gates

- The stock operator needs global informer reads, including all Secrets.
  The candidate's [scoped-write policy](#operator-runtime-authority) replaces its
  upstream global writes. This is not namespace isolation; source and live
  acceptance remain distinct.
- The native wait hook still emits unrestricted any-port egress even with general
  network policies disabled. Keep readiness; review API-only transport before use.
- Review exact image digest/security status, [edition and license](edition-review.md),
  Kubernetes compatibility and cumulative app/operator/data-service capacity.
- Prepare separately approved external PostgreSQL and S3 storage, trusted TLS,
  restricted routing, protected Secret delivery and independent restore evidence.
- Establish independent local administration with restricted signup before SSO.
  No human credentials, account grants, activation or deployment occurs here.

## Entry and Keycloak OIDC

Entry remains the planned free mode of the Enterprise binary, not a paid trial.
`enterprise.enabled: false` disables license wiring; it does not establish rights
or runtime features. Source evidence and runtime acceptance are distinct.

The `sso-values.yaml` contract uses native `MM_OPENIDSETTINGS` environment values
and an existing client Secret, plus a read-only public CA mount through
`SSL_CERT_FILE`. The [SSO preparation](../../authorization/sso/mattermost/README.md)
prepares the disabled Keycloak client and public app values together. Big Bang's `sso.enabled` stays false because that
helper configures GitLab auth rather than Other OIDC. Signup stays closed.
Initial person provisioning/linking, native team/channel membership and
offboarding remain separate acceptance requirements. Team Admin is not System Admin; assigned viewers may chat. No v12.1
ABAC or paid feature assumption is made. See `sso-review.yaml` for acceptance gates.

## Offline validation

Run the Mattermost security modules using the checksummed fixture sources,
Helm and kubectl, with KUBECONFIG=/dev/null and PYTHONPATH=big-bang-bootstrap/tests.
These verify the real umbrella/child renders, installer permissions, native values,
Secret references, no license and closed-signup OIDC. The SSO modules also execute
Ansible against disposable HTTPS and kubectl fixtures for client/input lifecycle.
They do not execute the
operator or prove live storage, network enforcement, login or restore acceptance.

## Integrated Portal pilot

The [native context acceptance check](../../authorization/sso/mattermost/context/README.md)
verifies the configured private team/channel, exact reviewed membership and
channel-locked incoming webhook without changing access. Portal shares its tenant
context with GitLab, Grafana and ntfy; tenant viewers may participate in channels
and see their alerts but are not direct notification subscribers. Native
provisioning, identity linkage and cross-tenant denial remain live acceptance,
not capabilities implied by Keycloak login or source-only fixture checks.


## Pragmatic rollout order and approval scope

**Staged, not deployed:** app/operator remain disabled and suspended; neither is
selected by a cluster root. Context inspection/reconciliation source and a
disposable vendor-binary permission test do not change that status.

1. Keep the current Big Bang chart and Registry One image references, per the
   owner's lab decision. Record the security patch gap in the
   [edition review](edition-review.md), and re-evaluate when Big Bang updates
   Mattermost references rather than independently substituting an image.
   Evaluation-versus-production entitlement remains separate from a lab walkthrough.
2. Stage dedicated app data using the repository's CNPG/PostgreSQL and S3-compatible
   storage patterns. Do not reuse GitLab credentials, database or bucket. Confirm
   actual deployed provider availability, free Longhorn capacity and compatible
   PostgreSQL version before choosing the app DB footprint. Current app requests
   alone are 2 CPU/4 GiB; database, filestore and operator capacity are additional.
3. Render the exact operator/installer RBAC and readiness network policy.
   Stock runtime reads span cluster-wide Secrets, workloads and native
   Mattermost resources; apply the candidate post-renderer and its namespace
   Roles together. Readiness emits unrestricted egress; replace that with
   reviewed API/DNS destinations from protected environment inputs before rollout.
   Keep the readiness job, rather than disabling checks to make installation pass.
4. Deliver dedicated DB/filestore/OIDC inputs through approved OpenBao/ESO scopes,
   with independent local-admin recovery custody. Resolve TLS, public CA trust,
   restricted routing and registry delivery. Keep signup closed.
5. After baseline acceptance, apply the approved global ordinary-member invitation
   restriction and exact channel memberships; verify actual tenant denial,
   linked login, PE visibility/history and scoped webhook delivery.

Ask for concrete approval **immediately before** each security-sensitive live batch,
with exact target identities, native IDs and resources resolved. Suggested scopes:

- Install the reviewed Mattermost operator in its dedicated namespace, explicitly
  disclosing its rendered cluster-wide Secret/workload authority and installer
  role bindings; apply the reviewed readiness network rules. This is not a claim
  of namespace-confined operator trust.
- Deliver only the named Mattermost runtime credentials to its namespace and
  configure the specific Keycloak client/redirect/TLS endpoint. Identify storage
  destinations and consumers; never bundle unrelated secrets or applications.
- Remove private-channel invitation management from the global ordinary
  `channel_user` role, affecting ordinary members across the Mattermost server,
  then apply the reviewed exact channel membership diff. Tenant viewers still
  participate and see channel alerts; all platform engineers join each tenant
  channel with history. Do not grant native administrator roles as a shortcut.

These are approval templates, not requests already approved or executable
commands. Stop at the relevant approval boundary. Preserve existing live
applications and data throughout.

## Operator runtime authority

The unchanged Big Bang 3.35.1 / operator 1.25.9-bb.1 Registry One image starts
cluster-wide informers. `WATCH_NAMESPACE` is not implemented. Replacing its
ClusterRoleBinding with a namespaced RoleBinding alone would prevent startup.
The owner's approved lab scope is global reads with writes restricted as below;
this source remains disabled/unselected until the application rollout is prepared.

| Authority | Effective scope |
| --- | --- |
| `get/list/watch` | Cluster-wide Pods, Services, ConfigMaps, Secrets, ServiceAccounts, PVCs, Deployments, ReplicaSets, Jobs, Ingresses, IngressClasses, Roles/RoleBindings and the three Mattermost CR kinds |
| App/workload mutations | `mattermost` namespace only; explicit resource/verb lists in `prerequisites/runtime-rbac.yaml` |
| Leader election | Lease creation in `mattermost-operator`; `get/update` only `b78a986e.mattermost.com`; leader-event `create/patch` in that namespace |
| IngressClass exception | `delete` only cluster-scoped `IngressClass/mattermost`; no class create/update/patch |
| Other operator APIs | No MySQL/MinIO operator, CNPG, namespace-management, ClusterRole-management, impersonation, bind or escalation authority for the runtime ServiceAccount |

**Global Secret reads expose credential values, not just metadata. A compromised
operator could use those credentials to gain capabilities beyond its own scoped
writes. This reduces direct mutation scope; it is not a security boundary against
credential-mediated escalation or a multi-tenant isolation claim.**

The exact named IngressClass exception is necessary because upstream
`controllers/mattermost/mattermost/mattermost.go:checkMattermostIngressClass`
cleans up a class named after the CR even when ALB is disabled. The app CR must
remain named `mattermost`. A platform-managed Traefik IngressClass may be
referenced by the namespaced Ingress, but that does not suppress the stock cleanup
call. Before applying the grant, verify `IngressClass/mattermost` is absent or
belongs to this app; never point this cleanup exception at an unrelated class.
Global cached IngressClass list/watch cannot be resourceName-restricted.

Use external PostgreSQL and either external S3 or a pre-provisioned
`fileStore.externalVolume` PVC in the same namespace. The latter code path only
reads the PVC and does not call the MinIO operator. The runtime policy does not
manage database StatefulSets or a CNPG Cluster. Backend installers own those
resources separately; enabling operator-managed MySQL/MinIO requires a new review.

### Ownership and deployment order

1. Keep the current Big Bang and Registry One pins. Do not build a custom operator.
2. Render `prerequisites` and deliver its two runtime Roles/two RoleBindings using
   the platform's approved foundation mechanism before operator startup.
3. Keep `candidate-values.yaml`'s post-renderer in the effective Big Bang values.
   It replaces the existing upstream ClusterRole rules; its ClusterRoleBinding and
   ServiceAccount are unchanged. Flux owns the patched chart resources. Namespace
   Roles/Bindings are foundation-owned, not injected by a manual live patch.
4. Render the actual HelmRelease and apply its Kustomize post-renderer offline.
   The test compares every other object and image to the unmodified native render.
   Never install this image using the raw chart RBAC while omitting the patch.
5. Verify leadership, app reconciliation/restart and API authorization after
   deployment. Check unrelated-namespace writes, other IngressClass deletion and
   cluster RBAC changes are denied. Global Secret reads are intentionally allowed.
   Do not print Secret contents during validation. Fix narrowly if actual API
   requests are denied; do not restore the vendor wildcard role as a shortcut.

The pre-existing **installer** identity is separate: it has named bind/escalate
permission for the Helm-managed operator ClusterRole. This change does not add to
that installer authority. Installer privilege is not evidence that runtime access
is namespaced; review the post-rendered runtime role itself.

### Upgrade guard and verification limits

`security.test_mattermost_operator_scope` renders the pinned umbrella/child charts,
executes the Flux-compatible Kustomize patches, checks unchanged images/objects,
checks bindings and the single named global mutation, and fingerprints the raw
vendor RBAC. It also keeps the candidate out of the selected cluster root.
Run with the checksummed pinned sources, Helm on PATH, `KUBECONFIG=/dev/null` and
`PYTHONPATH=big-bang-bootstrap/tests`:

```sh
python3 -m unittest security.test_mattermost_operator_scope security.test_mattermost_review -v
```

For every Big Bang operator/app reference update, review the raw RBAC fingerprint,
controller watches, lease name, IngressClass cleanup and external-storage paths
before updating expectations. A rules replacement can otherwise hide new upstream
requirements. Revisit the app security patch gap at the same time. This maintained
RBAC overlay uses supported Flux post-rendering, not an upstream namespace-mode
feature. Offline checks do not certify startup, reconciliation, storage, SSO or
notification delivery. No ticket requiring those live outcomes is complete merely
because these checks pass.
