# Harbor SSO adapter

Source for Harbor 2.15.2 (Big Bang package 1.19.2-bb.3), not permission to run it.
Nothing selects a root, creates credentials, delivers Secrets or changes another
application. Default and check mode contact no APIs or private input files.
Configuration stays in Ansible; Python tests use disposable HTTPS fixtures.

## Client and grants

`prepare.yaml` optionally writes one disabled public client payload to a fresh
private output directory. `reconcile-client.yaml` uses an existing, externally
provided operator bearer token and public CA; it never obtains or saves a token.
Protected token/client-secret files must be owned regular 0600 files with owned
0700 parents, no symlink path. No credentials go in command-line variables/Git.
Use the protected file references in `operator.example.yaml`.

Each operation needs `harbor_client_run=true`, its exact
`harbor_client_approval=harbor-client-<operation>-v1`, verified independent local
Harbor admin recovery, exact separate HTTPS app/PerkForge issuer origins, and TLS
verification. These flags record approval; they do not replace asking the owner.

- `prepare`: create only an absent disabled confidential client, using the supplied
  existing secret; create its one non-composite `admins` role and own-role scope.
  No group/user grant. Repeats require the same secret, preserve the existing
  client and resume after partial creation. Foreign/drifted clients are refused,
  not adopted, overwritten, rotated or deleted.
- `inspect`: require the exact previously recorded client UUID and expected
  enabled state; read public client/role metadata, never the client secret.
- `grant-admin-group`: while disabled, grant only the client's `admins` role to
  the existing exact `harbor_admin_group_uuid`, whose full path must be
  `/platform/admins`. Requires the additional
  `harbor_admin_grant_approval=harbor-platform-admin-group-v1`. This gives current
  and future members of that group Harbor system-admin access when SSO is enabled.
  It does not change group membership, realm roles, other apps or tenant projects.
- `activate`: require that same exact approved grant and
  `harbor_native_verified=true`, then change only `enabled` to true. Repeated
  activation pins `harbor_client_expected_enabled=true` and makes no change.
- `disable`: change only `enabled` to false, retaining client, role/grant,
  credentials, projects, images and recovery. This stops new client logins, not
  existing Harbor sessions, CLI secrets or robot credentials. No blind switch
  back to database auth or claim of immediate session revocation.

All operations after preparation pin `harbor_client_uuid`. If an operation loses
its response, inspect actual state first with the expected state observed through
an authorized read. Do not blindly retry a mutation or recreate the client.

The client has one `/c/oidc/callback` callback and one `/account/sign-in` logout
redirect at the exact Harbor origin, no wildcard or web origin. Authorization
code + PKCE S256 only; direct grants, implicit flow, service accounts and full
scope are off. Shared basic/profile/email scopes are checked against their exact
known mapper contracts. The ID-token audience is Harbor only. The `groups` claim
is derived from Harbor's own role, using `/platform/` prefix to emit
`/platform/admins`; it is not a realm-group mapper. Scope/role/member reads refuse
unexpected visible direct grants and outgoing composites rather than removing them.
These endpoints do not enumerate foreign composite roles containing this role;
that privileged-administrator drift is not proven absent by this adapter. Use an
operator token with complete view of these objects; filtered admin API results
are not an exhaustive authorization audit.

## Native configuration and acceptance

Use [the native adapter](NATIVE.md) after the app/TLS/data-stage checks and local
admin browser recovery have passed. Keep the Keycloak client disabled during
native preparation. Harbor's external configuration API omits secret values:
non-secret readback cannot prove the OIDC secret matches. A successful browser
exchange is required before declaring SSO accepted.

Harbor `oidc_auto_onboard=false` means interactive enrollment, **not login denial**.
A group filter only bounds imported groups. Unmapped realm users can reach that
flow; this source grants them no system-admin or project access. Public project
read behavior and any stricter admission policy require their own acceptance.
No tenant roles, project membership synchronization, robots, publishing tokens,
scanner or offboarding automation are supplied.

Before acceptance verify fresh MFA, named platform-admin login/logout, separate
local admin recovery, non-admin system-admin denial, unassigned private-project
push/pull denial, and existing sessions during disable/rollback. Keep consistent
protected credential/database/registry backups. Fixture passes are not physical
browser, network, data isolation or restore evidence.

References: [Harbor OIDC helper](https://github.com/goharbor/harbor/blob/v2.15.2/src/pkg/oidc/helper.go),
[Keycloak role endpoints](https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/services/resources/admin/RoleContainerResource.java).
