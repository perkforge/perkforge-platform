# Harbor native OIDC

`native.yaml` is human-operated, default-disabled configuration for native Harbor
v2.15.2 (the reviewed package chart is 1.19.2-bb.3). It does not deploy Harbor,
change PostgreSQL/Valkey, enable the Keycloak client, synchronize tenants, modify
projects/robots, start CI, or configure Trivy. Source publication is not live
approval. Run only against a separately approved exact target after deployment
and independently verify the selected chart/release.

## Guarded operations

Default and `--check` perform no API requests or credential reads. `inspect`
performs authenticated read-only inspection; `apply` needs
`harbor_native_apply_approved: true`. Supply an owner-controlled variable file
containing these public inputs and protected paths, never inline passwords:

```yaml
harbor_native_operation: inspect
harbor_native_origin: https://harbor.example.test
harbor_native_approved_origin: https://harbor.example.test
harbor_native_issuer: https://identity.example.test/auth/realms/perkforge
harbor_native_approved_issuer: https://identity.example.test/auth/realms/perkforge
harbor_native_version: v2.15.2
harbor_native_ca_file: /protected/public-ca.pem
harbor_native_admin_password_file: /protected/harbor-admin-password
harbor_native_client_secret_file: /protected/harbor-oidc-client-secret
```

```sh
ansible-playbook big-bang-bootstrap/configuration/authorization/sso/harbor/native.yaml -e @/protected/harbor-native.yaml
```

The exact observed build string may include a hexadecimal build suffix, but must
be v2.15.2. TLS and the server's `external_url` and build must match before Basic
authentication is sent. No proxies, redirects, netrc or insecure TLS are used.
URLs reject whitespace/control characters and equivalent normalized Harbor/issuer
hostnames. Existing OIDC mode must already use the exact issuer and client harbor;
foreign-provider adoption is refused. Credential paths must be absolute canonical
realpaths with no symlinked parent, inside a 0700 directory owned by the invoking
numeric UID. Credential files must be owner-only 0400/0600, regular, single-link files owned
by the invoking user, containing a single value with no trailing newline.
Never enable Ansible argument dumping/debug callbacks for protected operations.

The built-in `admin` account must independently authenticate as user ID 1,
system administrator, without OIDC metadata, both before and after the operation.
A fresh Basic request does not reuse browser/SSO cookies. Migration from db_auth
requires editable auth_mode, an empty user list and zero X-Total-Count. Harbor
excludes its built-in administrator from those results. Any additional user,
including a promoted local administrator, blocks migration. No account is deleted.

`apply` writes only differing owned fields. Initial migration additionally needs
`harbor_native_secret_write_approved: true`, which explicitly authorizes reading
and submitting the protected client secret. A later secret rotation also requires
that gate. **Configuration GET omits passwords entirely**: there is no masked
sentinel to compare. The adapter rejects unexpected secret exposure, verifies
all public fields and unrelated values, but cannot verify secret equality or
successful token exchange. It does not falsely report full SSO acceptance.

For a zero-write repeat, omit secret-write approval; the secret file is not read.
Secret-write approval always causes a write, even if the secret may already match.
An unconditional always block clears transient password, secret and delta facts
after success or failure; these facts are never intentionally cached.
After an interrupted or uncertain write, inspect the actual state before deciding
whether a separately approved secret rewrite is necessary. There is no automatic
retry or blind database-auth rollback.

## Identity and admission

Owned settings use `oidc_auth`, Keycloak, the exact issuer, client `harbor`, scopes
`openid profile email`, the ID-token `groups` claim, and admin group
`/platform/admins`. The corresponding Keycloak mapper must emit only this
client's roles, not all realm groups. Certificate verification stays enabled;
self-registration is false and project creation is admin-only.

Auto-onboard is false: new OIDC users follow Harbor's interactive username
onboarding. The user-claim override is empty; existing identity lookup uses
subject plus issuer. No email/username account-linking or account migration is
implemented here. The exact group filter `^/platform/admins$` bounds imported groups to the
reviewed admin claim; future project-role mappings need separate review. Neither the group filter, self-registration flag nor manual onboarding is
a login-denial policy. Unassigned-user admission and project authorization need
explicit real acceptance; this adapter does not promise deny-all admission.

OIDC logout is enabled. Harbor derives the exact post-logout callback from its
verified external URL: `https://harbor.example.test/account/sign-in`. The Keycloak
client must allow precisely that callback, separately from the login callback
`/c/oidc/callback`. Provider logout does not prove all CLI/refresh tokens revoked.
Harbor sends PKCE S256 and the client can require it.

Keep the Keycloak client disabled until separate enable approval. After enabling,
acceptance requires fresh MFA-backed admin login, local recovery, intended
non-admin/project denial checks, logout, and secret/token exchange validation.
No fixture result substitutes for these checks.

## Pinned upstream contract

Verified against [Harbor v2.15.2](https://github.com/goharbor/harbor/tree/v2.15.2):

- `api/v2.0/swagger.yaml`: configurations request/response schema, systeminfo,
  current-user and user-list endpoints.
- `src/controller/config/controller.go`: partial configuration update, password
  omission in ConvertForGet, and authModeCanBeModified requiring zero added users.
- `src/lib/config/metadata/metadatalist.go`: OIDCClientSecret is PasswordType.
- `src/pkg/user/manager.go` and `src/server/v2.0/handler/user.go`: list/count exclude
  default admin and expose X-Total-Count.
- `src/core/controllers/oidc.go`: subject/issuer lookup, manual onboarding,
  PKCE generation, and post-logout `/account/sign-in` construction.
- `src/pkg/oidc/helper.go`: challenge/method and exchange verifier.
- `src/go.mod` pins go.pinniped.dev v0.37.0; its
  [PKCE Method](https://github.com/vmware/pinniped/blob/v0.37.0/pkg/oidcclient/pkce/pkce.go)
  returns S256.

Offline real-Ansible loopback HTTPS checks:

```sh
python3 -m unittest discover -s big-bang-bootstrap/tests/security -p test_harbor_native_sso.py -v
```

These cover offline defaults/check, inspection, migration refusal, target/build,
redirect/TLS/recovery refusal, protected-file permissions, schema/read-only drift,
minimal write, unrelated preservation/readback failure, no blind retries, secret
redaction and a zero-write repeat without accessing the client-secret file.
