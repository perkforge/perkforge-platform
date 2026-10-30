# Credential custody and recovery proposal

**For review; no secrets have been read, generated, moved, rotated or backed up.**
`.secrets` is temporary runtime staging, not durable custody. The user has chosen
public-key node access with private keys on the workstation and encrypted backups.
Product, key separation, custodians, destinations and recovery policy remain
approval decisions. This is a small physical platform proposal, not IL2 readiness.

## Recommended starting point

Use an independently hosted encrypted password manager for human credentials and
bootstrap custody, a protected workstation SSH agent/key store for node access,
and independently encrypted off-cluster backup bundles. Keep recovery material
physically separate from the encrypted backups. Ansible Vault is optional for
small Ansible-only inputs; use SOPS/age only when a reviewed GitOps secret workflow
needs it. Do not make the cluster's own OpenBao the sole way to rebuild that cluster.

| Option | Useful role | Cost / recovery constraint |
|---|---|---|
| Hosted 1Password or Bitwarden | Human logins, test accounts, OIDC/bootstrap values, credential catalog and access sharing | External account/MFA recovery and export coverage must be tested; cloud sync is not an independent backup |
| Ansible Vault | Encrypt selected Ansible variables/files | At-rest protection only; shared vault passwords need separate custody; no lease, revocation or automatic backup lifecycle |
| SOPS with age | Encrypt authored YAML for Flux; public recipients can be reviewed | Private age identities must survive laptop/cluster loss; changing recipients does not revoke old Git ciphertext or rotate the underlying secret |
| OpenBao later | Scoped machine auth, leased/dynamic credentials, audit and runtime delivery | Operating/seal/restore dependency; deployment is currently unselected; requires its own tested recovery design |

I recommend choosing whichever hosted manager the operator already trusts, after a
dummy restore/export exercise. Do not self-host the only password manager on this
cluster. For Bitwarden disaster recovery, use a **password-protected** export;
account-restricted exports depend on the original account/key. Validate attachments,
SSH keys and organization collections separately against the selected export
format. For 1Password, its Emergency Kit restores account access; it is not an
independent copy of the vault. Select a separately encrypted export/archive process
before relying on it. No plaintext export should persist outside controlled staging.

## Names and nonsecret catalog

Use the same recognizable base name on workstation, password manager and encrypted
backup manifest: `perkforge-<target>-<purpose>-<operator>-<generation>`.
Examples (names only):

- `perkforge-physical-node-ssh-corey-2026-10` (one cluster/operator key option), or
  `perkforge-control-1-node-ssh-corey-2026-10` (per-node option).
- `perkforge-physical-test-viewer-corey-2026-10` and
  `perkforge-physical-rancher-breakglass-corey-2026-10`.

Private SSH file uses that base name; public half adds `.pub`; encrypted backup
keeps the base name inside its manifest. Do not name every key `id_rsa`. Record
public fingerprint, owner/custodian, purpose, permitted targets/role, durable item
reference, local path, backup generation/date, expiry/review date and last dummy
restore result in an ignored **nonsecret** catalog. A public template is
[`credential-catalog.example.yaml`](credential-catalog.example.yaml); never put
passwords, private keys, recovery shares or private addresses in it.

Choose key scope explicitly: one key per operator/physical cluster is easier to
manage but compromise reaches every authorized node; per-node keys reduce that
reach but increase backup/revocation work. Separate human, automation and emergency
identities; never reuse a personal/other-environment key by accident. Prefer
passphrase-protected private keys on an encrypted workstation, directory 0700,
files 0600, agent lifetime/confirmation limits and host-key verification. A spare
hardware-backed identity is an option; nonexportable keys require a spare/recovery
identity rather than a nonexistent private-key backup. Key algorithm depends on
RHEL crypto/FIPS policy, not an assumed universal default.

Only the approved **public** key may be supplied to a reviewed Kickstart `sshkey`
input or installed at the console. The current partial Kickstart has no user/key
input. Until reviewed, use console setup and confirm SSH/sudo before leaving it.
Private key paths belong in private inventory; no key generation or auth changes
are part of this PR.

## Ownership, delivery and retirement

Platform owner is accountable; name a backup custodian before live use. Maintain
a second independent emergency access method so the same laptop/phone/SSO is not
the only route to keys, manager, MFA, backup storage and decryption.

| Credential | Durable custody / least privilege | Delivery and rotation/revocation |
|---|---|---|
| Node SSH/become | Named operator key; distinct automation identity; approved sudo scope | Agent or protected key file, host-key pin verified by console; remove old authorized keys after replacement is tested; no password fallback invented |
| RKE2 server token | Platform recovery secret enabling server joins/bootstrap-data recovery; back up paired with each etcd snapshot generation | Root-only server storage; do not distribute to workers; rotate through supported maintenance and retain matching old recovery generations |
| Agent join credential | Dedicated static agent-only token for this installer; expiring bootstrap tokens are a later option | Root-only config/no-log transfer; revoke bootstrap token after join and test supported rejoin/restart behavior before deletion |
| Admin kubeconfig | Break-glass platform admin, not routine tests/users | Private explicit path/context; replace/renew via supported RKE2 certificate procedure; deleting a local copy alone does not revoke its certificate |
| Rancher local admin / OIDC client secret | Separate break-glass login and scoped confidential client; platform admin owner | Protected file/stdin to installer; rotate bootstrap/admin and client values deliberately, verify login and preserve local emergency access |
| Registry/automation tokens | Repository-scoped read-only pulls; separate publish token | Short expiry where supported, protected file/runtime injection; revoke at issuer and replace affected workloads |
| CA private material | Offline root if custom PKI is selected; separately scoped issuing material | Encrypted backup with trust-chain metadata; emergency CA replacement is a planned trust rollout, not delete-and-recreate |
| Test user/passwords | Dedicated test realm/users and least-privilege viewer/deployer/negative-test roles | Fetch only for the approved test; expire/disable afterward; no production admin reused for convenience |
| OpenBao root/recovery/seal | Separate custodians and recovery package | Revoke initial root token after scoped auth works; protect quorum shares or independent auto-unseal dependency; never store sole recovery in itself |

The installer now requires an explicit protected agent-token input, configures it
on the server and compares the resulting secure token against the server token
before worker joins. This is offline-tested behavior, not live token validation.
The server token permits server joins and decrypts bootstrap data, which can enable
administrative access; it is not directly a Kubernetes API bearer token. The
credential-review flag remains false pending accepted custody/restore decisions.
Existing Rancher OIDC reruns intentionally do not rotate a secret merely
because its file changed; a reviewed rotation must update provider and client,
verify authentication and revoke the old value.

## Test secrets: custody versus runtime

The password manager (later OpenBao) is the source of truth; the test process gets
only scoped, short-lived delivery. Unit tests use dummy values. Real integration
tests require separate live authorization and never borrow platform-admin access
unless that exact admin action is under test. Keep test-user lifecycle independent
of human emergency credentials; use purpose-named positive and denial identities.

Kubeconfig identities are distinct: humans use their individual OIDC identity;
automation gets a dedicated identity with only declared test permissions; bootstrap
and break-glass keep separate admin access. A test must state its needed role and
API operations. Cluster-wide evidence collection may require explicitly approved
elevated access, separate from tenant/denial tests; do not default to admin to make
tests pass. Prefer short-lived credentials where supported, not persistent
ServiceAccount tokens by default. Kubeconfigs may invoke exec plugins: trust and
pin the plugin/toolchain, review the source before use and never run an untrusted
kubeconfig. Bound token caches and clean them with the run's protected files. No
kubeconfig, grant or identity is created tonight.

For an approved run, retrieve only required items on a trusted workstation/runner.
Use private temporary directories (0700), precreated files (0600), restrictive
umask and explicit paths; prefer supported file/stdin APIs over argv/URLs. Avoid
shell tracing, debug/fact dumps, verbose HTTP traces, screenshot/token capture,
core dumps and artifact uploads. Mark secret-bearing Ansible tasks `no_log` and
keep fact caching off; check-mode must not read secrets. Masking is a secondary
measure and may miss transformed values. Clean up in `finally`/exit handlers,
including failed runs; check for abandoned files after crashes. Secure deletion
cannot be guaranteed on SSD/snapshotted storage, so use encrypted storage and
minimal plaintext lifetime. Environment variables can leak through process
inspection/dumps; they are not a universal safe substitute for files.

Secrets necessarily exist in authorized process memory and are visible to trusted
runner administrators/compromised tools. Do not claim zero exposure. Use a dedicated
trusted runner, bounded sessions and approved tools; never deliver real secrets to
untrusted PR code. A future dummy-only acceptance test should inject recognizable
sentinels through success/failure paths, check stdout/stderr/reports for leakage,
verify file modes and cleanup, and prove unrelated credentials were not fetched.
This PR adds no real-secret test runner or password-manager integration.

## Backup and simultaneous laptop + cluster loss

Proposed objectives to accept: backup before/after credential changes and daily
cluster snapshots; maximum 24-hour recovery-point loss; initial recovery within one
day, to be measured in a drill. Keep seven daily and four weekly generations plus
one verified pre-rotation generation until no retained snapshot depends on it.
Encrypted backups remain sensitive and access-controlled; retention increases the
number of old valid secrets requiring custody.

Keep a workstation copy, an encrypted offline removable copy and an encrypted
offsite copy outside the cluster and workstation. Store decryption/recovery
material in a separate protected physical location/custodian; not only in the
password manager being restored, the same bag as the drive, or the lost phone.
Record backup credentials/MFA recovery independently. Use authenticated encryption,
versioned manifests/checksums and documented tool/version metadata; do not invent
homegrown crypto. The bundle includes key files, supported manager export plus
omitted attachments, inventory/catalog, bootstrap/CA recovery, etcd snapshots with
their **original server tokens**, Rancher/app-data backups and later OpenBao
snapshots/configuration. Git configuration alone cannot restore persistent data.

A later authorized drill must start from a clean replacement workstation with
**both original laptop and cluster unavailable**:

1. Recover independent manager/MFA and backup-storage access via the separate kit.
   Obtain encrypted bundles and the separate decryption material; verify manifests.
2. Restore to an isolated encrypted workspace; confirm catalog/file coverage and
   public SSH fingerprints without printing secret bytes. Test a dummy manager
   import first; include attachments and key formats, not just login records.
3. Restore the selected RKE2 version/snapshot with its matching original token,
   networking/trust and persistent-data plan. This is a separately approved live
   recovery, not tonight's check. Prove API/admin/SSH access and application data.
4. Restore OpenBao independently when adopted; verify seal dependency and auth,
   then Rancher/OIDC, registry and scoped tests. Record recovery time, snapshot age,
   missing dependencies and nonsecret evidence. Rotate/revoke lost-device access
   and used emergency credentials; make a new verified backup generation.

Run a dummy restore before first provisioning, a real isolated restore after
initial setup and quarterly/after recovery design changes. Hash checks alone do
not prove decryption, import, unseal or service recovery. Do not destroy original
credentials/backups until the replacement and rollback period are verified.

## OpenBao transition

Keep bootstrap custody outside the cluster. Adopt scoped auth/policies and short
leases gradually; migrate one credential class, verify issuance/revocation and
backup/restore, then retire duplicate plaintext staging under separate approval.
Do not automate this migration tonight. Choose Shamir quorum/custodians or an
independent auto-unseal service with its own disaster-recovery plan; do not choose
share counts without real custodians. With Shamir, preserve required unseal shares
separately. With auto-unseal, recovery keys **cannot replace a lost seal key or
service**. Back up Raft snapshots and configuration/TLS/plugin dependencies; test
with the selected OpenBao version before trusting recovery. Never make an
in-cluster transit/seal service the only dependency for restoring itself.

## Primary references (reviewed 2026-10-30)

- [Ansible Vault](https://docs.ansible.com/projects/ansible/latest/vault_guide/vault.html): encryption at rest and runtime responsibility.
- [SOPS](https://getsops.io/docs/): encrypted file formats and key backends.
- [1Password Emergency Kit](https://support.1password.com/emergency-kit/) and
  [Bitwarden encrypted exports](https://bitwarden.com/help/encrypted-export/): independent account recovery/export constraints.
- [RKE2 tokens](https://docs.rke2.io/security/token) and
  [snapshot restore](https://docs.rke2.io/datastore/backup_restore): server privilege and original-token dependency.
- [OpenBao seal](https://openbao.org/docs/concepts/seal/) and
  [Raft snapshots](https://openbao.org/docs/commands/operator/raft/): seal dependency and backup/restore primitives.

Decisions for the next review: manager, SSH scope/algorithm, named custodians,
encrypted backup tool/destinations and retention/objectives, test identity roles,
live agent-token validation and the first recovery drill. Nothing here authorizes a
secret migration, new account, credential rotation or live backup.
