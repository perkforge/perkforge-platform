# Portal identity and workload boundary — executable, inactive

This directory is **outside every active Fleet path and tenant catalog index**.
The renderer has no apply mode, network client, secret-generation path or activation
flag. `contract.yaml` accepts only `activation: disabled`. Ordinary invocation emits
a short plan. `--write` regenerates review files locally; it cannot contact the lab.
Merging this directory changes no currently deployed resource.

## Follow the configuration

1. `contract.yaml` is the platform source of issuer, browser client, API audience,
   exact portal origin/callback, Secret name/key, service identities, tenant commit
   and image approval. Existing realm is `perkforge`; groups are the existing Home
   paths. No client secret, admin credential or token belongs here.
2. `../../scripts/render-portal-identity.py` validates the contract and renders the
   committed `generated/` files from platform-owned templates. Unknown fields,
   credentials, HTTP endpoints, moving Git refs and an enabled activation fail.
3. `generated/resources.yaml` includes an **immutable platform ConfigMap** named
   `portal-platform-values`, paused scoped Fleet registration, service identities,
   namespace Role/Binding, deny-by-default network policies and four native
   `admissionregistration.k8s.io/v1` ValidatingAdmissionPolicies with Deny bindings.
4. `generated/tenant-fleet-reference.yaml` is the exact tenant bundle connection:
   `helm.valuesFrom` reads that ConfigMap's `values.yaml`. GitRepo targets do not
   support Helm values; no invented GitRepo field is used. The scoped deployer
   gets only named ConfigMap **get**, not mutation. Tenant PR #1 now includes this narrowly scoped reference; the platform and
   tenant changes remain independently reviewable and inactive.
5. `generated/helm-values.yaml` is the same non-secret values document for offline
   rendering. It supplies issuer/client/audience/Secret reference to the existing
   chart. The chart maps them to `OIDC_*` environment entries and the `client-secret`
   Secret key. Values precedence is convenience, never the authorization boundary.
6. `generated/identity-plan.json` is Keycloak **review data**, not a Kubernetes
   object or directly importable realm backup. It specifies disabled confidential
   browser/API clients, exact callback, S256, five-minute tokens, audience/group/
   client-role mappers and the required limited role-scope mapping. No role members
   are assigned, no client is created, and no key or secret is generated.

## What admission enforces

The actual workload—not the tenant's Helm input—is checked. Deployment and
ReplicaSet templates and final Pods (including ephemeral-container updates) must
retain the exact platform issuer/client/audience/origin, disabled GitLab source,
only the approved Secret key reference, exactly seven unique environment entries,
one approved image/container and the unprivileged `portal-runtime` service account.
No envFrom, command/args/lifecycle/exec-probe injection, init/sidecar/ephemeral
containers, volumes, token projection, extra Secret references, host access or
custom DNS is allowed. Security contexts remain non-root, read-only, capability-free
with RuntimeDefault seccomp. Service exposure is limited to the internal ClusterIP
and approved port. The deployer's write surface is Deployment/Service in exactly
`tenant-home-portal`, including rejection of scale/exec/token subresources.

These policies match the namespace name through `request.namespace`, not labels
that a tenant could change. The deployer-surface policy also matches its exact
principal across namespaces. No exemption is given to controller-created Pods;
controller mutations that violate the contract fail closed. This deliberately
narrow initial profile is incompatible with generic sidecar injectors and
interactive debugging; any exception belongs in platform review.

`imageDigest: null` means there is no approved image. The rendered workload image
validation is literally `false`: no placeholder digest is presented as deployable.
Tests alone substitute a synthetic digest into an in-memory contract. Even with a
future approved digest, GitRepo remains paused and Helm `enabled` remains false.
All generated files are review material until the activation gates below are met.

## What this cannot establish

The application receives its own low-privilege OIDC client secret. Approved code
can read it; a compromised app/image/node/platform administrator may leak it.
Platform configuration does **not** make arbitrary tenant code trustworthy. A
future privileged API must independently validate issuer/signature/audience/client,
roles, tenant/resource authorization and allowed operation server-side, outside
any tenant-editable trust configuration. Never supply Keycloak/GitLab admin
credentials to this workload. No privileged API capability is implemented here.

RBAC keeps other tenants out of this namespace; admission blocks arbitrary workloads
from mounting secrets here. This is a shared-kernel boundary, not defense against
node/cluster admins. Existing pods are not retroactively repaired by admission.
Schema/CEL tests do not prove live API defaulting, webhook ordering, Fleet controller
impersonation, race-free activation, CNI enforcement, provider tokens or load limits.

## Offline checks

```
python3 local-lab/scripts/render-portal-identity.py
python3 local-lab/scripts/render-portal-identity.py --check
python3 local-lab/scripts/render-tenant-foundation.py --check
python3 -m unittest discover -s local-lab/tests -v
# Install requirements-test.txt in an isolated environment first:
python3 local-lab/tests/validate_portal_schemas.py
cd local-lab/tests/portal-cel
GOMAXPROCS=1 GOMEMLIMIT=256MiB go test -p=1 ./...
```

Go dependencies are locked at Kubernetes v1.36.5, matching the recorded RKE2 target.
The native admission compiler/evaluator executes the **generated CEL strings** on
positive Helm-rendered objects and negative mutations, not a Python approximation.
Schema checks use pinned upstream Kubernetes 1.36.5 and Fleet 0.16.0 definitions,
reject unknown fields, and interpret the Kubernetes IntOrString extension. The
Rancher FleetWorkspace schema is not covered; it follows the existing repository
convention. Upstream provenance is in `tests/fixtures/portal/schemas/README.md`.

## Activation prerequisites — no activation performed

- Inspect fresh capacity; provision namespace/project/quota through the existing
  Home catalog renderer with restricted Pod Security `v1.36`. This change does not
  alter its active allocation or create the namespace. Review existing workload
  cleanup/order before introducing a new admission boundary.
- Resolve **Fleet/Helm release Secret storage** without broad tenant Secret grants.
  Current RBAC deliberately cannot manage release Secrets. This is an unresolved
  installation blocker, not permission to widen access. Validate agent identities,
  named ConfigMap loading, workspace mapping and effective Policy unions offline/
  in an independently authorized isolated runtime before enabling anything.
- Review/build/scan an application image and record its real digest. Verify the
  installed API versions, policy type-check status and native admission behavior in
  an authorized isolated test; include negative requests after all mutating webhooks.
- Configure trusted HTTPS Keycloak separately. Current provisioning uses HTTP and
  Keycloak is paused; neither is changed here. Approve client/role-scope/member
  setup and secure delivery of only `portal-oidc/client-secret`. No automatic Home
  group grants are inferred from a group name.
- Approve internal TLS ingress and exact identity egress; current policies allow
  DNS only and deliberately block login/network ingress. Add only verified peers/
  ports, test CNI denial, and keep GitLab disabled.
- Apply platform controls **before** any secret or tenant workload; verify controls
  are effective; then review a separate change enabling the chart and unpausing the
  immutable Git pin. This renderer intentionally provides no one-command activation.

Fleet 0.16's schema does not include the older `allowNamespaceCreation` field seen
in the existing Nextcloud convention. New portal output does not rely on it;
namespace authority is excluded by RBAC and admission. Existing Nextcloud files
are untouched and require separate version/live-behavior review.

## Fleet source verification and version scope

These are **target-version** checks, not a new observation of running versions.
Kubernetes 1.36 is recorded in the catalog/handoff; the evaluator is pinned to
1.36.5. Fleet 0.16.0 is the explicit schema/source compatibility target; activation
must verify the installed Fleet/Rancher CRDs and agent behavior before using it.

In Fleet 0.16's [`install.go`](https://github.com/rancher/fleet/blob/v0.16.0/internal/helmdeployer/install.go),
`getValues` honors the ConfigMap namespace/key and fails if the object/key is absent.
Our reference fixes `tenant-home-portal/portal-platform-values`, key `values.yaml`;
it is not a copied downstream resource. The client is built from the Helm config's
REST getter, which [`getCfg`](https://github.com/rancher/fleet/blob/v0.16.0/internal/helmdeployer/deployer.go)
constructs with the explicitly requested deployer identity. Thus the Role grants
only `get` on that named ConfigMap. It never grants broad ConfigMap/Secret reads.

Source values override earlier values, but a tenant can change its bundle, remove
the reference or add later sources. The admission contract remains the enforcement
layer. Fleet template-only mode skips cluster lookups, so offline Helm tests feed
the same generated ConfigMap data explicitly; they do not claim to test a real
Fleet fetch. That source uses Helm4 internally; the dependency-free chart is tested
with Helm3.19 offline, and installed Fleet rendering remains an activation check.
The same Helm configuration uses a Secret release driver, preserving the explicit
release-storage permission blocker rather than silently broadening its Role.
