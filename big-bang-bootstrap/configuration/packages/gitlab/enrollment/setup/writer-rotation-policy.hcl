path "auth/token/lookup-self" { capabilities = ["read"] }
path "sys/policies/acl/tenant-identity-writer-rotation-v1" { capabilities = ["read"] }
path "platform/metadata/identity/gitlab/tenants-writer-v1" { capabilities = ["read"] }
path "platform/data/identity/gitlab/tenants-writer-v1" { capabilities = ["read", "update"] }
