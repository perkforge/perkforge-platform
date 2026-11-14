# Native owner-pilot bootstrap

Default/check mode is inert. `prepare.yaml` creates only an explicitly verified
OpenID ordinary account, one private `perkforge` team with open invitations off,
one private `portal-alerts` channel, and that account's ordinary team/channel
memberships. It does not grant System Admin, change role definitions or signup
settings, migrate an existing account, provision a webhook, or run a controller.
Related acceptance: #395. This is not fresh browser-login or tenant-isolation proof.

Inputs reuse `mattermost_context_origin`, `mattermost_context_ca_file`,
`mattermost_context_token_file`, `mattermost_context_contract_file`.
Explicit execution additionally requires `mattermost_bootstrap_apply=true` and
`mattermost_bootstrap_approved=true`, after the actual owner authorization.
The existing HTTPS administrator session is supplied privately by the caller,
not created here. The caller owns session revocation in `finally`.
No redirects, plaintext HTTP, certificate bypass or credentials in command arguments.

Contract/token files must be owner-only0600 under0700 directories, with no
symlinks. The protected JSON contract contains:

```json
{
  "schema_version": 1,
  "subject": "EXTERNALLY-VERIFIED-KEYCLOAK-SUBJECT",
  "subject_verified": true,
  "username": "native-username",
  "email": "verified-identity-address@example.invalid",
  "email_verified": false,
  "operator_id": "EXACT_NATIVE_RECOVERY_USER_ID",
  "operator_exception_approved": true,
  "team_name": "perkforge",
  "channel_name": "portal-alerts",
  "existing_ids": {}
}
```

Verify Keycloak subject, username/email and enabled state through the existing
approved identity workflow first; this adapter does not invent that verification.
`email_verified` must reflect the real identity input, not force a claim true.
The native username may differ from the Keycloak username; pin both to the same
verified identity in the caller's private evidence. No passwords are generated.

Existing objects require exact reviewed `existing_ids` (`user_id`, `team_id`,
`channel_id`) or a prior protected receipt. Username and email lookups must resolve
the same active native account, exact `openid` subject, and only `system_user`.
A name collision, absent/redacted linkage or unexpected administrator role stops
before writes. An existing team must remain private/invitation-closed and the
channel private in that exact team. Never silently adopt foreign same-name state.

Each successful create immediately saves its native ID to owner-only
`bootstrap-receipt.json` beside the contract. Resume uses this receipt and verifies
its origin/subject/operator/target identity. A network failure after server commit
but before receipt creation is uncertain, not permission to retry creation or
adopt by name: inspect privately and explicitly pin the verified ID first. Partial
success is retained; there are no deletes or rollback into public signup.

The already authorized independent recovery System Admin creates the objects.
Mattermost automatically makes that same creator team/channel admin. The adapter
records its explicit operator ID, verifies those expected creator memberships and
preserves them as an independent bootstrap exception, **not a Keycloak-derived
role**. The owner's linked account receives only `system_user`, `team_user` and
`channel_user`. No tenant Team Admin is inferred on the shared team. Future exact
channel reconciliation lives in `../context/`; this adapter is not a replacement.
Ordinary-member private invitation restrictions and tenant denial remain open
acceptance before multi-tenant rollout.

Offline test: `PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest
security.test_mattermost_bootstrap -v`. Real Ansible uses synthetic HTTPS responses
for create/readback, receipt repeat with no POST, foreign collision refusal, and
default/check inactivity. No real credentials, account or network grant is tested.
