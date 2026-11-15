path "auth/token/lookup-self" { capabilities = ["read"] }
path "sys/policies/acl/tenant-identity-bootstrap-keycloak-v1" { capabilities = ["read"] }
path "platform/metadata/identity/keycloak/portal-membership-reader-v1" { capabilities = ["read"] }
path "platform/data/identity/keycloak/portal-membership-reader-v1" { capabilities = ["create", "update", "read"] }
