# No platform data is granted by the foundation. Approve exact paths per consumer.
# In particular this does not expose platform/bootstrap recovery records to ESO.
path "auth/token/lookup-self" {
  capabilities = ["read"]
}
