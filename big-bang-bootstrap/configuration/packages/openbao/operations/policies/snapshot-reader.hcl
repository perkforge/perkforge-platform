# Assign only to the separately approved backup operator; never human tenant/ESO roles.
path "sys/storage/raft/snapshot" {
  capabilities = ["read"]
}
