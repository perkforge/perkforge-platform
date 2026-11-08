# Harbor token-signing identity

## Native format contract

Harbor 2.15.2 [derives JWT `kid`](https://github.com/goharbor/harbor/blob/a97e7b835d1364e2cc11fd706a15171a5c9d5d77/src/core/service/token/authutils.go#L140-L146)
with the [pinned libtrust parser](https://github.com/docker/libtrust/blob/aabc10ec26b754e797f9028f4589c5b7bd90dc20/key.go#L135-L163).
It requires PKCS#1 DER under `RSA PRIVATE KEY` for RSA; PKCS#8 `PRIVATE KEY`
fails even when the certificate and public key match. Changing only the PEM label
does not convert DER. Harbor's RS256 contract excludes the parser's EC alternative.
This restriction is token-only: network TLS and encrypted CA keys are unrelated.

`harbor-token-signing-pkcs1-v1` is an immutable, create-only application Secret
containing exactly `tls.key` and `tls.crt`. The certificate must match the key,
be current, and permit digital signatures. Existing RSA minimum checks are
unchanged; fresh issuance uses RSA3072.

## New cluster: issue once, then assemble and deliver

Dependencies: Ansible, Bash, Git, OpenSSL supporting `genrsa -traditional`, and
Python with the protected-input dependencies in [README](README.md#protected-input-procedure).
No cluster API, physical host identity, private path or deterministic key seed is
embedded in the producer. Each approved issuance uses independent OS randomness.

Example contents of the protected issuance variables file (replace every value
for the intended cluster before use):

```yaml
harbor_token_signing_run: true
harbor_token_signing_scope: harbor-token-signing-issuance-v1
harbor_token_signing_cluster_id: NEW_CLUSTER_LOGICAL_ID
harbor_token_signing_namespace_uid: EXACT_NAMESPACE_UID_OR_NOT_CREATED
harbor_token_signing_output_parent: /OWNED_PRIVATE_PARENT
harbor_token_signing_bundle_name: harbor-token-signing-pkcs1-v1
```

`cluster_id` is mandatory and stable for that cluster. Set namespace UID to the
observed UID, or literal `NOT_CREATED` only before that Namespace exists. These
receipt fields are offline operator declarations, not verified cluster/namespace
bindings. Assembly/delivery must subsequently bind and verify the actual UID.
Invoke from the reviewed checkout:

```sh
ansible-playbook -i localhost, big-bang-bootstrap/configuration/packages/harbor/prepare-token-signing.yaml -e @/PROTECTED/issuance-vars.yaml
```

1. Choose the reviewed release and intended cluster/namespace. Approve fresh
   local key issuance, then select an owned 0700 parent outside Git, with no
   symlink or group/world-writable ancestor. Supply protected operator variables
   to `prepare-token-signing.yaml`; do not put them in tracked files.
2. Run the producer once with its exact issuance scope. Default/check mode does
   nothing. It creates an exclusive bundle, RSA key, matching self-signed
   digital-signature certificate, public fingerprint receipt and `READY` only
   after successful validation. All private files are owned, single-link 0600.
3. Preserve the completed bundle. In the full application input mapping used by
   `prepare-credentials.yaml`, set `harbor-token-signing-pkcs1-v1` → `tls.key`
   and `tls.crt` to the absolute paths under its `delivery/token-signing/`.
   Keep the other 15 exact application inputs and trust pins. Use the existing
   `harbor-application-private-assembly-v1` gate and a fresh protected manifest.
4. After exact target/namespace/cluster and key-transmission approval, use the
   existing `harbor-application-credential-delivery-v1` create-only delivery.
   It preflights every target before any create. Existing identical objects
   are reused; changed or foreign targets stop the whole operation. Deliver
   before activating the reviewed `core.secretName` reference through GitOps.
5. Verify normal token issuance, bounded private push/pull, denied unauthorized
   access, worker-only placement and unchanged unrelated workloads/storage.
   Offline fixtures do not establish live acceptance on another cluster.

The signing entry in the protected **complete** application input mapping is:

```yaml
harbor_credentials_inputs:
  harbor-token-signing-pkcs1-v1:
    tls.key: /OWNED_PRIVATE_PARENT/harbor-token-signing-pkcs1-v1/delivery/token-signing/tls.key
    tls.crt: /OWNED_PRIVATE_PARENT/harbor-token-signing-pkcs1-v1/delivery/token-signing/tls.crt
  # Retain all 15 other exact application entries, not a signing-only manifest.
```

With those complete protected variables and the existing approval/pin fields:

```sh
ansible-playbook -i localhost, big-bang-bootstrap/configuration/packages/harbor/prepare-credentials.yaml -e @/PROTECTED/application-assembly-vars.yaml
ansible-playbook -i localhost, big-bang-bootstrap/configuration/packages/harbor/deliver-credentials.yaml -e @/PROTECTED/application-delivery-vars.yaml
```

These are distinct explicit gates, not an unattended whole-cluster deployment.
No private one-off generator or manual key conversion is needed for a new cluster.

The producer uses `openssl genrsa -traditional -out KEY 3072`, then
`openssl req -new -x509 -key KEY -sha256 -days 365` with digital-signature usage.
It does not use `req -newkey`, whose modern default can produce PKCS#8.
The same bundle name is refused on a repeat, whether complete or partial. For a
completed bundle, retain and reuse its inputs through the idempotent assembly and
delivery stages; do not rerun issuance. For partial output, preserve it for
inspection and obtain explicit approval before choosing a new bundle. Never
deliver a bundle without verified receipt and `READY`, or overwrite it to retry.

## Existing cluster: encoding repair without rotation

This is a separately approved recovery, not new-cluster issuance. Preserve the
original immutable `harbor-token-signing` Secret, local key/certificate and
original application manifest. Do not run the fresh producer for this repair.

1. Pin the reviewed release/commit, API/context, cluster UID, Harbor namespace
   UID, original signing Secret UID and approved public-key/certificate SHA256
   fingerprints in protected operator inputs. Read back the exact old immutable
   Secret under approved custody and confirm its complete data and ownership
   match the retained original manifest. Stop on any mismatch.
2. In a fresh protected output location, run Ansible `command` with `no_log: true`
   and owner-only custody to execute
   `openssl rsa -traditional -in OLD_KEY -out NEW_KEY`. Never overwrite OLD_KEY.
   Keep the certificate bytes unchanged. This converts encoding, not key identity.
3. Before any delivery, verify old/new RSA private numbers and public DER are
   identical, the complete certificate bytes and SHA256 fingerprint are unchanged,
   the key matches that certificate, and the new key passes the token-only native
   PKCS#1 guard. Check the original signing Secret UID/data again. A changed key
   or certificate is rotation and outside this repair.
4. Assemble a **new** application manifest with the one versioned signing target
   and the 15 unchanged original targets. Compare complete manifests privately:
   only the signing Secret name and key encoding may differ. Keep all custody,
   ownership, namespace and all-target preflight guards enabled.
5. After exact action-time key-transmission/security approval, deliver create-only.
   If the versioned target exists, require complete exact equality; never adopt,
   replace or delete it. Inspect uncertain outcomes before retrying. Readback must
   preserve the old Secret UID/data and every original unrelated target; a repeat
   must be zero-change.
6. Only then select the reviewed release with `core.secretName` pointing to the
   new Secret. The pinned chart mounts only `tls.key` into core at
   `/etc/core/private_key.pem` using `subPath`. The Pod template reference change
   rolls core; it is not hot-reloaded. The chart's registry uses htpasswd and has
   no signing-secret mount, so this repair does not require a registry restart.
   No other app/TLS/SSO/database/PVC/RBAC change is intended. Verify the effective
   render before promotion and live preservation afterward.

The same public key yields the same JWT `kid` and verifies the same signatures.
Encoding conversion does not invalidate issued tokens. A core rollout may briefly
interrupt requests. A rollback selects the prior reviewed reference, recreating
core with the untouched original Secret; for the known PKCS#8 input that restores
the original token failure, not a working repair. Keep both Secrets and manifests
through acceptance; cleanup needs separate approval.

## Restore or rotate later

- Restore the exact retained key/certificate from an approved, verified backup
  when the same identity is required. The private key cannot be reconstructed
  from a certificate, public fingerprint, Git or cluster name. This procedure
  does not create or verify an encrypted backup.
- Converting a retained PKCS#8 RSA key uses the same-key repair above.
- Generating another random key is **rotation**: a new certificate/public key,
  JWT `kid` and signing identity. Prepare an explicitly reviewed versioned Secret
  name/contract/reference, approve issuance and transmission, retain old material,
  deliver before switching core, and separately plan token/session compatibility,
  acceptance and rollback. Do not reuse `pkcs1-v1` to overwrite an existing identity.

## Offline evidence

The [native fixture](../../../tests/fixtures/harbor-token-signing/) runs the exact
libtrust dependency with synthetic RSA3072 material. It reproduces the PKCS#8
failure and proves PKCS#1 parsing, unchanged public DER/certificate match, JWT
`kid` and RS256 signatures. Python/real-Ansible fixtures prove token-only rejection
before manifest/API writes, create-only versioned delivery, old-object retention,
zero-change repeat and effective core-only reference changes. They do not access
real key material or demonstrate a live repair.
