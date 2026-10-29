# PostgreSQL and Keycloak stage

Builds on Headlamp without tenant enrollment or OpenBao. Configure `identity/` storage node/path/class, DNS/TLS hosts, database inputs and registry references for the selected physical cluster. The retained static 4 GiB local PV is a non-HA reference: retaining a PV does not provide backup or failover. Review placement, ownership and storage capacity before choosing it.

Use `ansible/identity-foundation.yaml` only after a concrete approval for scoped installer permissions, storage, secrets and routes. Deploy database before enabling Keycloak and validate persistence/HTTPS before configuring API OIDC. Existing credentials remain external. One-shot realm initialization must not be rerun against an adopted realm. See the identity live plan.
