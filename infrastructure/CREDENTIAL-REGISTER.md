# Real-cluster credential register proposal

Maintain one **private, metadata-only** register per real cluster, using
[`credential-catalog.example.yaml`](credential-catalog.example.yaml). The public
file is a schema/example, not an inventory of credentials that exist. The
[storage table](CREDENTIALS.md#ownership-delivery-and-retirement) describes proposed
logical locations. No discovery, migration, monitoring or rotation is implemented
by these documents; populated registers remain ignored and encrypted in backup.
Metadata can reveal access architecture, so restrict its readership too.

## Record contract

Create one record per independently issued/rotated credential and generation;
separate consumers/privileges where they differ. Record purpose/type, issuer,
cluster reference, owner/custodian and permitted role/scope. Reference each durable
source of truth, runtime/cache copy, encrypted backup and separately held recovery
material. Use logical references, never secret values, token-bearing URLs, private
keys, passwords, shares or decrypted kubeconfigs.

Use `expires_at` as an RFC3339 UTC timestamp from authoritative issuer metadata;
otherwise set **`unknown`** or **`not_applicable` with a reason**. Unknown is an
unresolved review item, not “never expires.” File modification time is not expiry.
Keep next policy review separate from hard expiry. Record last verification,
redacted evidence, renewal/replacement/revocation procedures, dependencies and the
person responsible for alert delivery/escalation. Record restore verification
separately; a configured backup location does not establish a usable backup.

Track automation in three independent dimensions: **supported** by the selected
provider/token/version (with evidence), **configured** for this cluster (with a
configuration reference), and **tested** end-to-end (with date/evidence). Renewal
support and replacement support are separate. Set unknown/false until established;
do not present this proposal as configured automation. Alert lead times, review
cadence, notification route and escalation owner still need operator decisions.

## Coverage checklist

Review every category below; create records for actual credentials, or record
“not used” with owner/date/evidence. This is a discovery checklist, not a claim
that every real cluster uses every item. Add application/vendor-specific categories
when discovered; “all credentials” requires an owned recurring completeness review.

- **Physical/OS:** human, automation and emergency SSH private keys/passphrases;
  host-console/sudo credentials; BMC/firmware/network-device administrators where
  present; RHEL subscription/repository credentials; disk/Windows recovery keys.
- **Cluster access:** RKE2 server, dedicated agent and expiring bootstrap tokens;
  platform-engineer OIDC/refresh credentials and kubeconfigs; separate test and
  elevated evidence identities; bootstrap/break-glass admin kubeconfigs;
  workload/ServiceAccount tokens. Tenants use Headlamp, not issued kubeconfigs.
- **Platform/identity:** Rancher local/bootstrap admin and API credentials; OIDC
  client secrets; identity-provider admin/test-user passwords, signing material and
  backing-database credentials. Track human and test identities separately.
- **Git/CI/registries:** repository deploy keys/access tokens, CI runner identities,
  webhook secrets and artifact credentials; **GHCR pull**, **GHCR publish** and
  **Registry1 pull** are separate categories/records, with distinct issuers/scopes.
  Separate Repo1 source access from Registry1 image access too.
- **OpenBao or Vault:** scoped service tokens, batch/periodic tokens where used,
  auth bootstrap material such as AppRole SecretIDs, and initial/emergency root
  tokens. Keep Shamir unseal shares, auto-unseal recovery shares and seal-provider
  credentials/key references in distinct records; never list share values.
- **Application/data/recovery:** database/service accounts, API/webhook/session
  signing/encryption secrets, storage/backup/object-store credentials, KMS/HSM
  identities, Ansible Vault passwords, SOPS/age identities, password-manager/MFA
  recovery material and backup-decryption references.
- **Certificates and keys:** leaf server/client certificates, their private keys,
  issuing intermediates, root CAs and trust bundles as linked but distinct records.
  Include ingress, API/node, identity, registry and secrets-service TLS where used.
  Certificates have validity dates; a private key has its own custody/rotation
  lifecycle and does not inherit an expiry from its file or paired certificate.

## Rotation means more than synchronization

**Renewal** extends an eligible lease/TTL; it does not necessarily change the
credential. **Replacement** issues a new credential, updates all consumers,
verifies access/restarts as required, then revokes the old credential. Track both,
including rollback and encrypted backup updates. Expiry of one dependency may
invalidate another credential before its recorded maximum lifetime.

- **GHCR:** identify the actual token kind and package permissions. GitHub documents
  PAT-classic and Actions `GITHUB_TOKEN` authentication paths. Job-scoped issuance
  is different from replacing a long-lived pull token. Do not assume that a
  fine-grained token, GitHub App token or unattended PAT replacement is supported
  for a given consumer. Verify issuance, expiry/policy, SSO and revocation at GitHub.
- **Registry1:** record the actual identity/provider token type and issuer-reported
  expiry. Big Bang documents multiple access paths; no universal token lifetime or
  automatic replacement capability is assumed here. Record renewal/replacement
  support as unknown until the current provider/account policy is verified.
- **OpenBao/Vault:** renewal depends on token type, renewable status, TTL/max-TTL,
  parent/auth role and policy; periodic renewal is not credential replacement.
  Root-token retirement/recovery is separate from routine service-token renewal.
  Unseal/recovery shares are not login tokens or renewable leases. Auto-unseal
  recovery shares cannot replace a lost seal-provider key/service.
- **ESO:** ExternalSecret refresh synchronizes provider values into Kubernetes;
  synchronization alone does not prove the provider issued a replacement or
  revoked the old credential. Record issuance, synchronization and consumer uptake
  as separate dependencies/tests. ESO installation is not part of this proposal.
- **Certificates:** a controller such as cert-manager can support renewal, but
  issuer auth, private-key rotation policy, DNS/challenges, Secret delivery and
  consumer reload must all work. Mark configured/tested only with cluster evidence;
  CA rotation and trust rollout need their own procedure. Certificate expiry
  metadata may be inspected later without exposing private-key bytes.

A future authorized register review should verify issuer metadata, enumerate
consumers and backups, flag unknown/near-expiry items, test alert delivery, then
exercise one replacement/renewal and restore in isolation. Start with dummy data;
real access, automation installation and credential changes need separate scope.

## Primary capability references (reviewed 2026-10-30)

- [GHCR authentication](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) and
  [GitHub PAT policy/expiry](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).
- [Big Bang Repo1/Registry1 access guidance](https://docs-bigbang.dso.mil/3.28.0/bigbang-training/docs/2_pre-install-prep/Access-Verification/): access-path reference, not an expiry promise for a selected account.
- [OpenBao tokens](https://openbao.org/docs/concepts/tokens/),
  [Vault tokens](https://developer.hashicorp.com/vault/docs/concepts/tokens) and
  [OpenBao seal/recovery](https://openbao.org/docs/concepts/seal/).
- [ESO refresh semantics](https://external-secrets.io/latest/api/externalsecret/) and
  [cert-manager certificate lifecycle](https://cert-manager.io/docs/usage/certificate/).
