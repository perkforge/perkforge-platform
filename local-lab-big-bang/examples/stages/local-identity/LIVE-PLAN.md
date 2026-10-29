# One bundled live approval (not granted by this PR)

Approve the following **after this PR is merged/released; image gates must pass before workload apply**:

1. Recheck cluster UID/host and per-node capacity. Generate dedicated trial CA,
   leaf keys, distinct PostgreSQL superuser/app passwords, Keycloak bootstrap
   password, Headlamp client secret and three trial-user passwords under the new
   owner-only ignored identity directory. Do not rotate/reuse old credentials.
   Approve Registry1 use only against verified registry1.dso.mil and delivery of
   `keycloak/private-registry`; existing Flux/Headlamp credentials stay intact.
2. Prepare only the new worker directory (verified UID/GID, 0700, SELinux label),
   retained PV/PVC, namespace and scoped installer bindings. Deliver external
   `keycloak-database-existing` keys `postgres-password`/`password`,
   `keycloak-bootstrap-existing` keys `KC_BOOTSTRAP_ADMIN_USERNAME` (fixed
   `local-bootstrap-admin`)/`KC_BOOTSTRAP_ADMIN_PASSWORD`, TLS leaf Secrets
   `keycloak-local-tls`/`headlamp-local-tls`, public CA ConfigMap `headlamp/identity-ca`,
   and `headlamp/headlamp-oidc` key `OIDC_CLIENT_SECRET`. Readers of these Secrets
   can use the credentials. Nothing sensitive goes in Big Bang values/Helm history.
3. Install the NetworkPolicies and **Keycloak route only**. Select the published
   tag's `local-keycloak` stage on the existing root, explicitly resume it, wait for
   DB then Keycloak, inspect init errors without passwords and verify HTTPS issuer.
   Initialize the new owned realm/client/groups/three test users with the guarded
   Ansible play; no existing identity or external tenant is enrolled.
4. Approve browser/control-host name mappings and CA trust, API drop-in/public CA
   mounts, config backup and one control-plane restart. Verify API/admin access.
   Apply exact login RBAC, deploy `local-identity`, then add the Headlamp HTTPS
   route. Verify admin/developer/no-grants API matrix and browser behavior.
   The revised `local-platform-admin` ClusterRoleBinding grants built-in
   `cluster-admin` only to `oidc:/platform/admins`, including Secret reads and
   RBAC/impersonation authority. Developer/no-grants and tenant boundaries remain
   separate. Applying this expansion requires explicit live approval; publication
   does not grant it. Verify privileged mutation decisions with access reviews,
   without making test mutations. See README for named redundant RBAC cleanup.
5. Observe each startup for ten minutes. Capture timestamps, events and sanitized
   failure/cause/fix/verification notes in ignored local evidence, keeping failed
   attempts. Verify app DB role is non-superuser, then a separately planned safe
   restart preserves realm/client state. Do not delete PVC/PV or directory.

Stop on unexpected inventory/RBAC/host/issuer, API recovery failure, no readiness
within ten minutes, OOM/CrashLoop or sustained pressure. Existing trial thresholds:
host available <2048 MiB for 15s; node available <512 MiB; host PSI full avg10 >1%
for 30s; swap growth >256 MiB or swap IO >1 MiB/s for 60s. Capture evidence first.
Suspend only this stage's root/releases/sources and scale only its new Keycloak/DB
workloads to zero; preserve Flux, existing Headlamp and all retained data. If the
SSO switch fails, remove only the new Headlamp route and restore the previously
reviewed Headlamp-only values. API recovery may restore only this OIDC drop-in and
its backed-up host mapping, then restart control-plane RKE2; never run uninstall,
rebuild, or delete identity/storage. This containment scope needs the same approval.
