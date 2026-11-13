# Inactive exact-topic native auth preparation

Not selected by deployment or a live reconciler. No account/token is created by
merging. Render `native-auth.yaml.j2` only after `verify_inputs.verify` succeeds
and the actual owner-approved identities, topic entitlement and native state
have been verified. Approval flags in input are not authorization evidence.

Every native account is `user`, never `admin`. Publishers get write-only access;
subscribers read-only. Exact topic lists only, including platform engineers:
all-tenant entitlement is expanded from the approved context inventory, not `*`.
Viewers are rejected: their alerts are Mattermost-channel-only. Subscriber inputs
bind to an exact Keycloak subject and reviewed role; ntfy does not perform OIDC or
magically sync memberships. A supplied role string cannot prove membership. The validator additionally requires
`approved_entitlements`, a separately reviewed mapping keyed by subscriber subject
UUID or publisher username, containing kind/role/exact allowed topics. Each input
must match that binding and be a subset of its allowed topics. Derive this map
from platform-owned identity/context evidence, not the submitted account itself.
This is a consistency guard, not an identity provider or native membership sync.

Inputs contain username, kind, role, subject_id, approved, topics, bcrypt
password_hash and native token. Generate credentials locally with native ntfy,
never an online hash service. Publisher subject is null/service; subscribers
must have an explicit subject UUID. Tokens and hashes belong in scoped OpenBao
runtime custody and approved ESO Secret delivery, not ConfigMaps, values, Git,
logs or alert payloads. Real credential creation/delivery and native access grants
require the concrete approval batch before use. Native credentials are distinct
from human Keycloak passwords. No shared account is inferred for multiple users.

## Lifecycle safety

Native v2.37.2 declarative configuration creates/updates users and ACLs at startup.
Removing previously provisioned users deletes them on restart; declaring an
existing manual user adopts it. The guard rejects adoption and requires an exact
approved removal list against `previous_managed` and `existing_users`. Fetch those
sets from current reviewed ownership/native state, not caller guesses; stop on
drift. A renderer does not safely perform a live lifecycle change by itself.
Deletion/offboarding approvals and old token/session checks remain required.

Activation must compose these keys into one protected server configuration,
replace the current public config mount through reviewed GitOps, and restart only
ntfy. Do not layer config fragments as if ntfy loads arbitrary include files.
Preserve all non-auth settings, SQLite PVC and existing namespace policy. Test
firing/resolved and cross-topic denial before describing delivery as complete.

Morning approval batch: exact publisher username + Portal topic write-only;
exact named subject(s) + topic read-only (no viewers); OpenBao record/ESO consumer
scope; protected ntfy configuration and restart; separate protected Grafana
contact point and rule binding only once Mattermost destination is locked and
ready. No live access or deletion is authorized by this document.

[Native version-pinned configuration](https://github.com/binwiederhier/ntfy/blob/v2.37.2/docs/config.md).

Verification: six checks pass including an opt-in native isolated fixture proving
publisher write/subscriber read, inverse/cross-topic denial, and removal of a
synthetic managed subscriber on restart invalidating its old token while retaining
the publisher. Token rotation and real membership/offboarding remain unverified.
Run `RUN_NTFY_DEPLOYMENT_NATIVE=1 PYTHONPATH=big-bang-bootstrap/tests python3 -m
unittest configuration.test_ntfy_auth -v` with the pre-pulled pinned official image.
