# Proposed physical Portal records only; not old home/tenant-home-portal data.
path "tenants/data/tenant-portal/oidc" {
  capabilities = ["read"]
}
path "tenants/data/tenant-portal/registry/ghcr" {
  capabilities = ["read"]
}
path "tenants/data/tenant-portal/tls" {
  capabilities = ["read"]
}
path "auth/token/lookup-self" {
  capabilities = ["read"]
}
