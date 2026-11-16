# Phased acceptance custody: source only, no standing renewal

Earlier approval expired the GitLab writer and broad identity reader at
2026-11-16T00:00:00Z and explicitly excluded automatic renewal. Project/event
approval does not silently change that date or grant new root use. Do not execute
this source until the concrete phase, absolute expiry and custody are approved.
PR510/511 are preparation source, not native acceptance or a credential grant.

## A. Writer replacement, then project foundation only

Native target: existing private top-level `tenants` group7, old writer token2,
existing same nonadmin bot. The bot ID must first be read from exact owned token2
metadata and recorded privately; it is not guessed. Original protected bootstrap
receipt supplies the setup marker. Verify actor3's exact immutable OIDC binding,
active admin state, pinned GitLab19.4.2 and toolbox namespace/Pod UIDs. Verify bot
active/nonadmin/api-only, sole existing group7 direct Owner membership with no
membership expiry and unchanged external status; no new users/grants or reader3
rotation. Group-owner authority spans the tenant subtree, not one project.

Suggested consent date is Nov17 00:00UTC, NOT a moving default. Both coordinator
and native adapter require 1..48h actual remaining lifetime at execution. A later
consent may require a different explicitly stated date. No background renewal,
expiry extension, account approval or membership cleanup is implied.

Phase A exact additional custody objects:
- ONE ACL `tenant-identity-writer-rotation-v1`, exact checked-in
  `writer-rotation-policy.hcl`: only lookup-self, own policy readback, writer-record
  metadata/read/update. No create/delete, reader-record or root policy.
- ONE setup service token, only that ACL/no default or inherited policy,
  nonrenewable, ttl/explicit_max_ttl3600; consumer requires remaining900..3600s.
- ZERO new ESO roles, SAs, SecretStores, ExternalSecrets, namespaces or workloads.
  Existing writer ESO reads the existing writer record after successful CAS.
- ONE GitLab successor token, same bot/scopes; old token is revoked by rotation.
  NO replacement broad instance reader. No manager or runner permissions here.

The bounded [one-policy issuer](writer-issuer.md) supplies executable source for
this stage. Fresh explicit root-use approval remains required: exact public
health/cluster check, root identity check, one byte-exact ACL if absent and one
nonrenewable service child, followed by owned-accessor cleanup/readback. It never
reads/writes KV or enters GitLab/workloads. The previous five-policy/two-token
issuer and CAS0 bootstrap MUST NOT be rerun. ACL creation lacks CAS, so require an
exclusive administrative window. Unknown mint or undurable accessor evidence
requires manual recovery/expiry, never automatic remint. Retain ACL/receipts.

The provided child goes to `rotate-writer.py validate|apply TOKEN RECEIPT INPUTS`.
No command/default authenticates without explicit apply. JSON is literal/exact,
paths private/no-follow/bounded; new receipt/lock only. Fixed native Ruby include
`gitlab-writer-rotation.rb` receives no root or Bao token. It calls supported native
GroupAccessTokens::RotateService under an old-token row lock. Old expired but
not-revoked token2 and no linked successor are required. Native rotation also
emits GitLab's token-rotated notification; no new custom message is sent.

Custody is ONLY `platform/data/identity/gitlab/tenants-writer-v1`, expected current
version1 and original marker/native_token_id2/expiry2026-11-16. Metadata and data
must match before mutation; drift stops, never adopt a newer version. The old
expired token value is not authenticated or printed. CAS1 writes version2 with
new token/ID/expiry, original marker, predecessor2 and attempt ID; exact readback
is required. ESO delivery is independently verified before any consumer runs.
Source cannot claim that ESO automatically proved effective endpoint access.

Receipt stages retain Requested, NativeRotated, CustodyCASRequested and Verified
or ManualRecovery. Token values exist only in memory and the approved KV record,
never receipts/logs. Known successor on persistence/CAS/readback failure is revoked
only after exact native predecessor/bot/marker verification. Old remains revoked;
a possibly written record may contain a revoked successor and requires review.
Unknown native response is NEVER replayed: revoked-token family behavior could
revoke another successor. No automatic rollback, KV deletion or remint.

After custody succeeds, Phase A may separately use approved project/seed helpers
for ONE private `tenants/portal/platform-acceptance`, fixed commit and exact main
protection. CI/shared/group runners stay disabled. This requires ZERO runner,
manager, namespace, registry or pipeline-execution permission. Native project ID
and seed commit must be read back and retained before later phases.

## B. Separate project reader and runner custody proposal

These are NEW consumers, not renewal of the identity reader. Proposed record names
must match the final reviewed collector/manager manifests before consent:
- `platform/data/ci/portal/platform-acceptance-reader-v1`: one native project
  `read_api` Reporter20 token for the exact owned project ID, not instance reader3.
  Explicit date/rotation policy required; native bot internal/external visibility
  and foreign-project denial must be verified, not hidden behind fixed-path code.
- `platform/data/ci/portal/platform-acceptance-runner-v1`: authentication token of
  ONE NEW paused/locked/protected project runner, exact tenant tag/no untagged;
  never runner1 and never an API writer token. Runner lifetime is a separate gate:
  pinned19.4.2-ee supports token_expires_at and token_rotation_deadline, but current
  preparation source does not yet set/verify these or prove auto-rotation behavior.
  Do not use that source to claim a finite token or silently mint an indefinite one.

Runner custody proposed exact identities: policy/role/SA
`eso-portal-acceptance-runner`; namespace `gitlab-tenant-portal-runner`;
SecretStore/ExternalSecret `portal-acceptance-runner`; generated Secret
`gitlab-runner-auth` with native chart key `runner-token` (and empty registration
key only if pinned chart requires it). Public CA and registry credentials are
separate deliveries, not copies of the runner record. Existing kubernetes-eso
mount only, exact SA/namespace/audience binding, one-record read ACL, TTL300/max900.
No root/default/inherited policy or namespace selector.

Per new reader or runner delivery: ONE read ACL + ONE exact kubernetes-eso role +
ONE ESO SA + ONE SecretStore + ONE ExternalSecret + ONE generated Secret. Each
new record additionally needs a separately approved exact-record short-lived
write operator, not the Phase A writer-rotation child. Proposed reader delivery
ABI is context-derived namespace
`gitlab-tenant-<context>-events`, Secret `gitlab-pipeline-reader` key `token`,
ESO SA/role `eso-<context>-acceptance-reader`. Its separate runtime SA is
`gitlab-pipeline-observer`, with no API automount. Namespace/runtime-SA/deployment,
NetworkPolicy and scrape object counts still await reviewed manifests and consent;
these proposed names grant no Phase A authority.

Runner manager candidate separately adds TWO namespaces, THREE application
SAs (manager/job/installer), TWO Roles and TWO RoleBindings, ONE quota, THREE
NetworkPolicies, ONE chart GitRepository and ONE suspended HelmRelease:15 objects.
ESO SA/delivery above is additional. No native Helm verification yet; image pulls,
CA, precise egress/admission/installer permissions, scheduling and explicit resume
remain separate prerequisites. Foundation/source rendering never authorizes jobs.

## Tests and remaining gates

`test_gitlab_writer_rotation` tests actual localhost TLS custody plus fake native
responses: CAS1, foreign version/actor/marker, explicit real-time expiry, lost
response/no replay, known-successor revoke, failed revoke disclosure, durability
failure and no token receipts. Native Ruby fixture substitutes models/services,
network-none/read-only cached vendor runtime. Neither proves real DB permissions,
transaction effects, notifications, ESO delivery or live rotation. The native
component and coordinator require independent review together before publication.
