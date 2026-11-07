# Grafana SSO review preparation

- Run `ansible-playbook prepare.yaml` from this directory: default and check mode do not create payloads or contact APIs.
- Explicit offline rendering requires `grafana_sso_render=true`, exact HTTPS `grafana_sso_origin` and `grafana_sso_issuer` (PerkForge realm), and a fresh absolute `grafana_sso_output` directory. Outputs are private `client.json` and `values.yaml` files; existing output is never overwritten.
- The disabled confidential client has one `/login/generic_oauth` callback, S256, no alternate grants, no web origins and only basic/profile/email scopes. The groups claim is bounded to this client's roles, not realm group membership. No roles, scope-role mappings, users or group grants are created.
- Values pair the same origin/issuer with the existing optional provider proposal. Package, Big Bang SSO and native OAuth remain off; local basic/login-form recovery remains on. Existing proposed role expressions are retained for review, not approved or exercised.
- This is not a realm import or an apply command. No root selects these files, no secret is generated/read, and no existing app adapter changes. The referenced client Secret and public CA are not delivered.

## Remaining gates

- Review exact claim/role policy and separately implement activation/rollback and independently gated provider/Secret/CA delivery.
- Verify pinned Grafana rendering, TLS, recovery and native positive/unmapped/engineer/tenant denial behavior before activation. No tenant access is authorized by this preparation.
- Separately approve source selection and live activation; test rollback and existing sessions. Offline payload tests are not live login or data-isolation evidence.

## Disabled client lifecycle (source only)

`ansible-playbook reconcile-client.yaml` and `--check` are noncontacting by default,
even if run is requested in check mode. This entrypoint does not activate SSO.
After separate action-specific approval, provide protected operator variables:

- `grafana_client_run: true`, `grafana_client_operation: inspect` or `prepare`,
  `grafana_client_approval: grafana-client-<operation>-v1`, and
  `grafana_recovery_verified: true` after independently verifying recovery.
- Exact `grafana_sso_origin` and `grafana_sso_issuer` used for preparation.
- Absolute `grafana_operator_token_file` and `grafana_ca_file`; token must be an
  existing operator-owned 0600 regular file in an owned 0700 directory, public CA must be a regular file.
- For `prepare` only, `grafana_client_secret_file`: an existing operator-owned
  0600 regular file containing the separately approved confidential client secret.
  Secret/token generation, persistent access creation and delivery are not included.

`inspect` reads only client/scope metadata, never the client credential endpoint.
`prepare` creates exactly one missing **disabled** client, then checks the exact
callback, owned identity, grant flags, reviewed shared-scope mappers, own-client
mappers, absence of roles/scope-role grants, and matching supplied credential.
An existing active, foreign or drifted client is refused, never adopted/repaired.
No PUT/DELETE, role or membership writes, token issuance or other app operations
exist. An interrupted create can be inspected and repeated without rotation if
its readback matches; do not automatically delete a partially created client.
API calls require verified TLS, do not follow redirects or use proxy/netrc, and
private inputs/results are suppressed. Approval strings are guards, not consent.

This stage intentionally cannot activate or disable an active client. Role policy,
client activation/rollback, protected Kubernetes Secret/public-CA delivery, pinned
native source selection, login/denial/session acceptance and live rollback still
need separate reviewed changes and approval. Preserve existing Grafana local
recovery, organization/admin/dashboard ownership and all other app grants.
