# Current operator handoff

## GitLab provider activation — Valkey placement blocked

Observed 2026-11-04: v0.17.0 foundation passed exact 46-object readback and a
zero-change repeat. The approved five immutable Secrets and four GitLab ingress
policies are delivered. Flux selects the released provider stage; CNPG is Ready
and watches only gitlab. Valkey has not started: its unbound 2Gi claim selected
the control plane, where Longhorn CSI is absent. Existing nodes/apps remain
healthy. Security/persistence acceptance is pending; no GitLab, PostgreSQL,
Garage or runner activation, Registry1 copies or independent backup claim.

The local correction requires the existing storage-worker label and Recreate
for the single PVC writer, explicitly clearing API-defaulted rollingUpdate
fields. Server dry-run rejected the type-only transition and accepted clearing
those fields; neither dry-run changed the live Deployment. The correction is
not applied. Publish/release/promotion and
guarded recovery of only the still-unbound claim's selected-node annotation
require review and approval. Preserve the claim, Secrets and operator; never
delete/recreate the claim or uninstall providers to recover this selection.

## GitLab coordinated preparation contract

Only GitLab scope from old stacked #114 is reconciled here; observability
predecessors and PR bases are untouched. The disabled combined review root adds
public values only and preserves existing objects. GitLab, its shared database
operator foundation, Valkey, Garage and protected-project runner were initially
prepared disabled; current partial activation is recorded above.

Corey chose CloudNativePG as the shared platform foundation. The approved
operator is Ready in cnpg-system, watches gitlab only, and retains explicit
namespace RBAC plus reviewed global CRD/webhook permissions. Installer delegation
is applied within the reviewed foundation scope. Additional database namespaces require explicit
watch/RBAC changes, rather than another operator instance.

Ansible owns credential/CA/leaf preparation and delivery, Garage bootstrap and
runner-network assembly. Python is verification and independent fixtures only.
Default/check modes perform no API writes. Actual native account approval,
instance administration, SSO, database/S3 persistence, runner jobs, transport/CNI
and backup/restore acceptance are still gated. Fixtures do not establish those
outcomes. The exact pinned webservice CNG ActiveRecord/PG TLS rejection fixture
passed; its authorized one-time pull saved no registry login.

Corey selected the encrypted 128 GB external drive for initial independent backup
custody; no drive access is authorized or performed. Capacity, unlock, retention
and restore need separate acceptance. See the
[coordinated procedure](big-bang-bootstrap/configuration/packages/gitlab/coordinated-outcome.md).

## OpenBao SSO configured — 2026-11-03 18:49 UTC

Approved batch executed clean merged #153 source
`701edffb1a7ab2112303816c80e09950da2f21f9`. Existing root recovery and
Keycloak administration passed before writes. Created only the owned empty
`platform/` and `tenants/` KV-v2 engines and `oidc/` method; prepared one dedicated
confidential Keycloak client/secret; applied `perkforge-sso-v1-platform-admin`;
then mapped only `/platform/admins` to its app role and enabled that client.
No user, membership, machine-auth, unseal or other-app grant changes.

Engine/mount repeats: 17/18 ok, changed 0. Disabled-client repeat: 66 ok,
changed 0. Native apply: 33 ok / 3 changed; repeat: 31 ok / 0 changed.
Client activation: 70 ok / 2 changed; repeat: 68 ok / 0 changed. All failed 0.
Independent readback verified exact policy/role, no default policy, 900-second TTL
and 3600-second explicit maximum, trusted UI HTTP200, and actual native code-flow
redirect with S256/state/nonce and the exact callback. No human login or human
OpenBao token was issued by this batch. Engines remain empty; no KV values read.
Independent recovery still works. Rollback was not exercised.

**Owner reports successful named OIDC login after the batch.** This is user-reported
browser acceptance, not independent proof of every data permission, fresh factor
prompt or session-revocation behavior. Automation did not use the owner's
password, factor or token. Login reference:
https://openbao.perkforge.home.arpa/ui/vault/auth?with=oidc , role
`perkforge-sso-v1-platform-admin`, mount `oidc`. The method is not advertised by
unauthenticated discovery and default role remains empty.

Approved bounded native policy test passed at **2026-11-03 19:34 UTC** using
committed source `caa355a`: **58 ok / 12 changed / 0 failed**. Exactly one
5-minute nonrenewable token carried the actual PA policy, with no default or
identity policies. It created/updated/read/soft-deleted only its unique platform
dummy value, listed only its dummy tenant prefix, received HTTP403 for that
synthetic tenant value and detailed metadata, and verified denied auth/policy,
token-create, retention/destruction capabilities. No shared configuration write
was attempted to demonstrate those denials.

Cleanup passed: own-token revocation, bearer403, exact accessor invalidation,
permanent deletion/metadata404 of only the two marked dummy keys and all their
versions, and private token-file removal. Shared policy and the original root
recovery were preserved. No owner token, Keycloak user/membership, OIDC role/client,
engine or other-app changes. The disposable actor was root-minted for native ACL
verification; **no-group OIDC denial and OIDC token lifetime remain untested**.
The owner's reported named OIDC login is separate evidence. Default/check mode
of `accept-policy.yaml` remains inert; any repetition needs new approval/scope.

Post-test GET-only checks found all 3 nodes and 6 releases Ready, 55 Running and
11 Succeeded pods, none Pending/Failed or unready Running, unchanged source/root
and Keycloak/OpenBao pod identities. Raw scope, recap, token-cleanup and resource
receipts remain protected/ignored. No live rollback or outage test was performed. At 19:34:25 UTC actual CPU was
0.507/0.147/0.118 cores and RAM 4.66/2.04/2.41 GiB for control-1/worker-1/worker-2;
requests/limits and Longhorn scheduling were unchanged. Test RAM delta was
-9/+8/+2 MiB; no capacity claim follows from that short sample.

Next: review this acceptance and separately decide whether to run one no-group
OIDC denial identity before advancing another app. No new test is authorized by
this record. Token issuance/cleanup ambiguity must fail closed without scanning
other users/tokens or claiming success; the offline failure fixtures retain those
boundaries. Actual successful cleanup did not require any broad recovery action.

PA policy allows platform values CRUD and tenant-name LIST, plus five exact
current-token/UI endpoints. It does not allow tenant values, auth/policy
administration, other-token management, retention edits or permanent destruction.
On approved rollback remove only the exact owned human role/policy and disable
this client/remove its direct app mapping. Retain engines/OIDC configuration,
operator recovery and other apps. Client disable does not revoke existing native
tokens; account explicitly for any later acceptance tokens. No automatic rollback,
engine deletion or global session revocation is authorized by this record.

Protected operator/client-secret custody and phase logs stay local and ignored.
Verified canonical app/role UUIDs for all three enabled SSO clients were recorded
in `app-client-identity-contract.yaml` in private run evidence. Use that reviewed
contract in future realm-admin verification; it is metadata recognition, not a
new realm-admin grant. No real root/unseal credential was moved or changed.

Post-batch snapshot 18:49:27 UTC: 3 Ready nodes, 6 Ready releases, 55 Running /
11 Succeeded pods, no Pending/Failed or unready Running pods, no node pressure.
Source/root and Keycloak/OpenBao pod identities stayed unchanged; Flux remains
v0.15.2 / `local-headlamp-sso`. Each node has 6 CPU / 15.2 GiB allocatable:

| Node | CPU used / requested / finite limits | RAM GiB used / requested / finite limits | RAM delta MiB |
|---|---|---|---|
| control-1 | 0.55 / 2.09 / 0.80 | 4.69 / 3.66 / 5.04 | +26 |
| worker-1 | 0.16 / 2.37 / 2.30 | 2.03 / 1.84 / 3.83 | +29 |
| worker-2 | 0.14 / 2.47 / 2.90 | 2.42 / 2.00 / 3.63 | +33 |

Requests/limits unchanged; several containers are unbounded, so finite totals are
not ceilings. CPU delta was +0.035/+0.009/+0.011 cores. Worker disks each have
235.8 GiB maximum, about 220.5/220.8 GiB filesystem free, 70.7 GiB reserved and
15 GiB scheduled. Both disks Ready; 2 healthy volumes and the unchanged retained
detached test volume with unknown robustness. No storage cleanup or attach.

## Historical OpenBao SSO preflight and self-session candidate

Approved GET-only inspection at 2026-11-03 17:37 UTC verified the existing recovery
credential and trusted HTTPS to the same initialized/unsealed OpenBao 2.7.2 store.
`openbao-0` is Ready; its 10 GiB claim is Bound. Only token auth and default/root
policies exist. The `platform/` and `tenants/` engines, OIDC mount, versioned SSO
policy and identity aliases are absent. No KV values were read or server changes
made. Flux remains v0.15.2 / `local-headlamp-sso`.

The prepared policy correction grants only current-token lookup, renewal,
revocation, capability inspection and UI ACL display, keeping the default policy
disabled and tenant values/retention/destruction/self-grant denied. An isolated
pinned 2.7.2 fixture reproduces the old self/UI denials and verifies the new exact
permissions. This is not a deployed policy or browser/OIDC acceptance. See the
[self-session boundary](big-bang-bootstrap/configuration/authorization/sso/README.md#openbao-self-session-boundary--configured-live-token-tests-pending).

Next: review this correction, then explicitly approve preparation/activation
stages. Preserve recovery/unseal material, reject conflicting client/mount
ownership, retain data engines on rollback, and account for any issued tokens.
Approved read-only Keycloak inspection at 18:16 UTC verified the trusted issuer
and owned PerkForge realm; exact `clientId=openbao` lookup returned no client.
No foreign client must be adopted. A new dedicated confidential client/secret
still needs explicit activation approval. No client secret was queried; only the
verifier's ephemeral admin session was logged out after inspection.
No new credential, client, engine, role, policy or login was created by this work.

## Rancher SSO configuration and reported login — 2026-11-03

Approved execution used clean merged #150 source
`dc1470bee13811d394ed0f6d6b4d0e510669f0d1`. Rancher local-admin and Keycloak
recovery authentication passed first; the temporary recovery probe was removed
with exact UID checks and other sessions preserved. One dedicated confidential
Rancher client/secret, S256 and bounded own-client claims were prepared. Only
`/platform/admins` received the Rancher client role and the owned Generic OIDC
GlobalRoleBinding to `admin`. Local authentication remains enabled.

Native apply: 44 ok / 2 changed; client activation: 70 ok / 2 changed. Native
repeat: 45 ok / 0 changed; client repeat: 68 ok / 0 changed; no failures.
Public login advertises only local and Generic OIDC. Trusted HTTPS passed.
Flux remains v0.15.2 at `local-headlamp-sso`; no deployment or host restart.
Private evidence retains exact identities, protected logs and resource snapshots;
the owner-only temporary client credential is in the existing local cache, not Git.

**Owner reports completing initial local-admin login, logging out, then signing
in with the named account and seeing the local cluster and pods.** First-login is now false and the canonical server URL
is configured. This is reported browser-login acceptance plus GET-only settings
verification, not proof of effective per-user Rancher global-admin authorization.
A separately approved bounded non-admin denial passed at 17:06 UTC (details
below). Fresh owner factor prompts, successful-session expiry/revocation and live
rollback acceptance remain pending. Do not change the callback based on
the earlier loop: a synthetic UI state verified `/verify-auth` routes correctly.

At 16:10 UTC all three nodes and six releases were Ready: 55 Running pods,
zero Pending/Failed or unready Running pods. Each node has 6 CPU/15.2 GiB allocatable:

| Node | CPU used / requested / finite limits | RAM GiB used / requested / finite limits |
|---|---|---|
| control-1 | 0.49 / 2.09 / 0.80 | 4.61 / 3.66 / 5.04 |
| worker-1 | 0.16 / 2.37 / 2.30 | 2.01 / 1.84 / 3.83 |
| worker-2 | 0.12 / 2.47 / 2.90 | 2.36 / 2.00 / 3.63 |

Many containers lack limits; finite totals are not ceilings. Requests/limits
were unchanged; RAM delta was -59/+4/-14 MiB. Longhorn scheduling/robustness was
unchanged: 15 GiB scheduled per worker, about 220 GiB filesystem free and 70.7 GiB
reserved each. The retained detached test volume was not attached or cleaned up.

A separately approved real no-group/no-admin-role identity completed test-only
password/TOTP enrollment and the native Rancher S256 flow. IdP authentication
succeeded, then Rancher returned the pinned `Unauthorized` / `unauthorized`
access-policy denial without issuing a Rancher session. Exactly one native
attempt; Corey was not used. Run: **83 ok / 7 changed / 0 failed**, completed
2026-11-03 17:06:07 UTC using MR #152 source `72f248c`.

Cleanup revoked only this test identity's Keycloak sessions, deleted its exact
recorded UID and verified UID404/empty-name lookup. Its issued account-console
bearer and refresh credentials were rejected; the generated password/OTP/token
file was removed. Realm/browser flow, Corey's membership and credential IDs,
Rancher provider and existing admin binding compared unchanged. No native
Rancher session existed to delete. Protected phase/cleanup evidence is retained
under the run's ignored infrastructure state directory, never in Git.

Post-test GET-only verification at 17:06:33 UTC found all three nodes and six
releases Ready, no node pressure, and unchanged source/root/Keycloak pod identities.
Flux still selects v0.15.2 / `local-headlamp-sso`. The default-off
[runnable procedure](big-bang-bootstrap/configuration/authorization/rancher-denial-acceptance.yaml)
and [scope/limits](big-bang-bootstrap/configuration/authorization/sso/README.md#rancher-bounded-denial-acceptance--executed)
remain gated. This proves the tested no-grant denial, not every admin operation,
role, session lifetime or IdP-outage recovery. Uncertain native attempts retain
private evidence and stop for exact-session review; automatic Rancher token/user
cleanup is deliberately not implemented.

The independently approved OpenBao configuration is now recorded above; the
owner reports named OIDC login and bounded native policy acceptance has passed.
This Rancher test did not authorize another app or test batch.
If local setup changed the recovery password, refresh its proper custody; the
previous bootstrap cache was not revalidated after that owner action. Never reset
or retry guessed credentials automatically. No new execution or publication is
authorized by this record.

## Headlamp owner acceptance — 2026-11-03

Published v0.15.2 at `260f413c7e92d814c7af2d26ca09e62d7083d729` passed all
post-merge checks. Flux selects that tag and `local-headlamp-sso`; the effective
PKCE workload is Ready. Existing client and protected secret were reused. The
released native adapter verified exact API issuer/audience/azp/RS256/claims/CA,
workload image/Secret/mounts/arguments, then created only the owned
`oidc:/platform/admins` to `cluster-admin` binding. The client adapter mapped
only its bounded role to the owned admin group and enabled the same client;
non-target mappings were preserved. No extra host restart or secret rotation.

Native repeat passed 30 ok / 0 changed; client repeat passed 70 ok / 0 changed.
Trusted HTTPS/discovery and an actual authorization-code redirect with S256,
expected client and callback passed without following the redirect or supplying
human credentials. Synthetic Kubernetes access reviews allowed the admin group
and denied an ungranted group plus runtime-SA cluster Secret access.

**Owner reports signed in as named Corey account and can see nodes and pods.**
This is real owner-reported browser acceptance, not a synthetic fixture result.
Automation did not authenticate as Corey or capture his tokens/credentials.
Fresh MFA prompt timing was not independently observed.

A separately approved real non-admin drill then created exactly one owned,
no-group/no-admin-role user, completed Headlamp OIDC/S256 and test-only TOTP,
and verified the exact authenticated UID. Headlamp proxy and direct API both
returned 403 for nodes/pods; both Secret-list access reviews denied permission.
Cleanup revoked its sessions, deleted only that UID and verified 404/empty-name
lookup. Generated password/OTP/token files were removed; realm/flow/existing
admin grants compared unchanged. Corey was never targeted. Drill: 57 ok / 0 failed.

The 300-second ID JWT still authenticated immediately after deletion, while the
same resource denials remained. Recorded expiry: 2026-11-03T13:08:12Z. The token
was removed from local custody; expiry was not independently awaited. User
session revocation is not immediate offline JWT revocation. This acceptance
covers the tested no-grant identity/operations, not all roles, verbs or resources.

Post-acceptance inspect-only checks passed: native 30 ok / 0 changed and client
69 ok / 0 changed. Independent trusted certificate admin/API access and existing
Keycloak recovery credential authentication passed. The original v0.15.1 host
transaction/rollback checkout and root-only backup evidence remain preserved;
no IdP outage, datastore restore or forced rollback was exercised. Earlier
owner-local host apply/repeat preserved the original base hash with zero
second-pass host changes. Recovery source is separate from the app release.

Rancher/OpenBao SSO remains untouched by this Headlamp acceptance. Current main
also retains the separately reviewed, default-off remaining-app prerequisites
(#145), conservative change-aware CI selection (#146) and complete offline suite
parallelization (#149). Their code and documentation are preserved unchanged;
no CI or app configuration changes are part of this acceptance update.

## Current checkpoint — 2026-11-02

**Identity checkpoint #1 passed within the scoped lab acceptance.** The operator
confirmed fresh password+TOTP login and same-browser fresh-tab SSO reuse. A
separately approved real Keycloak OIDC/browser-form protocol drill used exactly
one disposable, unprivileged identity: wrong password, missing OTP and wrong OTP
were each rejected (three failed submissions total), followed by valid login.
Existing master administration removed only that identity's old OTP and required
re-enrollment; a new independent factor then authenticated successfully.

Cleanup verified the exact test UID absent (404/name lookup empty), all three
issued access/refresh pairs denied at userinfo/refresh endpoints, and the generated
password/seed/token file removed. The private credential and Ansible temporary
directories were empty afterward. Corey was never authenticated by automation;
his membership/credential IDs were unchanged. Realm configuration (including
lockout settings) and bound MFA executions compared equal before/after.

Post-test health passed at **14:19:15 UTC**: three nodes Ready without pressure,
six selected releases Ready, v0.14.0/local-keycloak and Keycloak/database pod
identities unchanged. The reproducible default-off test is
[authorization/factor-acceptance.yaml](big-bang-bootstrap/configuration/authorization/factor-acceptance.yaml),
with Ansible owning test-only API writes and Python verifying trusted-HTTPS forms,
PKCE/token acceptance and cleanup. No new app clients, group/role grants or restarts.

Limits: this is admin-assisted factor replacement while Keycloak/master access
is available, not IdP/database outage restoration, durable credential-custody
validation or recovery-code/CAC testing. Userinfo/refresh rejection is not proof
that every external offline JWT verifier immediately revokes an unexpired token.
No test identity had platform/tenant app permissions. Headlamp SSO and app-specific
authorization are the next separate scoped implementation/approval; do not rerun
the drill or retire independent recovery merely because this checkpoint passed.

**Human enrollment configuration passed at 02:52:34 UTC.** #132 merged at
`4dd6481b351ed2f254c09df490e241d1d8b11c18`; both post-merge workflows passed.
The separately approved normal run verified the exact recorded account, existing
admin-only ownership fields and nested flow metadata, then added only nominal
`/platform/admins` membership: **123 ok / 1 changed / 0 failed**. The second run
passed **122 ok / 0 changed / 0 failed**. This group has no application role mappings.

Readback verified unchanged user profile, password credential metadata, pending
`UPDATE_PASSWORD`/`CONFIGURE_TOTP` actions, password/TOTP executions and master
recovery flow. No new password, seed, app client/grant, flow rebuild, reset or
control-plane restart occurred. Three nodes were Ready without pressure; six
selected releases remained Ready. Source/root and Keycloak/database pod identities
were unchanged; deployed Flux remains v0.14.0/local-keycloak. Direct Kubernetes
administration worked; SSH settings were untouched, not separately retested.

**Operator report — 13:08 UTC:** the operator reports account setup with a new
password and TOTP. That report alone is not proof of a fresh MFA challenge; independent metadata
verification is recorded below. At 13:09 UTC the operator also reported signing
out and back in. At 13:15 UTC the operator explicitly confirmed both the new password and a fresh
TOTP code were prompted. **Fresh password+TOTP login passed by user report**;
the automation did not authenticate as the user. Wrong/missing-
factor denials and admin-assisted recovery were subsequently tested only on the
approved disposable identity; same-browser SSO reuse was confirmed by the operator.

**Read-only metadata — 13:12:58 UTC:** using the existing master credential,
GET-only checks of the protected recorded UUID confirmed exactly `/platform/admins`,
**no remaining required actions**, and credential type names **password / otp**.
The automation did not attempt user login; no personal profile values or credential contents
were inspected/persisted, no token retained locally, and no account/permission or
session configuration changed. This supports the enrollment report; the later separately approved disposable
identity drill above provides bounded negative-factor/recovery evidence.
The health evidence above remains the 02:52 snapshot; no new cluster health claim
is made by this metadata check.

The original temporary-password file is retained untouched; after the reported
password change it is historical custody, not a recommendation to use it again.
No deletion/rotation or user-session action was performed. Use the user's new password
for human access; never send passwords or TOTP QR/seeds through chat.
App SSO/authorization and durable recovery/bootstrap retirement remain separate
reviews. No additional live work is implied by this checkpoint.

Historical failures are preserved in protected evidence: undeclared ownership
attributes were filtered by the default profile, then the flow-list check wrongly
expected nested forms in a top-level-only collection. The reviewed fixes declare
only admin-owned markers and resolve child metadata by verified execution flowId.
The existing account/password and MFA flow survived both stops; no automatic
rollback/recreation or guard weakening was used.

PerkForge platform-only realm/group foundation, Keycloak initial master administration, OpenBao LAN HTTPS, Headlamp temporary-admin acceptance, Rancher installation and the first Longhorn storage test passed. **No further live
action is authorized by this handoff.** Never push main or merge for the operator;
preserve protected evidence, retained test data and other worktrees.

- Three physical nodes run RHEL 10.2 / RKE2 v1.36.5+rke2r1; node health and
  conservative scheduling headroom passed the Rancher preflight. One control-plane/
  embedded-etcd server means no control-plane HA. Previous key-only SSH/password-
  sudo, networking and sequential connected OS reboot checks passed.
- Flux source and root now select **v0.14.0**, exact commit
  `1ac80591d63c45105a5110182a3fdc4bf7ded7d2`, path
  `./big-bang-bootstrap/clusters/local-keycloak` (retaining Headlamp/OpenBao/Longhorn/Rancher). Publication/CI and exact artifact were verified.
  Root/umbrella/Keycloak/Headlamp/OpenBao/Rancher/Longhorn Ready; Keycloak acceptance passed at **18:23:33Z**.
  Historical OpenBao initial administration passed at 15:29:57Z.
  Historical first Rancher installation: Rancher Ready at **03:23:32Z**, Big Bang
  at **03:23:35Z**, root Ready/Healthy at **03:23:39Z**. Longhorn stayed Ready.
- Rancher **2.15.2** server, webhook, fleet-controller and helmops deployments were
  available. Trusted HTTPS hostname/current physical CA verification and `/ping`
  passed. **First login/password setup has NOT been attempted.** No SSO/groups,
  tenant authorization or cluster lifecycle operation was performed. Continuous
  Delivery remains off; internal Fleet is required platform machinery.
- The approved namespace/TLS/public-CA/bootstrap Secret and Rancher prerequisite
  delivery passed. Only Rancher's current physical service leaf/key was sent;
  the CA signing key stayed local. The installer has named cluster-admin bind;
  Rancher's runtime account is cluster-admin. This is trusted infrastructure,
  not least privilege. No Flux reinstall or forced retry was needed.
- Longhorn **1.13.0** remains V1, worker-only, two replicas, nondefault `longhorn`
  class with Retain/WaitForFirstConsumer. UI ingress remains absent. Root-disk
  reservations are not filesystem quotas. The accepted diagnostic cluster-admin
  delegation and powerful manager RBAC remain the explicit lab trust decision.
- OpenBao **2.7.2**, chart **0.30.6**, is deployed: one worker-hosted TLS server,
  10 GiB Longhorn/PebbleDB claim with two healthy replicas. The approved one-time
  operation proved an uninitialized store, initialized with **3 Shamir shares /
  threshold 2**, unsealed and verified initial root-token administration through
  trusted loopback TLS. Separately approved v0.14.0 exact-SNI LAN passthrough
  passed trusted UI/health/leaf verification at **16:51:36Z**. No new keys, init,
  unseal, root-token browser login or OIDC/policy changes during routing.
- Headlamp **0.45.0**, chart **0.45.0-bb.1**, is Ready with no ingress or OIDC.
  Approved one-hour dedicated bootstrap admin passed actual cookie-login/proxy,
  identity and safe capability reviews. Its SA/binding were UID-checked/deleted
  and the cached token denied afterward; loopback forwarding closed. This proves
  the authentication/API path, **not Corey's personal browser login**. The temporary identity remains revoked; no new Headlamp access was created.

The Rancher/RKE2 matrix includes our Kubernetes/OS versions, but lists Longhorn
1.12 rather than independent 1.13. This lab combination is not claimed fully
vendor-certified. One Rancher replica/control-plane is not HA. Required rollout
and HTTPS checks passed; real browser login and lifecycle operations remain
unverified. No competing direct Ansible/Helm installer is used.

Protected `.rke2-state/` retains the activation summary, exact source/root/Helm
objects, authorization/capacity checks and automatically saved redacted Ansible
output. The temporary app credential cache was moved to
`~/src/perkforge-tmp-secrets/`, outside Git (directory 0700, files 0600). It contains
Rancher's admin username and bootstrap-password flat files plus metadata. Future
approved app credential saves use this location, not the former `.rke2-state/`
cache. No values belong in Git/chat.
The operator owns proper-store migration and explicit temporary-copy cleanup;
changing a cached file is not server password rotation. Other app entries remain
pending or not applicable. OpenBao custody is deliberately separate: an
`openbao-v0130-<run>/root/root-token.txt` and `unseal/` with three share files plus
a share-only recovery response. Directory 0700/files 0600; this is temporary
**single-workstation custody**, not independent split custody. CA signing/SSH
material remains outside this cache. Everyday operator access is intended to use Keycloak platform-admin SSO;
durable local break-glass credential custody stays independent of the cluster/Keycloak in
the operator's password manager and requires a tested emergency path. Bootstrap
credentials are not automatically permanent recovery identities. No SSO, account
creation, credential rotation or deletion was performed for this custody move.

## Keycloak acceptance — passed 18:23:33 UTC

Same verified v0.14.0 artifact; only the root advanced from `local-headlamp` to
`local-keycloak`. Keycloak **26.8.1** (verified immutable Iron Bank digest), chart
7.3.2-bb.1, and PostgreSQL 18.6 are Ready without restart. One app/database is not HA.
Ansible applied the reviewed namespaced installer prerequisites, empty-store SQL,
4 GiB Longhorn claim and Keycloak-only ingress. Only `identity-ingress` and
`postgres-from-keycloak` NetworkPolicies were selected; no Headlamp route or
realm/Kubernetes group bindings were applied. The database application role was
verified non-superuser without create-database, create-role or replication rights.

Current physical leaf/key delivery passed chain, hostname, lifetime and key-match
checks; the CA signing key stayed local. Trusted HTTPS, exact served leaf, master
issuer discovery, private bootstrap-admin login and read-only master-realm API
passed. This is not an observed personal browser login. Traefik terminates TLS;
Traefik-to-Keycloak HTTP and Keycloak-to-PostgreSQL traffic are **unencrypted inside
the cluster**, explicitly accepted for this lab. Policies restrict reachability,
not encryption or proof of comprehensive tenant isolation. Management port 9000
is not publicly routed. OpenBao LAN HTTPS and Rancher ping still passed.

The temporary **master** bootstrap administrator does not automatically expire,
and has no automatic PerkForge/platform group membership. Three distinct new
passwords (bootstrap, database superuser, application database user) and username
are in an owner-only `keycloak-v0140-<run>/` custody directory. They are not durable
recovery merely because cached. Establish independently held permanent recovery,
then separately approve bootstrap retirement; no account deletion/rotation was
performed. A populated database must never be deleted/reinitialized to retry.
PerkForge realm/groups/clients, application SSO and API OIDC remain **not applied**.

Protected `keycloak-v0140-<run>/` execution evidence retains the actual private
credential-delivery Ansible batch, redacted output, target/release guards,
readiness/image/HTTPS/login/database verification and resource/storage snapshots.
The versioned operation is documented in the [Keycloak procedure](big-bang-bootstrap/configuration/packages/keycloak/README.md).
No credential values or private operational inputs belong in this handoff.

Post-app snapshot: all three nodes Ready/no pressure, 55 Running pods all Ready,
zero Pending/Failed. Actual CPU/RAM, declared requests and finite limits:

| Node | CPU actual / requests / finite limits | RAM GiB actual / requests / finite limits |
|---|---|---|
| control-1 | 0.369 / 2.085 / 0.800 | 4.959 / 3.656 / 5.039 |
| worker-1 | 0.156 / 2.370 / 2.300 | 1.925 / 1.836 / 3.828 |
| worker-2 | 0.137 / 2.470 / 2.900 | 2.233 / 2.000 / 3.625 |

Each node allocates 6 CPU/~15.201 GiB. Remaining unrequested CPU/RAM is respectively
3.915/11.544, 3.630/13.365 and 3.530/13.201. Limits omit unlimited containers and
are not node ceilings. Keycloak/database added 0.5 CPU/1 GiB requests; actual RAM
changed -0.022/+0.114/+0.578 GiB over the immediate baseline, not solely attributable
to this app. Longhorn workers have ~220.51/220.80 GiB physical available, 70.73 GiB
reserved each and 15 GiB logical scheduled each (previously 11). The 4 GiB database
volume is attached/healthy with two running replicas on distinct workers.
Replication and successful login do not prove backup/restore. Retained storage-test
data is untouched. Next checkpoint: permanent recovery/custody and separately
approved realm/group configuration; no further deployment is authorized here.

## OpenBao LAN HTTPS — passed 16:51:36 UTC

Helm owns the exact-SNI TCP passthrough on existing Traefik 443 to `openbao:8200`.
TLS terminates only at Bao; trusted CA/hostname/exact served leaf, unauthenticated
UI/health and Rancher HTTPS ping passed. Existing HTTP routes and Bao pod unchanged.
Only namespaced IngressRouteTCP CRUD was added; no keys or human grants changed.
Private `openbao-lan-v0140-<run>/` evidence preserves both the original stopped
checker and later `acceptance-summary.txt` exit 0. The initial checker mistook
old Ready conditions for new values consumption and failed an early route lookup.
Normal parent/child reconciliation then consumed new configuration digests; no
force/reset was used. This was a readiness-validation bug, not an app failure.
Future checks must verify expected child resources/configuration consumption,
not only root revision or unchanged-generation Ready conditions. See the
[procedure](big-bang-bootstrap/configuration/packages/openbao/README.md#lan-https-candidate--not-activated).

## Headlamp acceptance — passed 17:11:21 UTC

Reviewed prerequisites and existing Registry1 credential were delivered without
replacing a conflicting Secret. Only the root path advanced; v0.14.0 stayed pinned.
One worker pod requests 100m CPU/128Mi, limits 500m/256Mi, no PVC. Runtime SA remains
without application RBAC; no Secret/exec/RBAC permissions were added to it.
The separately approved [Ansible test](big-bang-bootstrap/configuration/ansible/headlamp-access-smoke.yaml)
created a unique dedicated SA/binding to existing cluster-admin, requested 3600s,
verified actual expiry and cookie-backed UI API identity with read-only operations
and nonpersistent capability reviews. No Secret values were read and no destructive
operation demonstrated. [Cleanup](big-bang-bootstrap/configuration/ansible/headlamp-access-cleanup.yaml)
verified recorded UIDs and absence; the [verifier](big-bang-bootstrap/configuration/ansible/files/verify-headlamp-access.py)
proved the old token no longer authorizes namespace reads. No persistent token Secret.
Personal browser login remains unobserved; the completed test is not an ongoing
access session. A future session or SSO requires approval; Headlamp has no native
admin username/password. The revoked token/metadata remains owner-only under
`~/src/perkforge-tmp-secrets/headlamp-bootstrap-admin-<run>/` for operator cleanup;
it is not a durable break-glass credential. Temporary localhost forwarding closed.
Private `headlamp-v0140-<run>/summary.txt` records exit 0/complete and automatic safe
output/resources. Registry pull Secret stays for app operation; no other credentials
were changed. OpenBao LAN/Rancher checks still passed after Headlamp.

All nodes Ready/no pressure; 53 Running pods, zero Pending/Failed, nine completed
jobs. Actual CPU/RAM: control-1 0.604/4.955GiB, worker-1 0.310/1.843GiB,
worker-2 0.145/1.675GiB. CPU requests/finite limits: 2.085/0.8, 2.12/1.8,
2.22/1.9 cores. RAM requests/finite limits: 3.656/5.039, 1.586/3.328,
1.25/2.125GiB. Each node has 6 CPU/~15.201GiB allocatable; unrequested headroom
3.915/11.544, 3.88/13.615, 3.78/13.951 CPU/GiB. Some containers lack limits;
finite sums are not node-wide ceilings. Immediate RAM delta +0.127/+0.062/+0.033GiB
is a short sample, not all attributable to Headlamp. Its declared request adds
0.1 CPU/0.125GiB on worker-1. Longhorn logical scheduled stays 11GiB each worker;
physical available ~221.19/222.56GiB with 70.73GiB reserve each. No backup/HA or
new storage acceptance claimed, and the retained test volume was not deleted.

## PerkForge platform realm/group foundation — passed 20:20:07 UTC

Approved platform-only execution used clean merged source
`f2fa519434973197a12008805324c08d97a3644d` and the
[versioned Ansible operation](big-bang-bootstrap/configuration/authorization/foundation.yaml).
Target, trusted hostname/exact physical TLS leaf, existing master credential and
absence of the realm were verified first. Read-only inspect: ok 14/changed 0.
First apply: ok 111/changed **6** (one realm and five groups), failed 0. Second
apply: ok 132/changed **0**, failed 0. Final independent API readback passed.

Observed realm: `perkforge` / PerkForge. Exactly five empty group paths:
`/platform`, `/platform/admins`, `/platform/engineers`, `/platform/viewers`,
`/tenants`. `authorization_tenants: []`: no tenant-specific groups were created.
There are **zero users, memberships, custom group role mappings, default groups
or custom app clients**. Keycloak's six normal built-in realm clients are present.
Canonical group labels confer no application permission. No engineer powers,
PerkForge user enrollment, realm-management grants or SSO integration was applied.

Existing master API access remains usable; no credentials were generated, copied,
reset, retired or logged. The temporary master account still does not expire
itself; independently held permanent recovery remains a separate checkpoint.
Flux source stays v0.14.0 and root local-keycloak; source/root specs and Keycloak/
PostgreSQL pod identities stayed unchanged. All six HelmReleases remained Ready.
No route, Kubernetes RBAC, storage, other-app or forced recovery operation occurred.
Private `realm-foundation-<run>/` evidence retains merged-source guards, protected
inputs, redacted inspect/apply logs, two acceptance reads, changed=0 recap and
summary exit 0. Credential-value scanning of saved logs passed.

Next: separately review/approve the first human identity and membership enrollment,
permanent recovery, and one app integration at a time with allowed/denied tests.
Tenant delegation, multi-tenant shared-user changes and engineer scope remain
unimplemented. Foundation creation/idempotence is live-tested; actual human/app
role enforcement, cross-tenant authorization and recovery drill are **not proven**.

## Prepared named-human IL2 TOTP enrollment — not executed

A default-off [Ansible entrypoint](big-bang-bootstrap/configuration/authorization/enroll-human.yaml)
prepares one explicitly named human and owned PerkForge password+required-TOTP
browser flow. Existing test-user enrollment is default-off/localhost-fixture-only;
its useful evidence remains. Proposed username is an external input, never assumed
to be email or verified mailbox. Default Keycloak profile requires email and name
fields during user login; no fake fields/profile-policy relaxation is supplied.
Realm-wide browser scope, profile completion and permanent recovery decisions
must be confirmed before live execution. Existing master/direct recovery stay intact.

Current IL2 uses TOTP; intended future IL5 CAC is a design requirement only, with
no CAC/X.509 implementation or compliance claim. Structural HTTPS tests are not
live factor proof. Human password/TOTP completion and fresh wrong/missing-factor
denials are unexecuted. No user, credential, flow, membership, client, permission,
restart or app SSO has changed during this preparation. Headlamp remains separate.

## Next configuration — recovery and identity remain separately gated

OpenBao, Headlamp and Keycloak initial acceptance are complete on the same v0.14.0
artifact using the [ordered stage roots](big-bang-bootstrap/configuration/ansible/README.md#ordered-app-stages).
No further app is authorized. Platform-only realm/group creation and idempotence
are now accepted above. Establish independent Keycloak permanent recovery, review
the six-role matrix and separately approve human membership/client configuration.
Empty groups are not that authorization rollout.
OpenBao root retirement/scoped recovery, custody transfer and backup/restore remain
pending; Headlamp's temporary admin remains revoked. Never move backward to an
older root as an automatic rollback or assume publishing a release activates it.

## OpenBao acceptance evidence — 2026-11-01 15:29:57 UTC

Private evidence is in the OpenBao implementation worktree under
`infrastructure/ansible/inventory/.rke2-state/openbao-v0130-<run>/`:
`summary.txt` exit 0/complete, redacted Ansible output, exact release evidence,
readiness and before/after resource summaries. No credential values are in Git.
The [executed init/unseal playbook](big-bang-bootstrap/configuration/ansible/openbao-initialize.yaml)
and [synthetic success/refusal tests](big-bang-bootstrap/tests/security/test_openbao_initialization.py)
are reusable; this is a one-time operation, never a restart/recovery command.

All three nodes Ready/no pressure; 52 Running pods, zero Pending/Failed (nine
completed jobs). Immediate actual usage: control-1 0.656 CPU / 4.85 GiB RAM;
worker-1 0.173 / 1.75 GiB; worker-2 0.261 / 1.61 GiB. Versus baseline, RAM changed
+0.01/+0.07/+0.00 GiB; short CPU samples fluctuate, not attributable solely to Bao.
Per-node memory requests/finite limits: 3.66/5.04, 1.46/3.08, 1.25/2.12 GiB;
CPU requests: 2.085/2.020/2.220 of 6 allocatable each. Some containers have no
CPU/memory limits; summed finite limits are not a cluster-wide usage ceiling.
Longhorn each worker: 11 GiB logical scheduled (10 GiB Bao + retained 1 GiB test),
~221.9/222.8 GiB physically available with 70.7 GiB configured reserve. Replication
is not a backup. Bao volume attached/healthy; historical completed test remains
detached/unknown as previously explained. No test cleanup was performed.

## Acceptance requirement for every subsequent app

After each successful deployment, provide timestamped per-node CPU/RAM usage
versus requests/limits, node/pod readiness/failures, and Longhorn disk/replica usage
and remaining headroom, preferably with a comparable previous-app delta. Save
safe evidence automatically, without terminal-output transcription. Missing metrics
are unavailable, not zero. See the shared [acceptance contract](big-bang-bootstrap/configuration/ansible/README.md#health-and-capacity-acceptance-after-every-app).
This does not authorize deployment or repair. After app deployment, an early Grafana
goal is a verified cluster overview; assess the six queued dashboards or a reviewed
compatible community dashboard before adoption.

## First storage test — passed, resources retained

The run completed at **2026-11-01 02:03:46 UTC** (saved exit-record timestamp and
Ansible recap). The explicitly approved test created one unique namespace, one **1 GiB** claim and
one non-root, digest-pinned official BusyBox pod at a time. It passed:

1. Initial write/checksum on worker-1.
2. Graceful pod deletion, normal CSI detach and a new pod on worker-1; checksum
   matched without rewriting the data.
3. Graceful deletion/detach and scheduler-based placement on worker-2; checksum
   matched again.
4. Volume healthy; exactly two running healthy replicas on distinct workers and
   two engine replica modes `RW`. Evidence confirms three distinct pod UIDs with
   the same PVC/PV UIDs. Ansible: `ok=78 changed=25 failed=0`.

The namespace, PVC, Retain PV, Longhorn volume/replicas and final pod are retained.
Saved read-only evidence at 03:33 UTC shows the final pod completed normally
(exit 0) at **03:03:42Z**, exactly one hour after startup. Its command was the
bounded one-hour sleep. The retained claim/volume remain; the volume is now
Detached and reports robustness Unknown while inactive. This is not fresh
active-replica validation or evidence of a storage regression; no attach/retest
or cleanup was performed.
**Cleanup is not approved.** Protected run evidence under the existing ignored
`infrastructure/ansible/inventory/.rke2-state/` contains `retained-resources.json`
with exact names/UIDs, stage manifests/objects/checksums, logs and exit status.
Do not delete a Retain PV and assume its data was removed.

This proves only small-sample persistence, same-worker recreation, cross-worker
reattachment and replica health. It does **not** prove throughput, full-volume I/O,
node failure/rebuild, backup/restore, application suitability or HA.
Longhorn reports `dm_crypt` unloaded on both workers; this unencrypted test passed.
Encrypted volumes require separate preparation/validation; no module was changed.

Repeat only after new action-specific approval, with a fresh namespace/output and
reviewed target inputs: [storage test procedure](big-bang-bootstrap/configuration/packages/longhorn/README.md#disposable-storage-acceptance).
The [C4 storage flow](docs/architecture/README.md) links the actual Ansible code.

## OpenBao deployment complete; recovery work remains

Initial administration is observed above, not a queued deployment. The server is
non-HA, has no ingress/Kubernetes-auth/OIDC integration, and remains manually
unsealed after restart. Root retirement/scoped recovery, independent custody,
audit/backup and restore testing need separate approval. Existing proven role/API
configuration stays retained for later review, not applied automatically. See the
[OpenBao procedure](big-bang-bootstrap/configuration/packages/openbao/README.md).

## Headlamp source and future access

Deployment and temporary-admin acceptance are recorded above. OIDC/group mappings,
LAN ingress and ongoing user access remain separate approvals. Existing useful
historical OIDC/RBAC tests are retained; no competing installer is introduced.

## Queued Keycloak candidate

Stacked after Headlamp: chart 7.3.2-bb.1 with a verified immutable Iron Bank Keycloak 26.8.1 image
override (chart metadata remains 26.8.0), plus the unchanged pinned database
and a separately prepared Longhorn claim. Initial master bootstrap administration
only; no startup realm import, PerkForge groups or app client integration. Protected
bootstrap/database/pull/TLS delivery and real first login remain future approvals.
Ansible retains realm API ownership separately from Helm deployment. See the
[Keycloak procedure](big-bang-bootstrap/configuration/packages/keycloak/README.md).

## Queued authorization review

The authorization draft now has a [six-role/app matrix](big-bang-bootstrap/configuration/authorization/MATRIX.md)
and zoomable C4 role → group → client/app mapping → tenant/resource views. One shared
PerkForge realm, per-app clients and multi-tenant memberships are design intent;
unsupported native protocols/edition features are explicitly gated. PA controls
platform/shared identity and platform values; tenant values need grant/emergency
in nominal OpenBao policy, with administrator bypass acknowledged. Platform-engineer is a distinct code/MR and proposed scoped-diagnostics role,
with no inherited identity/RBAC/secret/break-glass authority; direct live writes
remain undecided. TD reads own
values without writes; viewers perform no operational changes or value reads,
but may chat in assigned channels. Tenant membership ownership must not reset or
delete shared identities or grant platform authority.

Only disabled group/Kubernetes/OpenBao review examples are rendered. Consent and
emergency elevation, delegated identity mechanics, admission, app/query isolation,
revocation/migration and most app integrations remain unimplemented. No users,
credentials, memberships or live grants were created. Use small per-app integration
MRs; the shared design is not an all-app apply. Existing API configuration still
defaults to platform_api_apply=false. See the
[review contract](big-bang-bootstrap/configuration/authorization/README.md).

## Next decisions

1. Separately approve Rancher first login and private password setup; keep direct
   RKE2 recovery access. No login/password change or OIDC operation is implied.
2. Initial OpenBao/Headlamp/Keycloak acceptance is complete. Review the six-role
   matrix and disabled authorization configuration, establish permanent recovery
   and separately approve realm/groups/clients before one-at-a-time app SSO.
   Preserve proven mappings; no live integration is implied by the design.
3. Retained storage-test cleanup and further storage/recovery tests need separate
   approval. Recovery drill #101 and Velero evaluation #105 are backlog only;
   replication is not backup. No automatic data-volume deletion.
4. Deferred ownership/configuration refactors #95/#14, Kickstart and node upgrades
   do not authorize rebuilding or upgrading existing nodes.

## Custody, DNS/TLS and recovery limits

Physical addresses/MACs and SSH references belong only in ignored
`infrastructure/ansible/inventory/.topology.yml`; trusted SSH host records are also
ignored. Private keys and credentials never belong in tracked docs/viewer sources.
Protected `.rke2-state/` contains kubeconfig, server/agent token exports and runtime
inputs/evidence. Its existing ZIP is **not encrypted** and is not an etcd backup.
Independent password-manager custody of those exports has not been confirmed.

An off-node etcd snapshot plus matching server token previously passed transfer
size/SHA256 and embedded integrity checks. Restore, database consistency and an
independent encrypted/off-site copy remain untested. Etcd backups do not contain
application PV data. Preserve current local recovery material.

Previously approved DNS migration and CoreDNS checks passed for lab, Kubernetes
and public names. DNS-service/node/workstation reboot persistence and browser DoH
are not fully verified. Local CA/service certificate issuance and workstation/node
OS trust checks passed; Rancher trusted HTTPS passed; other container/application/browser trust remains separate.
Independent CA backup/passphrase custody is unconfirmed. Application TLS delivery
is prepared in `configuration/ansible/platform-tls.yaml` under Big Bang bootstrap,
and was applied only for Rancher under explicit approval. Other applications require
their own released-source/target/security approval.
Reuse the existing Flux registry Secret; do not read, replace or rotate it as part
of ordinary release promotion.

Use the [platform operation order](big-bang-bootstrap/configuration/ansible/README.md),
[Longhorn procedure](big-bang-bootstrap/configuration/packages/longhorn/README.md),
[Rancher procedure](big-bang-bootstrap/configuration/packages/rancher/README.md),
[RKE2 procedure](infrastructure/ansible/RKE2.md) and [PXE procedure](pxe/README.md).
Do not rerun first-install provisioning on this installed cluster. Every new live
operation needs concrete approval; these recorded results are not continuous
monitoring or permission to repair unrelated systems.

## PerkForge realm administration — applied, rerun guard follow-up

At 2026-11-02 16:24:03 UTC, the separately approved corrected merged #136 operation
(`9398fb5`) applied exactly one PerkForge realm-management/realm-admin mapping to
/platform/admins: 37 ok, changed 1, failed 0. Direct readback is realm-admin only;
effective closure is the reviewed 22 roles. Full PerkForge administration includes
impersonation and authentication/realm settings, not master/other realms.

Independent before/after checks preserved non-target group mappings across both
realms, master role/composite definitions and verifier role mappings, captured
realm security settings and the built-in management role graph. Fresh master
recovery authentication passed; three nodes Ready and both Keycloak/database pods
Ready with unchanged zero restarts. No human authentication, new identities,
password/MFA resets or other app grants occurred.

The normal rerun stopped at the early group-representation guard: 11 ok,
changed 0, failed 1. Keycloak now correctly represents the approved mapping as
clientRoles={realm-management: [realm-admin]}, but the merged guard still requires
that field empty. Independent verification confirms the desired mapping remains
correct and all preservation checks pass. Do not claim successful idempotence,
remove the grant, bypass the guard or perform further live writes to hide this.
A narrow local representation/fixture correction is prepared; current granted
access is not rolled back. It allows only empty or exact realm-management realm-admin
representation and cross-checks independent direct metadata. Forced GET-only
execution against the active state passed (38 ok, changed 0, failed 0), including
all subsequent guards. Realistic synthetic apply/second-invocation tests cover the
previous mismatch; a new merged normal rerun remains pending review and merge.
The owner reports signing out, signing back in with MFA and seeing the expected
Keycloak console access. This is user-reported fresh-login/console acceptance,
not proof of every management operation or master-denial behavior. Automation
did not authenticate as the human. Publication of this correction and acceptance
evidence is separately approved; no additional live writes are authorized.

## Merged-source no-change acceptance — 2026-11-02

MR #137 merged as `e7cac52fcc328249de9ef7d704757d6484996b4a`.
Both exact post-merge workflows passed (`41494971414`, `41494971826`), including
configuration/release checks and the release job. The separately approved normal
Ansible invocation from that clean merged checkout passed: **38 ok, changed=0,
failed=0, skipped=1**. This supersedes the historical rerun failure above; no
additional mapping was written. Independent before/after metadata again verified
realm-admin only, exactly 22 effective roles, unchanged non-target/master mappings,
management definitions/edges, realm security and master verifier access. All three
nodes Ready; Keycloak/database Ready with zero restarts. No personal authentication,
credential reset, new identity or application SSO grant occurred. The owner separately
reports fresh MFA console access; not every management operation/master-denial
scenario was tested. Local documentation of this final result is unpublished.

## Coordinated application SSO — local source ready for publication review

The local feat/platform-apps-sso branch is based on merged #138 (`fd36dfa`),
preserving TLS lifecycle/Pixel trust documentation and the successful #137 normal
rerun evidence above. Shared Keycloak and independent Headlamp, Rancher and OpenBao
adapters default to no contact. Existing private credential delivery, bounded
claims/roles, explicit app-UUID coexistence, independent rollback and native
acceptance procedures are in configuration/authorization/sso/README.md.
Headlamp has no deployment/restart side effects; its missing API OIDC trust still
needs separate approval. OpenBao can separately prepare only a missing owned OIDC
method; it refuses legacy/inherited authority and missing/wrong KV-v2 data engines.
Rancher preserves existing provider credentials on public-setting updates.

31 distinct SSO tests passed (7 render, 10 native CLI, 6 shared-client HTTPS,
8 OpenBao HTTPS), plus 12 core realm-admin regressions, targeted completed-app
rollback/coexistence, 6 legacy Rancher, 5 authorization, 10 workflow and 13 docs
checks. Syntax/C4 validation/build and diff checks passed. These are synthetic
state/contract checks, not live native token/UI enforcement evidence. Nonsecret
GET-only installed-version/scope inspection informed pinned compatibility; no
human authentication, app/client grants, credential generation, deployment,
provisioning or restart ran. Publication of this reviewed combined source scope is approved. Live batches
remain separately gated; obtain explicit staged activation/acceptance approvals.


## Headlamp SSO source-selection follow-up — not activated

#139 merged as 8214a169a38046d1dbccddbd95244cf3d9a4558c; feature checks and
post-merge workflows 41519066282 / 41519066296 succeeded. Read-only preflight found
three Ready nodes, available token-mode Headlamp and no API OIDC flags. Proposed
Headlamp client/Secret/CA/binding were absent. Host SSH/sudo recovery was not
verified because the execution environment had no usable SSH-agent identity.

The follow-up source adds only the optional local-headlamp-sso stage, selecting
the reviewed external-credential/public-trust Headlamp values. Old stages and
live v0.14.0/local-keycloak are unchanged. Offline Kustomize comparison preserves
all object identities and changes only bigbang/values-app-stage; pinned umbrella
render changes only the Headlamp generated values and its checksum annotation.
The pinned child consumes the versioned Secret and read-only public CA without
creating credentials or a cluster-admin binding.

A verified immutable release containing this stage is required before separately
approved tag/path promotion. Existing release PR #125 must include this source
before it can serve that purpose. No credential generation, API provisioning,
restart, deployment or app grant occurred. Follow the SSO runbook's release and
activation gate; no Headlamp live compatibility/owner login is claimed.


## Headlamp missing prerequisites — prepared source, not executed

Owner approved one focused prerequisite MR and publication. It adds a dedicated
default-off API OIDC host-maintenance/rollback entrypoint and a Headlamp-only HTTPS
route gate. Existing Ansible become prompting is used locally; no password is
stored or passwordless sudo added. Exact published source/target ownership,
base/config/service checksums, root-only host backup journal and matching owned
CA/drop-in content bound repeat/resume/rollback. Only rke2-server may restart.
Rollback requires matching host journal, not initial API availability; unrelated
config/service drift refuses automatic restoration.

Read-only live preflight previously verified the unlocked expected SSH identity,
strict known-host SSH and control-plane trusted Keycloak discovery. Sudo needs a
local password; Headlamp lacked its TLS Secret/Ingress and served Traefik's default
certificate. New routing reuses the authored ingress and emits only public
leaf/type from kubectl and validates backend/trusted HTTPS; it never applies the shared identity bundle.
Existing separately gated TLS delivery remains Headlamp-only with the existing
leaf/key/public-root bundle. No issuance, signing-key copy, trust change, live host
write/restart, route delivery, new SSO credential/grant or activation occurred.

#125 candidate 19c8e4c includes #140; workflow 41532185238 passed selection, SSO
and release checks. Hold release until this prerequisite change is included and
checks pass again. The later live batch still needs owner-local read-only inspect,
reviewed base hash/recovery, exact scope approval and human/native acceptance.
