# Grafana SSO review preparation

- Run `ansible-playbook prepare.yaml` from this directory: default and check mode do not create payloads or contact APIs.
- Explicit offline rendering requires `grafana_sso_render=true`, exact HTTPS `grafana_sso_origin` and `grafana_sso_issuer` (PerkForge realm), and a fresh absolute `grafana_sso_output` directory. Outputs are private `client.json` and `values.yaml` files; existing output is never overwritten.
- The disabled confidential client has one `/login/generic_oauth` callback, S256, no alternate grants, no web origins and only basic/profile/email scopes. The groups claim is bounded to this client's roles, not realm group membership. No roles, scope-role mappings, users or group grants are created.
- Values pair the same origin/issuer with the existing optional provider proposal. Package, Big Bang SSO and native OAuth remain off; local basic/login-form recovery remains on. Existing proposed role expressions are retained for review, not approved or exercised.
- This is not a realm import or an apply command. No root selects these files, no secret is generated/read, and no existing app adapter changes. The referenced client Secret and public CA are not delivered.

## Remaining gates

- Review exact claim/scope and role policy, implement a bounded client lifecycle and independently gated provider/Secret/CA delivery.
- Verify pinned Grafana rendering, TLS, recovery and native positive/unmapped/engineer/tenant denial behavior before activation. No tenant access is authorized by this preparation.
- Separately approve source selection and live activation; test rollback and existing sessions. Offline payload tests are not live login or data-isolation evidence.
