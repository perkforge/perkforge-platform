# Local identity trial

Prepared from platform v0.4.0; **nothing in this PR activates it**. The running
`local-headlamp` root and `dev` remain unchanged. `local`/`local`/`il2` are the
cluster/environment/profile selections; il2 does not claim authorization.

## Follow the files

1. `../local-keycloak/bootstrap-inputs.yaml` selects Headlamp + Keycloak/PostgreSQL;
   existing Headlamp stays private. Existing bootstrap still seeds a **paused** root.
2. `../local-keycloak/release.yaml` composes shared → app Keycloak/database → RKE2
   provider → il2 → local Headlamp → identity values, in that order. Last wins.
3. `bootstrap-inputs.yaml` selects the final stage. Its last `sso.yaml` layer enables
   Headlamp OIDC. This is the same Big Bang release, not another release owner.
4. `foundation/` is Ansible-owned namespace/installer RBAC and retained storage.
   `routing/` and `access/` are **separate explicit security approvals**, not app
   installer permissions. Neither root contains them automatically.
5. `../../identity/` holds the realm/client, API trust and real-token test contract.
   `../../ansible/identity-*.yaml` default to no writes and no credentials/API access.

Big Bang **3.35.1**, Headlamp **0.45.0-bb.1** (image v0.45.0), Keycloak
**7.3.2-bb.1** (26.8.0) and its vendored PostgreSQL chart **18.12.4** (Iron Bank
18.6) remain pinned. No chart vendoring or generated deployment YAML is added.
OpenBao, tenants, portal, mesh, cert-manager and storage controllers are excluded.

## Resource and storage budget

| Worker workload | CPU request / limit | RAM request / limit |
| --- | --- | --- |
| Headlamp (already running) | 100m / 500m | 128 / 256 MiB |
| PostgreSQL | 250m / 500m | 256 / 512 MiB |
| Keycloak | 250m / 1000m | 768 / 1536 MiB |
| Added database waiter (init only) | 10m / 50m | 32 / 64 MiB |

The init container does not overlap Keycloak and is smaller than its request.
Steady selected apps total **600m / 1152 MiB** requests, **2000m / 2304 MiB** limits.
The prior worker baseline already includes Headlamp: 1000m/768 MiB requests becomes
**1500m/1792 MiB**, leaving **500m/1861 MiB** of its 2000m/3653 MiB allocatable.
Reserve at least 250m/512 MiB of that remainder for system variation. A Headlamp
rollout surge adds 100m/128 MiB requests and 256 MiB cap. Do not roll both identity
StatefulSets together or treat CPU limits/requests as measured memory usage.

Read-only preparation measured control/worker working sets **2188/1069 MiB**,
host MemAvailable **2774 MiB**, swap occupancy **9879 MiB**, and 0–4 KiB/s swap-in,
zero swap-out in the two sampled one-second intervals. These are a snapshot, not
startup evidence. The RKE2 single-control-plane restart needs fresh measurements.
Existing VM RAM is already backed by the host; do not add all container limits to
host usage again. Guest/page-cache/startup peaks and actual requests must be monitored.

The static **4 GiB** PVC/PV is prebound to a new directory on `cks-worker`:
`/opt/local-path-provisioner/bigbang-keycloak18`. No dynamic provisioner or helper
Pod is required. `Retain` means no automatic data removal on release/PVC deletion.
Capacity is an advertised bound, **not a directory quota**. Worker disk loss loses
this database; no HA, replication, resize or tested backup/restore is supplied.
Never initialize an existing nonempty directory or clear PGDATA to fix startup.

## Identity and authorization

The browser, Headlamp and Kubernetes API use the exact issuer
`https://keycloak-local-il2.local-lab.test/auth/realms/perkforge`, client/audience
`headlamp-local`, signed ID tokens (RS256), stable `sub` usernames prefixed `oidc:`,
and full-path groups prefixed `oidc:`. API validation also requires `azp` to equal
the client. Headlamp uses authorization code + S256 PKCE with a confidential client;
implicit flow, password grant and service accounts are disabled for this client.
Only the separately scoped bootstrap admin uses the established Admin API pattern.
The one-shot realm play refuses any existing realm instead of overwriting users,
passwords or ownership. Later changes need reviewed Admin API tasks, not delete/import.

Existing `/platform/admins` and `/platform/developers` concepts are retained:

| Identity | Trial grants |
| --- | --- |
| admins | Built-in Kubernetes `cluster-admin` across the cluster, including all tenant namespaces |
| developers | Read Pods/Services/Deployment/ReplicaSet/StatefulSet in headlamp only |
| no-grants test user | Authenticate, but no workload access |

Only the exact authenticated group `oidc:/platform/admins` receives this binding. Platform
admins are trusted full cluster administrators: Secrets, workload mutation, RBAC
and impersonation are included. This does not assign a Keycloak realm-admin role;
Kubernetes cluster-admin can nevertheless obtain service credentials from Secrets.
The parent `/platform`, developers, tenant groups and Headlamp service account do
not inherit this grant. Developer/no-grants restrictions above remain unchanged.
Like the Fleet tenant RoleTemplates, tenant grants remain scoped; this explicit
platform-admin mapping is separate from those tenant roles. No tenant enrollment
or membership changes are included.

The paused live trial confirmed a PostgreSQL server-side Secret lookup. The new
loopback regression additionally finds a second lookup of `keycloak-postgresql`,
even though an external Secret is selected. A single-name GET rule is therefore
insufficient. The installer rule grants `get` on exactly those two names in
`keycloak`, with no Secret list/watch or other Secret access in that namespace.
Existing Helm-history permissions in `bigbang` are unchanged. These are trusted
installer permissions, not UI/user grants. Live application/retry is separate.

No UI service-account binding or unsafe-token fallback is enabled. The trusted
installer can indirectly mount namespace Secrets through workloads; it is never a
login/tenant identity. No admission or broader tenant-isolation claim is made.
Restricted namespace discovery may reveal a Headlamp usability gap: test direct
namespace/deep links for restricted users; do not broaden their roles for UI errors.

The revised access files are not live until separately approved and applied.
`kubectl apply` does not prune the former `local-platform-health` binding/role,
`local-identity-scaler` role or the four `identity-admin-*` namespace bindings.
They become redundant after the new binding; remove only those named old objects
in a separately reviewed activation step after verifying the intended group.
Tests model built-in RBAC offline; live authorization and Firefox checks must be
repeated after activation. Privileged mutation tests use access reviews only.

## TLS and API prerequisites

Existing RKE2 Traefik keeps 80/443. Two `websecure` Ingresses use external TLS
Secrets and the exact names `keycloak-local-il2.local-lab.test` and
`headlamp-local-il2.local-lab.test`. No HTTP route, new ingress controller, or
certificate controller is added. TLS terminates at Traefik; backend HTTP and the
PostgreSQL connection are **not encrypted** in this bounded trial.
The three ingress NetworkPolicies use the observed `rke2-traefik` Pod label,
permit Keycloak→PostgreSQL, and leave egress unchanged. Network enforcement,
Traefik source identity and forwarded-header handling still need live tests.

Provision a dedicated trial CA and leaf certificates externally after approval.
Keep its private key on the workstation; only leaf keys enter Kubernetes. Browser
trust is explicit; never click through an unverified issuer certificate. Headlamp
mounts a public `identity-ca` ConfigMap and uses both its OIDC CA flag and
`SSL_CERT_FILE` for discovery/refresh. The API uses the same public CA through
`oidc-ca-file`. RKE2 automatically mounts that existing flag-referenced file
read-only; do not also declare it in `kube-apiserver-extra-mount+`. The explicit
read-only `/etc/hosts` mount remains necessary for the issuer name mapping.

`../../identity/rke2-oidc.yaml` is a reviewed **input**, not auto-applied by any
playbook. It appends API arguments/mounts through an RKE2 config drop-in. Before
installing it, inspect all existing config/drop-ins/CLI settings without logging
credentials; refuse conflicting OIDC/authentication configuration or later overrides.
Preserve the admin certificate kubeconfig and take private config backups. Map the
issuer to 192.168.122.201 in the control host's managed `/etc/hosts` block; the
read-only static-Pod mount makes that mapping visible to the API. Headlamp has an
explicit hostAlias. Host/browser DNS mappings and public CA trust need approval; see the small
[workstation instructions](WORKSTATION.md).
Restart **only cks-control's rke2-server** after issuer discovery/JWKS work from
its network context. Expect brief API downtime; worker RKE2 need not restart.
Verify the generated API static-Pod flags, CA and issuer reachability after restart.
Also check every container's mount destinations are unique before accepting
readiness. A prior trial's duplicate explicit CA mount invalidated the API Pod;
the new drop-in was disabled and the prior configuration recovered. Flux restarted
during that outage; retained identity data and the existing Headlamp were preserved.
The regression models the pinned RKE2 auto-file/extra-mount contract and rejects
the prior input. It does not prove a corrected live restart has succeeded.

Pinned source: [automatic file discovery](https://github.com/rancher/rke2/blob/e1d699d2c3a3d3c1f3247c4f9eb140f20d369776/pkg/podtemplate/podtemplate.go#L280)
and [static-Pod file injection](https://github.com/rancher/rke2/blob/e1d699d2c3a3d3c1f3247c4f9eb140f20d369776/pkg/executor/staticpod/staticpod.go#L596).
No API serving certificate or existing admin credential needs replacement.

## Offline and future live tests

Run the existing full suite with the checksummed sources and dependency checkouts
as documented in [the preflight instructions](../../../preflight/README.md). The new tests render
both children through real umbrella values, inspect storage/Secret/env/probe wiring,
verify resource totals and RBAC allow/deny rules, and run all new Ansible plays in
no-write check mode. A regression runs the actual pinned chart with `--dry-run=server` against a
loopback synthetic API. It reproduces the first denied lookup, then exposes the
second chart-name lookup after granting only the external Secret GET. Both
insufficient policies fail; the two-name rule renders successfully while the absent
chart-name Secret returns 404. This validates the actual chart request paths
against a permission model, not a live grant or proof of the Kubernetes authorizer. These tests do not prove image startup or login.

Before live apply, inspect the exact authenticated Keycloak/PostgreSQL image
manifests/config/digests and PostgreSQL UID/NSS-wrapper/entrypoint contract. No
Registry1 credential was transmitted for this PR. The package adapts a Bitnami
chart to a native image: the native entrypoint must support `POSTGRES_PASSWORD_FILE`,
`/docker-entrypoint-initdb.d/*.sql`, psql `\getenv` and arbitrary UID 1001. A public
Iron Bank source fetch returned a sign-in page; that is **not** runtime verification.
Stop if these checks disagree, rather than changing UID/privileges/images silently.
The SQL creates a separate NOSUPERUSER Keycloak role; PostgreSQL superuser and app
passwords must be different. Container readiness alone does not prove that role.

After browser logins, `identity-verify.yaml` consumes owner-only signed ID-token
files, verifies the actual API subject/groups and positive/negative HTTP responses,
and uses SelfSubjectAccessReview for mutation/subresource decisions. Supply real
expired, wrong-audience and wrong-issuer signed tokens; a tampered JWT is only an
invalid-signature test. Do not enable password grants to obtain test tokens.
No valid token, refresh token, browser HAR or cookie enters Git or ordinary logs.
Browser/deep-link checks, logout/expiry, actual denied dry-run writes, persistence
across a controlled Pod restart, and DB role verification remain live gates.

## Live activation

See the [single bundled approval and containment plan](LIVE-PLAN.md).
No live operation is authorized by this PR.

## Primary references

- [Pinned Big Bang Keycloak package](https://repo1.dso.mil/big-bang/product/packages/keycloak/-/tree/7.3.2-bb.1)
  and its vendored chart define the render; upstream native-image behavior still
  needs checking against the actual Iron Bank image.
- [Native PostgreSQL entrypoint](https://github.com/docker-library/postgres/blob/master/docker-entrypoint.sh)
  explains fresh-data initialization and superuser semantics; it is not proof of
  Iron Bank's binary contents.
- [Headlamp OIDC](https://headlamp.dev/docs/latest/installation/in-cluster/oidc/)
  forwards the user's token; [Kubernetes authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
  validates it independently. The [pinned Headlamp parser](https://github.com/kubernetes-sigs/headlamp/blob/v0.45.0/backend/cmd/server.go)
  splits CLI scopes on commas; `sso.yaml` uses that format.
- [RKE2 configuration/drop-ins](https://docs.rke2.io/install/configuration) and
  [server mounts/arguments](https://docs.rke2.io/reference/server_config) define
  the append/restart contract.
- [Keycloak hostname](https://www.keycloak.org/server/hostname) and
  [reverse proxy](https://www.keycloak.org/server/reverseproxy) explain exact
  public issuer URLs and the edge-TLS limitation.
