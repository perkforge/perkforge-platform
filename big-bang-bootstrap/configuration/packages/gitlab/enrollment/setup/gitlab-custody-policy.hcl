path "auth/token/lookup-self" { capabilities = ["read"] }
path "sys/policies/acl/tenant-identity-bootstrap-gitlab-v1" { capabilities = ["read"] }
path "platform/metadata/identity/gitlab/tenant-reader-v1" { capabilities = ["read"] }
path "platform/metadata/identity/gitlab/tenants-writer-v1" { capabilities = ["read"] }
path "platform/data/identity/gitlab/tenant-reader-v1" { capabilities = ["create", "update", "read"] }
path "platform/data/identity/gitlab/tenants-writer-v1" { capabilities = ["create", "update", "read"] }
