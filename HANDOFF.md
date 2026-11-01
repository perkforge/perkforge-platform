# Current operator handoff

## Current checkpoint — 2026-11-01

Keycloak initial master administration, OpenBao LAN HTTPS, Headlamp temporary-admin acceptance, Rancher installation and the first Longhorn storage test passed. **No further live
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

## Prepared realm/group foundation — no live changes

`configuration/authorization/foundation.yaml` under big-bang-bootstrap is the
new default-off Ansible entrypoint for the owned PerkForge realm and empty six-role
group families. It creates no users/memberships/clients/role grants, credentials or
app integrations. Existing trial bootstrap and disabled review render are separate.
Synthetic HTTPS protocol/safety tests cover positive creation/idempotence/resume
and negative ownership, mapping, target, CA and access cases; live acceptance is
**not executed**. See the [approval/input/recovery scope](big-bang-bootstrap/configuration/authorization/README.md#realmgroup-foundation--implemented-not-applied).
Next: review/merge this feature MR, then separately approve the exact tenant list,
existing master credential use and realm/group writes. Preserve master recovery;
no account retirement, app SSO or delegated tenant administration is implied.

## Next configuration — recovery and identity remain separately gated

OpenBao, Headlamp and Keycloak initial acceptance are complete on the same v0.14.0
artifact using the [ordered stage roots](big-bang-bootstrap/configuration/ansible/README.md#ordered-app-stages).
No further app is authorized. Establish independent Keycloak permanent recovery,
review the six-role matrix and separately approve incremental PerkForge realm/
group/client configuration. Initial master administration is not that rollout.
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
