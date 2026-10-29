# Physical local identity stage

Adds Keycloak-backed Headlamp HTTPS/OIDC to the package stage. `identity/context.yaml` holds the explicit issuer, realm, Headlamp client, callback and origin; keep routes, RKE2 OIDC config, browser names and CA trust consistent. All example hosts/nodes are operator inputs. No personal endpoint is assumed.

`identity/foundation` and routing/storage inputs are platform-owned. Installer identities remain scoped separately from users. The exact platform admin group receives built-in cluster-admin; developers retain Headlamp-namespace read access and no-grants users receive no implicit access. Tenant deployment/workload identities do not inherit platform-admin.

Use [LIVE-PLAN.md](LIVE-PLAN.md) for the approval boundary and [WORKSTATION.md](WORKSTATION.md) for client trust. API token authentication and Kubernetes RBAC are separate from UI login. Test actual allowed/denied API calls, not hidden buttons.
