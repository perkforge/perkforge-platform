# Current operator handoff

## Current checkpoint — 2026-11-01

The physical cluster has reached the first Longhorn storage acceptance checkpoint.
No further live action is authorized by this handoff. Never push main or merge on
the operator's behalf; preserve protected runtime evidence and other worktrees.

- control-1, worker-1 and worker-2 run RHEL 10.2 / RKE2 v1.36.5+rke2r1. The last
  checks showed all three Ready. One control-plane/embedded-etcd server means
  **no control-plane HA**. OS installation, key-only SSH/password-sudo, workload
  networking and sequential connected OS reboot checks previously passed.
- Flux's active `flux-system/cluster-config` source and `cluster-root` select
  **v0.11.3**, commit `84cc2b7a79fde4b3e72af093ca79a0f1de7fe7f9`.
  Source artifact and root applied revision matched that exact release; root was
  Ready/Healthy. Big Bang and Longhorn HelmReleases were Ready after separately
  approved single failure resets. Publication alone never promotes the live source.
- Longhorn 1.13.0 is installed, V1 only, on the two workers. Manager and CSI rollout
  checks passed. `longhorn` is a **nondefault** StorageClass: two replicas,
  `Retain`, `WaitForFirstConsumer`. Default disks share the workers' OS filesystems;
  reserved/minimum headroom is not a filesystem quota. Control-1 has no data replica.
- The operator explicitly accepts upstream Longhorn as trusted lab infrastructure.
  The diagnostic account receives cluster-admin; the manager role already has
  powerful RBAC-management rights. The installer has a reviewed **named bind**
  grant, not its own general cluster-admin binding. This is not least privilege.
  [Trust decision and procedure](big-bang-bootstrap/configuration/packages/longhorn/README.md).
- UI ingress remains absent. Rancher, Headlamp, Keycloak, OpenBao and tenant
  enrollment remain unselected. No application authentication was extended.
- Dedicated workstation PXE services/listeners/guard remain stopped as previously
  verified. This work performed no host/network/firmware change or node reboot.

## First storage test — passed, resources retained

The explicitly approved test created one unique namespace, one **1 GiB** claim and
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
The test pod sleeps for at most one hour; the claim/data remain after it exits.
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

## Next decisions

1. Review the retained test evidence and separately approve exact resource cleanup
   or further storage tests. No automatic teardown or data-volume deletion.
2. Plan recovery tests appropriate to this lab: replica loss/rebuild and independent
   application backup/restore are still untested. Replication is not backup.
3. Rancher is the next platform stage, through a reviewed Big Bang package selection
   MR/release and explicit runtime promotion/activation. Review DNS, TLS/public-CA
   and protected bootstrap inputs first; do not use a competing direct installer.
   Rancher Helm has no fabricated PVC dependency. Keep its later OIDC API setup
   separate from installation.
4. Install Keycloak separately when selected, then review the original groups/roles
   before extending application authentication. Do not silently discard the original
   identity design or extend SSO during storage/Rancher preparation.
5. Deferred ownership/configuration refactors are tracked in #95 and #14. They do
   not block this completed storage test. Kickstart and node-upgrade backlog work
   does not authorize reinstalling or upgrading any node.

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
OS trust checks passed; container/application trust and live HTTPS remain separate.
Independent CA backup/passphrase custody is unconfirmed. Application TLS delivery
is prepared in `configuration/ansible/platform-tls.yaml` under Big Bang bootstrap,
but is **not applied**; it requires its own released-source/target/security approval.
Reuse the existing Flux registry Secret; do not read, replace or rotate it as part
of ordinary release promotion.

Use the [platform operation order](big-bang-bootstrap/configuration/ansible/README.md),
[Longhorn procedure](big-bang-bootstrap/configuration/packages/longhorn/README.md),
[Rancher procedure](big-bang-bootstrap/configuration/packages/rancher/README.md),
[RKE2 procedure](infrastructure/ansible/RKE2.md) and [PXE procedure](pxe/README.md).
Do not rerun first-install provisioning on this installed cluster. Every new live
operation needs concrete approval; these recorded results are not continuous
monitoring or permission to repair unrelated systems.
