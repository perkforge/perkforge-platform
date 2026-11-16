# One-record writer rotation component (inactive)

This Ruby module is included only by the fixed protected coordinator, never a
standalone CLI. It does not discover credentials, print tokens, choose pods or
access OpenBao. The coordinator must pin these bytes, verify the selected cluster,
GitLab namespace/toolbox Pod UID and existing original custody receipt, enforce
exclusive attempt handling, and keep the returned object private. Do not call this
module merely because `run:true` appears in an input. Actual execution requires
specific approval of rotation, successor custody and any cleanup.

ABI: `PerkforgeIdentityWriterRotation.execute(input)`; exact keys `run`, `mode`
(`rotate` or `revoke-successor`), `gitlab_origin`, `actor_native_id` (3),
`actor_subject` (the verified immutable OpenID subject constant), `parent_id` (7),
`old_token_id` (2), `expected_bot_id`, `original_setup_id` (64hex), `attempt_id`
(64hex), `expires_at` (absolute ISO UTC date). Cleanup adds only `successor_id`.
The bot ID comes from separately verified protected metadata, never guessed from
name/email. The original marker comes from the existing bootstrap receipt.

Rotation requires pinned GitLab19.4.2, unchanged verified origin/port, Admin Mode
off, active admin actor with exact unique OpenID binding, private top-level tenants
group7, exact active nonadmin existing project bot, original writer name/description,
api-only/non-granular/non-impersonation/non-sudo old token2. The old token must be
expired and not revoked. Remaining successor lifetime at UTC midnight must be
1..48h; there is no native default expiry fallback. The old token row is locked
through the native service call; an existing linked successor or repeated rotation
fails closed. This is not permission to replay a revoked-token/family API.

Pinned `GroupAccessTokens::RotateService` delegates to
`PersonalAccessTokens::RotateService` and returns `payload[:personal_access_token]`.
It revokes the old token and creates the linked successor with the same user,
name/description/scopes. It also clears bot membership expiry, copies the actor's
external status to the bot and emits GitLab's native token-rotated notification.
Therefore preflight requires the bot's ONLY membership to be existing group7
direct Owner with nil expiry, and existing external status equal to the actor's.
These checks avoid silently expanding the service's incidental effects. Native
actor permission/feature gates still apply. A transaction wrapper supplies the
old-row lock; it does not make external notification delivery transactional.

Success `Rotated` returns only parent/old/bot/successor IDs, expiry, attempt/original
setup binding and `successor_token` in memory to the coordinator. Post-service
readback must verify original marker, exact bot/scopes, old revoked, new not revoked,
expiry and predecessor2 before any returned token is accepted. Known-successor
cleanup uses only `ResourceAccessTokens::RevokeService` after revalidating that
exact successor's native linkage/ownership. It never deletes group/user/memberships,
rotates reader credentials, revokes a family or enumerates unrelated tokens.
Sanitized `ManualRecovery` never includes token or exception text. Unknown service
or transport outcome must be resolved by the coordinator without replay/remint.
Local lock/metadata checks do not promise immunity to unrelated concurrent admins.

Official pinned source under https://gitlab.com/gitlab-org/gitlab/-/tree/v19.4.2-ee:
- `app/services/group_access_tokens/rotate_service.rb`
- `app/services/personal_access_tokens/rotate_service.rb`
- `app/services/resource_access_tokens/revoke_service.rb`

The synthetic Ruby fixture substitutes every model/service and never boots Rails.
It tests guards, return shapes, refusal/retry and exact cleanup, NOT native database
transactions, installed API compatibility, custody, notifications or real rotation.
It runs with the existing cached19.4.2 image, nonroot/read-only/network-none; no
image pull or production configuration is needed. The coordinator's independent
TLS/custody tests remain separate. Native source compatibility is not execution
permission or a claim that token2 has been rotated.
