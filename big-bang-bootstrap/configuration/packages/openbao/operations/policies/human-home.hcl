path "tenants/data/home/tenant-home-portal/*" {
  capabilities = ["create", "read", "update", "delete"]
}
path "tenants/metadata/home/tenant-home-portal/*" {
  capabilities = ["read", "list", "delete"]
}
path "tenants/data/home/tenant-home-nextcloud/*" {
  capabilities = ["create", "read", "update", "delete"]
}
path "tenants/metadata/home/tenant-home-nextcloud/*" {
  capabilities = ["read", "list", "delete"]
}
