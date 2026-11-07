# Grafana SSO: one reviewed source, separate live approvals

This candidate completes the disabled-client and protected-input work with an
**admin-only proposal**, bounded role/member operations, native selection and
rollback. Publication changes nothing live. CI remains paused; offline fixture
passes are not fresh MFA, real login, tenant isolation or recovery evidence.

## Policy requiring owner confirmation

- Only explicitly approved existing Keycloak subject UUIDs receive Grafana's
  own `/platform/admins` client role and Grafana server-admin access.
- This role name is not a realm-group grant. Being in `/platform/admins` alone
  does not grant Grafana access. No realm/group/other-app memberships are edited.
- Engineers, viewers, tenants and unmapped users are denied. Broader Viewer access
  needs a separate datasource/org boundary review; hiding dashboards is not isolation.
- Preserve independent local recovery, current organization/dashboard ownership
  and other app grants. Disable insecure email-based account matching and automatic
  login. Confirm account collisions and correct subject binding before acceptance.

## Ordered operation

Use a clean published source containing this candidate, existing protected
operator credentials and the established cluster configuration. Do not put secret
values or tokens in command arguments, logs, Git or tickets. Approval strings below
are safety guards, not consent.

1. Independently verify local Grafana recovery, exact app/issuer origins, public
   CA/TLS, named operator identities and the unchanged monitoring baseline. Review
   and approve this policy and the exact recipients. Existing native identities
   must not be silently relinked to SSO by email or replaced.
2. Obtain action-time approval before creating/configuring the dedicated Grafana
   credential/persistent client access. Credential generation is not implemented
   here. Preserve the approved owner-only credential; never reset it on a retry.
3. Run `prepare.yaml` to render the paired disabled payloads offline if needed.
   Run `reconcile-client.yaml` with `prepare` to create only the missing disabled
   confidential client, or inspect an existing exact owned client first.
4. With separate policy/role-write approval, run `configure`. It adds exactly one
   non-composite own-client admin role and only its own-client scope mapping.
   This changes no recipients and cannot operate on an active client.
5. Run `members` with the complete reviewed recipient list and specific grant
   approval. It changes only those users' direct Grafana client roles; no account,
   group, realm role, other app, credential or session changes. Every subject and
   current direct/effective grant is preflighted before the first membership write.
6. Approve transmission of the existing credential to
   `monitoring/grafana-oidc-client` and the public CA to
   `monitoring/grafana-identity-ca`, then use [dedicated delivery](DELIVERY.md).
7. After separate deployment approval, select the same reviewed release's
   `big-bang-bootstrap/clusters/local-grafana-sso` root. It extends
   `local-harbor-app` and changes only Grafana's native OAuth configuration;
   existing monitoring, Harbor and other app ownership are preserved. Do not
   select the disabled review payload as a root. Validate actual Grafana TLS,
   Secret/CA mounts, local recovery, chart reconciliation and unchanged data.
8. Before activation, independently review incoming realm/client composite-role
   paths for the Grafana admin role. The direct-recipient API cannot prove that
   an unlisted identity inherits no access. Set `grafana_native_ready: true` only
   after that review and the native checks above. Run `activate` with
   exact policy/recipient approval. It verifies configured roles/scopes, direct
   recipient inventory, absence of group delegation and desired memberships, then
   changes only this client's `enabled` flag. It cannot silently grant a user.
9. Complete the acceptance below. Inspect and repeat each applicable operation
   to verify zero changes. Keep the original credential and object identities.

## Inputs and supported operations

`ansible-playbook reconcile-client.yaml` and `--check` are noncontacting by default,
even when run is requested in check mode. A live operation requires:

- `grafana_client_run: true`, operation `inspect`, `prepare`, `configure`,
  `members`, `activate` or `rollback`, and
  `grafana_client_approval: grafana-client-<operation>-v1`.
- `grafana_recovery_verified: true` only after independent local recovery proof.
- Exact HTTPS `grafana_sso_origin` and `grafana_sso_issuer`, realm `perkforge`.
- Absolute `grafana_operator_token_file` and `grafana_ca_file`. The existing token
  must be an owner-owned 0600 regular file in an owned 0700 directory. Symlink
  inputs, redirects, insecure TLS and proxy/netrc credential use are refused.
- `prepare` alone additionally requires the existing separately approved
  `grafana_client_secret_file` under the same ownership/mode contract. No other
  operation reads this file or the Keycloak client-credential endpoint.
- `configure`, `members` and `activate` require
  `grafana_role_policy_approval: grafana-explicit-admin-only-v1`.
- `members`/`activate`: `grafana_subjects` contains at most 20 unique existing
  `{sub: <UUID>, role: admin|absent}` entries. Activation requires at least one
  enabled intended admin, exact grant equality and `grafana_native_ready: true`.
  All current direct recipients must be in the reviewed list. Group delegation,
  unknown roles, composites and inherited grants on selected users are refused.

An interrupted create/role/grant/enable operation stops without cleanup. Inspect
the uncertain result before retrying. Exact state permits no-change repeats or
partial preparation resume. Foreign identity, changed callback, mapper/scope,
role policy or credential drift stops; no adoption, automatic repair or rotation.
The operator must separately review unexpected identity-provider changes; bounded
role-member endpoints are not a realm-wide proof against every possible indirect
role-composite path created by another administrator.

## Rollback and offboarding

- Stop new SSO authentication with the separately approved `rollback` client
  operation. It changes only the owned client's enabled flag and retains its
  identity, role definitions, grants and credential. It does not require reading
  the client credential. Foreign/drifted clients stop for inspection.
- Select `local-harbor-app` at the **same release** to remove only the Grafana SSO
  overlay. Do not downgrade the entire platform release or delete its PVC,
  Secret, CA, users, dashboards or organizations. Verify local recovery and the
  disabled provider, plus unchanged other apps and data.
- Disabling a client/provider does **not** invalidate existing Grafana sessions,
  native server-admin flags or API/service-account tokens. Review and revoke the
  affected native access/sessions with independent recovery and separate action
  approval, then prove denial in an existing session. Do not claim complete
  offboarding or security rollback until this is verified.
- For per-user removal, first verify the person's native admin/access and sessions
  are revoked. Record only that subject in `grafana_native_revoked_subjects`, then
  run `members` with `role: absent`. The guard is operator evidence, not automatic
  native revocation. Other users/roles remain untouched; no account is deleted.

## Acceptance before declaring SSO complete

- Fresh password+TOTP login for each approved admin; exact Grafana subject/admin
  identity, no insecure account linking and no extra organization membership.
- Actual unmapped/engineer/viewer/tenant and near-match role denials. Synthetic
  claim evaluation is not live identity-provider or datasource isolation proof.
- Public CA and hostname validation; wrong CA/host rejection, no insecure bypass.
- Local recovery works independently before/after deployment and rollback.
- Existing dashboard, datasource, organization, storage and local admin ownership
  stay unchanged. Inspect both fresh and existing-session behavior.
- Exercise bounded enable/disable/no-change repeats and the same-release rollback.
  Preserve evidence privately without tokens, credentials or full user payloads.
