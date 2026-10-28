path "tenants/data/home/tenant-home-portal/registry/ghcr" {
  capabilities = ["read"]
}
# ESO validates its own token before provider reads; this grants no KV expansion.
path "auth/token/lookup-self" {
  capabilities = ["read"]
}
