# Current operator handoff

## Current checkpoint — 2026-11-01

OpenBao initial administration, Rancher installation and the first Longhorn storage test passed. **No further live
action is authorized by this handoff.** Never push main or merge for the operator;
preserve protected evidence, retained test data and other worktrees.

- Three physical nodes run RHEL 10.2 / RKE2 v1.36.5+rke2r1; node health and
  conservative scheduling headroom passed the Rancher preflight. One control-plane/
  embedded-etcd server means no control-plane HA. Previous key-only SSH/password-
  sudo, networking and sequential connected OS reboot checks passed.
- Flux source and root now select **v0.13.0**, exact commit
  `9bf49bb7421d49610ff9cc125b01cc18caa438ac`, default OpenBao-only app stage
  (retaining Longhorn/Rancher). Publication/CI and exact artifact were verified.
  Root/umbrella/OpenBao/Rancher/Longhorn fresh Ready at **15:29:57Z**.
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
  trusted loopback TLS. Temporary port-forward closed; no ingress/OIDC/Kubernetes
  auth or policy mappings enabled. Headlamp/Keycloak remain disabled and undeployed.

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

## Next app selection — Headlamp requires separate approval

OpenBao initial administration acceptance passed; independent custody transfer,
root-token retirement/scoped recovery design and backup/restore remain pending.
Headlamp and Keycloak are merged source stages, not live deployments. A combined
release must use the [ordered app stage roots](big-bang-bootstrap/configuration/ansible/README.md#ordered-app-stages):
OpenBao-only default (retaining Rancher/Longhorn), then Headlamp, then Keycloak/database.
Each forward root-path promotion requires separate approval and successful access,
custody and health/capacity acceptance. The immutable source stays identical;
publication does not activate apps. The OpenBao stage was separately approved and completed; later stages are not authorized.

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

## Queued Headlamp candidate

Stacked after OpenBao: selects Headlamp 0.45.0-bb.1 in token mode with worker
placement, no ingress or Keycloak client settings. Existing OIDC files and proven
group/RBAC tests are preserved as explicit historical fixtures. Admin-login
acceptance needs a separately approved Kubernetes token identity and lifetime;
no native password or permanent cluster-admin account is invented. See the
[Headlamp procedure](big-bang-bootstrap/configuration/packages/headlamp/README.md).

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
2. Review queued OpenBao, Headlamp, Keycloak and disabled authorization drafts in
   dependency order. Each activation needs a verified release, concrete target,
   scoped credentials/TLS/prerequisites and separate approval. Preserve existing
   proven group/policy configuration for review after Keycloak is installed.
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
