# OpenBao secrets management (issue #12, stage 1)

This is an **offline-tested, inactive configuration stage**, not a live service.
No active Fleet GitRepo selects the new bundles. Secret enrollment defaults to
`enabled: false`. Do not activate by merely uncommenting a path. No credentials,
OIDC clients, policies, mounts, audit devices or Kubernetes resources have been
created in the cluster by this change.

## Architecture and capacity checkpoint

Use the official OpenBao chart 0.30.6 / OpenBao 2.7.2 and official ESO chart/app
2.14.0. Retain the already approved Keycloak chart/configuration; this work does
not replace it. Fleet loads shared YAML and tenant overrides directly, with no
configuration generator, custom chart, shared Helm library or new controller.

Read-only observation on 2026-10-27: control working set 2944 MiB (80%), worker
2741 MiB (75%). Keycloak was already 1/1, and portal/Nextcloud deployments were
ready. Earlier documentation saying Keycloak is paused is stale. These are
snapshots, not reserved capacity. The proposal adds worker requests of 320 MiB
and limits of 640 MiB (OpenBao 256/512, one scoped ESO 64/128), plus runtime
and filesystem overhead. Do not raise VM RAM on the 14-GiB laptop. Recheck node
allocatable/requests/working sets, pod peaks, disk availability and OOM events
before approval; a cold Keycloak start or backup may consume the remaining
headroom. Prefer waiting for physical hardware if a safe margin cannot be shown.
There is no demonstrated load/capacity guarantee.

One OpenBao instance uses single-member integrated Raft on a retained 2-GiB
local-path PVC and a separate retained 1-GiB audit PVC. This supports Raft
snapshots, but is **not HA** and cannot recover from losing its VM disk without
an off-VM snapshot plus unseal material. No automatic unseal or operator is added.

| Actor | Authentication | Authority |
|---|---|---|
| Home human administrator | Keycloak OIDC, exact `/tenants/home/admins` group | CRUD only two explicitly enrolled Home namespace paths |
| Platform secrets operator | Keycloak OIDC, exact `/platform/admins` group | Platform mount plus separately removable tenant-access policy |
| ESO Home portal | Kubernetes auth, exact `openbao-sync` SA in `tenant-home-portal`, audience `openbao` | Read only one GHCR record |
| Fleet app deployer | Existing Kubernetes SA/RBAC | Existing app deployment scope; no OpenBao human role or ESO TokenRequest grant |
| Recovery/bootstrap operator | Separately approved temporary privileged session | Initialize/unseal, mounts, auth, policies and audit setup; never app credentials |

KV v2 mounts are `platform/` and `tenants/`. Paths within `tenants/` are
`<tenant>/<namespace>/<purpose>/<name>`. They are policy scopes, not OpenBao
enterprise namespaces. Human policies permit soft delete of data and deliberate
metadata deletion of their own secrets; no root metadata listing or policy/auth
administration is granted. UI users may need to navigate directly to their
allowed folder. Developers/viewers receive no secrets role by default.

OIDC roles in `roles/human-*.json` bind issuer-verified claims, `sub` identity,
client audience `openbao`, exact groups and exact redirects, with 15-minute
sessions bounded to one hour. A dedicated confidential Keycloak `openbao`
client must use authorization-code flow, PKCE and a full-path group mapper in
ID tokens/userinfo (`groups`); do not use realm roles or a caller-supplied tenant
claim as a path. No default privileged OIDC role. Configure discovery against
`https://keycloak.local-lab.test/auth/realms/perkforge`, the managed
realm name in the existing script. Trust the public CA and preserve
issuer/hostname verification. Never use TLS-skip-verify. Role JSON is native
OpenBao API input; it is not yet applied or proof of successful Keycloak login.

Platform initially gets both `human-platform` and
`human-platform-tenant-access`. Later remove the latter from its OIDC role,
revoke existing sessions and remove equivalent identity-group grants. This
restricts normal OpenBao access only: Kubernetes/host administrators can still
read workload Secrets or alter the service. Stronger separation needs separate
administrative ownership/cluster or encryption-key custody; do not claim this
policy change protects against cluster root.

## Namespace delivery and registry rotation

The first enrollment is Home portal only. `../secrets-config/` holds shared
values, explicit Home overrides and native Fleet YAML templates. It is separate
from active foundation configuration, so this stage changes no existing bundle.

A namespace-local SecretStore is preferable to a ClusterSecretStore here: it
cannot be referenced across namespaces, carries no shared static credential,
and uses a per-namespace bound Kubernetes role. ESO's supported scoped mode
limits its controller and Role to `tenant-home-portal`, with the controller pod
in `external-secrets`. Cluster stores, push secrets, cluster generators, webhooks,
role aggregation and servicebinding ClusterRole creation are disabled. CRDs are
still cluster-scoped schema installation and require approval. ESO retains the
standard controller's namespace-local Secret read/write access; it is not
restricted to a single output key by Kubernetes RBAC. The backend policy limits
what it can retrieve. Add another scoped enrollment/controller only with a
capacity review, not a wildcard ClusterSecretStore or namespace binding.

The default broad TokenRequest grant is disabled. Enrollment adds only
`create serviceaccounts/token` for named `openbao-sync`. That SA does not
mount a token or run application pods. OpenBao's own SA gets the official
`system:auth-delegator` binding for TokenReview, distinct from ESO/Fleet. Configure
Kubernetes auth using the in-pod rotating reviewer token and CA; bind namespace,
SA and audience using `roles/eso-home-portal.json`. Do not export reviewer JWTs
or grant TokenReview to application identities.

`tenants/home/tenant-home-portal/registry/ghcr` holds one property,
`dockerconfigjson`: a valid JSON string for `ghcr.io`, entered privately by the
operator. ESO maps it to `.dockerconfigjson` in the **existing** `portal-ghcr`
Secret, every minute. `creationPolicy: Merge` requires that Secret to exist and
be mutable; verify metadata/ownership and mutability before activation.
`deletionPolicy: Retain` keeps its last value on backend deletion/error. Removing
an OpenBao record does not revoke an existing Kubernetes credential. Deliberate
credential retirement requires a separately reviewed workflow.

GitHub issues/renews/revokes the GHCR token separately. Update its value in
OpenBao's UI or via private stdin/file input, never shell arguments, logs or Git.
A Secret refresh affects future image pulls; it does not restart existing pods
or renew the token at GitHub. Do not edit unrelated portal OIDC/database Secrets.
Nextcloud remains outside delivery enrollment; its existing immutable Secrets
and all data remain untouched.

Human ownership is broader than this first machine enrollment: Home can manage
records for its two listed namespace paths, but only the portal registry record
has a delivery mapping. Arbitrary application secret mappings require explicit
platform enrollment and per-path read policy review. Downstream app repos
continue to consume ordinary Secret names and need no foundation internals.

## Live prerequisites and approval bundle (not executed)

Before any live action, present one concrete approval plan covering:

1. Placement/capacity evidence; install only the new OpenBao/ESO resources and
   cluster-scoped ESO CRDs, with no VM rebuild, existing workload restart or
   unreviewed quota adjustment. Preserve portal and Nextcloud health baselines.
2. Leaf certificate issuance for OpenBao's browser hostname and internal service
   DNS (`openbao.openbao.svc`, `.svc.cluster.local`, plus required pod/service
   identities). Mount only `openbao-server-tls` into the server. Publish only the
   public CA in `openbao-ca` ConfigMap in the enrolled namespace. Do not copy CA
   private keys. Review internal DNS resolution for OIDC discovery, TLS chain,
   ingress route and exact redirect before exposing the UI. No ingress is staged
   in this PR; it must be reviewed with the security rules below.
3. Platform-owned default-deny NetworkPolicies with narrowly reviewed allows:
   Traefik and the scoped ESO pod to OpenBao 8200; OpenBao to DNS, the Kubernetes
   API TokenReview endpoint and Keycloak HTTPS; ESO to DNS, Kubernetes API and
   OpenBao HTTPS. Verify actual service/endpoints, Canal behavior and namespace/
   pod labels before authoring the final rules. No new internet or tenant-to-
   tenant egress. Do not grant Fleet app deployers writes to stores, mappings,
   RBAC, policies or the ESO SA; account for existing broad tenant admin grants.
4. Named recovery owner and independent backup custodian; private initialization
   capture, key shares/threshold/custody decision, unseal ceremony, root-token
   revocation after bootstrap, and a tested emergency access path. Keep shares
   off-cluster and separate from snapshots/client credentials. Never initialize
   twice or store root/unseal material in Fleet/Git/Kubernetes application Secrets.
5. Enable the two KV v2 mounts; apply reviewed HCL policies and native role JSON;
   create the dedicated Keycloak client/group mapper without unrelated migrations;
   enable OIDC and Kubernetes auth. Client credentials remain private. Platform
   policy is secrets management, not blanket `sudo` or auth administration.
6. Enable file audit at `/openbao/audit/audit.json` **before user use**; default
   HMAC protection, no raw secret logging. Define restrictive access, rotation,
   retention and off-VM shipping. A full/unwritable audit sink can stop requests;
   monitor storage and test handling. Allocate audit ownership explicitly.
7. Encrypted off-VM Raft snapshots daily and before changes; proposed seven daily
   retention copies, custodian-owned encryption and keys. Decide actual destination
   and recovery objectives, then demonstrate restore into an isolated instance
   with separate unseal material before real credentials are entrusted. Raft
   snapshots do not back up external Keycloak state, TLS keys or audit files;
   protect those separately. A disposable cluster does not make recovery optional.
8. Privately enter the GHCR record, validate existing pull Secret mutability,
   enable the single enrollment, verify rotation without printing values and
   revoke superseded GitHub credentials only after approved validation.

These actions are pending authorization and implementation of the final live
security/TLS wiring; they are not implied by chart rendering. No CA-key copying,
secret migration/deletion, init/unseal, credential issuance, auth grant or deployment
is authorized by this staged PR.

## Validation and later acceptance

`test_openbao_secrets.py` runs a local synthetic OpenBao dev server (never the
cluster) to prove Home CRUD, foreign tenant/platform/unowned namespace denials,
ESO read-only exact-path access, backend rotation visibility and later removal
of platform tenant access. It also renders both pinned official charts and
actual Fleet enrollment, testing disabled defaults, namespace RBAC, named
TokenRequest and rejection of a foreign remote path. CI downloads tools with
pinned checksums. Tests do not prove OIDC/Kubernetes login, network enforcement
or actual Kubernetes Secret refresh.

Before marking the complete issue In Review, collect private live evidence of:
OIDC allowed/denied groups and expired sessions; Kubernetes auth denial for
wrong SA, namespace and audience; wrong-store/cross-tenant path denial; ESO
Forbidden writes outside its namespace; direct Fleet deployer denials; owned
secret CRUD and deletion/retention behavior; a synthetic token value update
causing the existing pull Secret's resourceVersion/content digest to change
without changing its UID; a successful fresh private-image pull; validated TLS,
audit events and isolated backup restore. Preserve failed evidence and record
limitations. Only use synthetic values for public logs and CI.

Stage 1 can be reviewed as configuration and offline evidence. Issue #12 remains
In Progress until the separate approved live prerequisites and acceptance pass.

## Official references

- [OpenBao Helm](https://openbao.org/docs/platform/k8s/helm/) and [pinned chart](https://github.com/openbao/openbao-helm/releases/tag/openbao-0.30.6)
- [OIDC claims and roles](https://openbao.org/docs/auth/jwt/), [Kubernetes auth](https://openbao.org/docs/auth/kubernetes/)
- [Raft](https://openbao.org/docs/configuration/storage/raft/), [audit](https://openbao.org/docs/audit/)
- [ESO OpenBao provider](https://external-secrets.io/latest/provider/openbao/), [Vault-compatible KV configuration](https://external-secrets.io/latest/provider/hashicorp-vault/)
- [ESO multi-tenancy](https://external-secrets.io/latest/guides/multi-tenancy/), [Secret lifecycle](https://external-secrets.io/latest/guides/ownership-deletion/)
