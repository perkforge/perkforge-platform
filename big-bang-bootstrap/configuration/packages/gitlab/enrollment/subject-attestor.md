# Exact-subject identity attestor

`resolve-subject.py` is a read-only verifier, not a native account creator,
account approver, identity linker, entitlement authority or continuous controller.
It uses a separately approved isolated administrator-owned `read_api` reader.
That native scope is **broad instance read access**, despite this helper's two
fixed endpoint paths. It is never the group writer and is never given to Portal.
`self_rotate` may additionally be present; this helper does not rotate tokens.

```sh
python3 resolve-subject.py --validate READER_TOKEN FRESH_RECEIPT INPUTS.json
python3 resolve-subject.py --verify READER_TOKEN FRESH_RECEIPT INPUTS.json
```

Default is inert. Validation performs no API, credential-content or output writes.
The five required JSON fields are `context`, `subject` (canonical lowercase
Keycloak UUID), `source_revision` (40-character immutable enrollment commit),
`origin` (HTTPS origin), and `ca_file` (literal CA path). No additional/internal keys, duplicate keys or template expressions are accepted.
Token/input/output custody reuses the group foundation's complete private-path
checks. TLS verification is mandatory; redirects and environment proxies are
forbidden. Each response is bounded; no API body, token or email is logged.

After checking `/personal_access_tokens/self` for active, non-revoked
`read_api`-only authority and explicit expiry, the only lookup is
`/users?provider=openid_connect&extern_uid=EXACT_UUID&per_page=2`.
Expiry on today's UTC date is conservatively rejected. Operational custody must
supply the separately approved short lifetime/rotation, not infer it from this
expiry check. No username/email fallback or enumeration is attempted.

- No result: `PendingFirstLogin`. The human must use native SSO first.
- One exact non-admin identity but blocked/pending approval: `PendingAccountApproval`.
  Native approval remains a manual authorized administrative action.
- One active non-admin identity with exactly one matching OpenID Connect binding:
  `IdentityVerified` with its native user ID.
- Duplicate/mismatched/admin/malformed/unsupported results fail closed, without a
  successful receipt. A successful empty response is distinct from API failure.

The receipt contains only schema, origin, context, subject, source revision,
UTC capture time, stage and (only for verified identity) native ID. It is an
executor-custodied observation, **not cryptographic attestation or proof of
canonical context membership**. The caller must independently bind a fresh
verified Keycloak group snapshot and approved role policy before membership
mutation. A supplied context is not authorization. No raw API identity inventory
is retained. Reader scope, native source compatibility and actual live authority
must be separately verified before activation.

Use a unique private receipt path per attempt. Existing files are never replaced;
exclusive reservation prevents competing writers. Failure removes only this
invocation's exact reserved inode. A crash can leave an empty or incomplete file;
consumers must require this invocation's successful exit plus the complete expected
schema/source/subject/origin and a bounded freshness window. Never reuse a prior
successful receipt as proof of a new verification. This helper does not deploy a
persistence service, durable enrollment trigger or approval automation.

The synthetic HTTPS fixture exercises real transport and custody, pending/active
states, duplicates, drift, broad scopes, expired tokens, redirects/pagination,
bounded responses, literal input rejection and no-overwrite cleanup. It does not
prove installed GitLab authorization or real subject membership.

## Pinned API source compatibility

Installed GitLab 19.4.2 source was inspected read-only: `lib/api/users.rb`
232–265 requires administrator authentication for provider/extern_uid filtering,
selects `UserWithAdmin` when administrative user data can be read, and preloads
identities. `UserWithAdmin < UserPublic` exposes `is_admin`; `UserPublic` exposes
`identities`. `personal_access_tokens/self_information.rb` permits available
scopes, authenticates a PAT and presents its self record; `lib/api/api.rb` permits
`read_api` for GET/HEAD. These are source-compatibility checks, not proof of a
provisioned reader's actual installed authorization or a real account lookup.
