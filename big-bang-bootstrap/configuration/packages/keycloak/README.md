# Keycloak initial master-administrator stage

Stacked after OpenBao and Headlamp. Select Big Bang Keycloak chart
**7.3.2-bb.1 / Keycloak 26.8.0**, with its pinned PostgreSQL 18.12.4 chart dependency
and Iron Bank PostgreSQL 18.6 image. One application and one database instance,
worker placement and the existing 4Gi Longhorn prerequisite claim: **not HA**.
Application/database passwords remain external Secrets; no realm import runs at
server startup. No PerkForge groups, app clients, mappings or API OIDC settings
are activated by selecting the chart.

## Who does what and why

- Flux/Big Bang deploy Keycloak and PostgreSQL using `keycloak-installer`; its
  namespace-scoped permissions include the two exact database Secret lookups.
  It cannot grant cluster RBAC. The chart creates no runtime RoleBindings or
  credential Secrets with this selection. Existing synthetic lookup tests verify
  denial, absence and existing protected input behavior.
- Ansible owns namespace, database initialization ConfigMap, **Longhorn** PVC and
  optional Keycloak-only TLS ingress. Use `keycloak_storage_backend=longhorn`;
  the old static local-volume specimen is not the physical installation path.
  Its alternate render excludes the static PV/StorageClass/volumeName.
- The native PostgreSQL entrypoint runs the retained SQL only for empty PGDATA,
  creates a dedicated non-superuser `keycloak` role and gives it the application
  database. Existing databases need explicit migration/recovery, never delete the
  claim or rerun initialization to reset credentials.
- Ansible Admin API configuration owns the later PerkForge realm/groups/clients;
  Helm does not import competing definitions. Existing proven pilot mappings and
  allow/deny fixtures remain for the separate authorization MR. Do not run the
  old one-shot trial realm/users workflow as initial app installation.

## Protected first-install inputs and future approval

| Reference | Required content / custody |
|---|---|
| `keycloak/keycloak-bootstrap-existing` | `KC_BOOTSTRAP_ADMIN_USERNAME`, `KC_BOOTSTRAP_ADMIN_PASSWORD`; temporary **master realm** bootstrap administrator, not automatic PerkForge/platform membership |
| `keycloak/keycloak-database-existing` | Distinct nonempty `postgres-password` (database superuser) and `password` (dedicated application role); no values in Git, arguments or logs |
| `keycloak/private-registry` | Approved existing Registry1 pull credential delivered privately to this namespace; no new token or implicit cross-namespace copy |
| `keycloak/keycloak-local-tls` | Current physical-cluster hostname leaf/key, privately validated/delivered through gated `platform-tls.yaml`; never old trial keys or CA signing key |

Before promotion, separately approve exact release/target, capacity/storage,
namespaced prerequisites, credential generation/capture/delivery and TLS/route.
Do not overwrite conflicting Secrets or a populated database. No credentials are
created, read or cached by this draft; metadata remains pending. A small approved
delivery batch must validate exact Secret keys/nonempty values and protect all
runtime output. Independent database/realm recovery and temporary admin custody
are required before relying on the identity service.

Apply the existing `configuration/ansible/keycloak-prerequisites.yaml` with
`identity_foundation_apply=true`, `keycloak_storage_backend=longhorn`, and only
`keycloak_routing_apply=true` if the HTTPS route is approved. Keep
`identity_routing_apply=false`, `identity_access_apply=false`, and all realm/API
configuration gates off. This uses the existing Keycloak ingress manifest without
applying Headlamp ingress or Kubernetes group bindings. TLS terminates at the
existing trusted Traefik path; the authored backend is HTTP inside the cluster,
not end-to-end encryption. Do not weaken host/CA checks or expose a plain external
HTTP administration endpoint.

After exact source promotion, verify database readiness, application/parent/root,
trusted HTTPS `/auth/`, then privately verify initial master admin login. Reset or
replace temporary bootstrap access only under explicit approval, preserving
independent break-glass recovery. Initial login does not authorize realm-admin
for platform users or any app OIDC integration.

Sources: [Keycloak bootstrap/recovery](https://www.keycloak.org/server/bootstrap-admin-recovery),
[database configuration](https://www.keycloak.org/server/db),
[import/export timing](https://www.keycloak.org/server/importExport).
No competing direct Keycloak Helm installer remains; useful Ansible API and
recovery/identity tests are preserved rather than deleted as obsolete deployment.
