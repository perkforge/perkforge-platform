path "platform/data/*" {
  capabilities = ["create", "read", "update", "delete"]
}
path "platform/metadata/*" {
  capabilities = ["read", "list", "delete"]
}
