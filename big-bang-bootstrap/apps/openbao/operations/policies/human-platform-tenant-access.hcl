path "tenants/data/*" {
  capabilities = ["create", "read", "update", "delete"]
}
path "tenants/metadata/*" {
  capabilities = ["read", "list", "delete"]
}
