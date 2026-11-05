# Headlamp initial Kubernetes-token stage

Stacked after OpenBao; chart **0.45.0-bb.1**, application **0.45.0**, existing
immutable source/checksum pins retained. The `clusters/local-headlamp` stage selects a single worker-hosted
Headlamp with bounded requests. Observed v0.14.0: deployment and temporary-admin authentication-path test passed
2026-11-01 17:11:21 UTC. Headlamp remains localhost-only, without ingress/SSO.

The active ConfigMap no longer imports `oidc.yaml`. That file and the prior proven
Headlamp/Keycloak group-to-Kubernetes-RBAC fixtures remain for the separate
identity review. No Keycloak dependency, OIDC client, human RoleBinding,
cluster-admin service account or auth-bypass flag is introduced. Headlamp's runtime
service account has no application RBAC grant; the separately applied installer
can manage only the reviewed namespaced chart resources and Helm release storage.
The selected render is ServiceAccount, Service and Deployment, with no Helm
lookup, chart-created Secret, role or binding. Existing Registry1 pull-Secret
delivery remains explicit, redacted and separate from deployment.

## Activation and initial administration

1. After separately approving an exact published release/target, apply
   `configuration/ansible/headlamp-prerequisites.yaml` with `foundation_apply=true`.
   Reuse only the approved Registry1 delivery mechanism if the namespaced pull
   Secret is absent; no credential is authored or copied by this draft.
2. Promote the existing source and verify fresh Headlamp/parent readiness and
   worker placement. Do not rerun bootstrap or configure API OIDC implicitly.
3. Initially keep ingress off. A separately approved loopback-only port-forward
   provides access to the UI over the authenticated Kubernetes transport.
4. **Headlamp has no standalone admin username/password.** Token login uses a
   Kubernetes bearer identity and its actual RBAC. Existing administrator
   kubeconfig client certificates are not an invented UI password. Before login,
   choose an approved existing suitable token identity or explicitly review a
   short-lived, narrowly time-bounded bootstrap identity and revocation. No
   persistent cluster-admin service account/token is created as a shortcut.
   Token acquisition, scope, expiry/audience and protected cache delivery require
   a separate action-specific approval. Until then admin-login acceptance is
   **pending**, even if the Deployment is Ready.
5. Verify actual allowed/denied API actions, then close the port-forward. No
   tenant permission or OIDC extension is authorized. Browser ingress and its
   current physical TLS Secret remain separate later approval if needed.

After deployment success, include the shared [health and capacity acceptance](../../ansible/README.md#health-and-capacity-acceptance-after-every-app)
report: per-node usage versus requests/limits, node/pod readiness and failures,
Longhorn disk/replica headroom, and a comparable delta from the previous app.
Capture evidence automatically within the approved deployment/acceptance scope.

The temporary cache records credential type/status, never an imaginary password.
A later human OIDC workflow must align Headlamp and kube-apiserver issuer,
audience, username and full-path group claims. Headlamp forwards the identity;
Kubernetes RBAC authorizes it. Reuse the earlier proven pattern rather than
assuming UI OIDC settings alone configure the API server.

Sources: [Headlamp in-cluster installation](https://headlamp.dev/docs/latest/installation/in-cluster/),
[Keycloak integration](https://headlamp.dev/docs/latest/installation/in-cluster/keycloak/).
Existing useful API/identity configuration and tests are preserved; no competing
direct Headlamp deployment installer remained to delete.

Use the [ordered app stages](../../ansible/README.md#ordered-app-stages); the default local root leaves Headlamp off until its separately approved stage.

## Executed temporary-admin acceptance

The separately approved [Ansible operation](../../ansible/headlamp-access-smoke.yaml)
is disabled by default. The operator establishes localhost-only forwarding after
exact-stage/deployment readiness. It creates a unique SA (automount false) and
binding to existing cluster-admin, requests exactly 3600s via TokenRequest, records
actual expiry and caches the token owner-only outside Git. This is powerful temporary
bootstrap authority, not a platform role or runtime/installer permission.

The [verification script](../../ansible/files/verify-headlamp-access.py) checks
subject/UID/lifetime, then exercises the real pinned Headlamp cookie-login and API
proxy. SelfSubjectReview proves the dedicated identity; access reviews prove admin
capability without reading Secret values or modifying workloads. Anonymous access
is denied. The actual test passed; **personal browser login was not observed**.

Ansible always invokes [UID-guarded cleanup](../../ansible/headlamp-access-cleanup.yaml)
for recorded successful creations, binding first then SA, refusing replacement UIDs.
Absence and denial of the old token passed. Forwarding was closed by the operator
runner. No token Secret or persistent cluster-admin account remains. Cached token
metadata is marked revoked; this is not a reusable login or break-glass credential.
Operator owns temporary-file cleanup. Another access session, permanent access or
OIDC requires approval. Never reuse runtime/installer tokens as human credentials.

[Offline tests](../../../tests/security/test_headlamp_access_smoke.py) cover the
verifier's cookie/revocation path, wrong identity/excess lifetime rejection, actual
Ansible cleanup success/replacement refusal and the no-action default. They do not
replace the recorded live API test or prove a user's browser rendering.
