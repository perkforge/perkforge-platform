# Current operator handoff

## Inactive logging draft

The [logging candidate](big-bang-bootstrap/configuration/observability/logging.md)
adds scoped API collection and authenticated TLS Loki with 3d/10Gi retention.
No selection, credentials, permissions or live acceptance. Operator-generated
workloads, Alloy binary validation, query auth and network enforcement remain gates.

## Current checkpoint — 2026-11-01

Rancher installation and the first Longhorn storage test passed. **No further live
action is authorized by this handoff.** Never push main or merge for the operator;
preserve protected evidence, retained test data and other worktrees.

- Three physical nodes run RHEL 10.2 / RKE2 v1.36.5+rke2r1; node health and
  conservative scheduling headroom passed the Rancher preflight. One control-plane/
  embedded-etcd server means no control-plane HA. Previous key-only SSH/password-
  sudo, networking and sequential connected OS reboot checks passed.
- Flux source and root now select **v0.12.0**, exact commit
  `44083aa4413a135ddc65eb6664d92851057b9e6f`. Publication and CI were verified
  before the separately approved promotion. Rancher Ready at **03:23:32Z**, Big Bang
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
- OpenBao, Headlamp and Keycloak are queued source candidates, **not deployed**.
  Ordinary publication does not promote the pinned live source. No credentials
  or identity integrations were created for them.

The Rancher/RKE2 matrix includes our Kubernetes/OS versions, but lists Longhorn
1.12 rather than independent 1.13. This lab combination is not claimed fully
vendor-certified. One Rancher replica/control-plane is not HA. Required rollout
and HTTPS checks passed; real browser login and lifecycle operations remain
unverified. No competing direct Ansible/Helm installer is used.

Protected `.rke2-state/` retains the activation summary, exact source/root/Helm
objects, authorization/capacity checks and automatically saved redacted Ansible
output. The ignored owner-only `app-admin-cache/` contains Rancher's admin username
and bootstrap-password flat files plus metadata. No values belong in Git/chat.
The operator owns proper-store migration and explicit temporary-copy cleanup;
changing a cached file is not server password rotation. Other app entries remain
pending or not applicable; no OpenBao unseal material is bundled there.

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

## Queued OpenBao candidate

This feature adds OpenBao 2.7.2/chart 0.30.6 after the merged Rancher source stage.
It is not deployed. TLS-required single-server PebbleDB on a 10Gi Longhorn claim
is a non-HA lab choice; no ingress, Kubernetes auth delegation, auto-init/unseal
or OIDC integration is enabled. Namespaced installer prerequisites are separate
from Flux deployment. New-store initialization, unseal shares, admin token custody
and verified client login require explicit future approval. A sealed server is
NotReady; the draft does not claim admin access is already usable. See the
[OpenBao procedure](big-bang-bootstrap/configuration/packages/openbao/README.md).
Existing proven policy/role/API configuration is retained for later review.

## Queued Headlamp candidate

Stacked after OpenBao: selects Headlamp 0.45.0-bb.1 in token mode with worker
placement, no ingress or Keycloak client settings. Existing OIDC files and proven
group/RBAC tests are preserved as explicit historical fixtures. Admin-login
acceptance needs a separately approved Kubernetes token identity and lifetime;
no native password or permanent cluster-admin account is invented. See the
[Headlamp procedure](big-bang-bootstrap/configuration/packages/headlamp/README.md).

## Queued Keycloak candidate

Stacked after Headlamp: chart 7.3.2-bb.1/Keycloak 26.8.0 with the pinned database
and a separately prepared Longhorn claim. Initial master bootstrap administration
only; no startup realm import, PerkForge groups or app client integration. Protected
bootstrap/database/pull/TLS delivery and real first login remain future approvals.
Ansible retains realm API ownership separately from Helm deployment. See the
[Keycloak procedure](big-bang-bootstrap/configuration/packages/keycloak/README.md).

## Queued authorization review

After the three app drafts, the authorization draft renders disabled PerkForge
realm/groups/client, tenant RBAC and OpenBao role/policy proposals with Ansible.
Nothing selects or applies them. Canonical /platform/admins is retained; tenant
roles use /tenants/<id>/admins or developers. Realm administration remains separate.
Admission/workload identity, claim disclosure, broad OpenBao admin scope and the
Longhorn admin proxy path still need decisions before activation. Existing API
configuration additionally defaults to platform_api_apply=false. No users, client
secrets or live memberships are created. See the
[review contract](big-bang-bootstrap/configuration/authorization/README.md).

## Observability follow-on — partial draft only

#35/#36 has an inactive architecture/source-pin and native values review, after
the app/auth stack. Monitoring/Grafana locally rendered; full installer/lookup/RBAC
and CRD compatibility audit, Alloy/Loki configuration, six dashboards, one verified
ntfy path and #37–40 acceptance remain unfinished. No package is selected or
activated, no credential/destination is created, and Myles provisioner is excluded.
See the [review and explicit limits](big-bang-bootstrap/configuration/observability/README.md).

## Metrics/Grafana implementation candidate

A subsequent inactive #37 candidate implements ten CRD renders, full selected
object/binding/escalation/lookup checks, supported admission certificate patch jobs,
three scoped installers, namespace ConfigMap-only Grafana sidecar access and six
starting dashboard documents. Default-off Ansible requires exact protected API
source inputs before foundation/network writes. No root selects it; credentials,
actual scrape/tenant/policy/admin behavior and resource/restore acceptance remain
unverified. See [implemented scope and gates](big-bang-bootstrap/configuration/observability/metrics.md).

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
