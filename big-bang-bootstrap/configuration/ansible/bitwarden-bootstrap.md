# Bitwarden recovery bootstrap

Bitwarden Password Manager provides explicitly selected initial/recovery inputs.
After OpenBao is available, a separate phase populates only the required downstream
values in its existing `platform/` KV-v2 engine. OpenBao and scoped ESO delivery
remain the ongoing secret-management path. This procedure is part of recovery
[#101](https://github.com/perkforge/perkforge-platform/issues/101), not an alternative
GitOps controller or proof of a completed restore.

`bitwarden-bootstrap.yaml` is opt-in, runs locally and is not imported by bootstrap,
Flux or CI. Default and check mode do not read credentials or contact a server.
One reviewed source works with each explicitly selected inventory/environment.
There are no home-lab credentials, hardware identities or environment guesses in
source. CI gates remain off.

To create an approved Login item before recovery, follow the separate
[credential storage procedure](bitwarden-credentials.md). This adapter only reads
existing items; it neither creates them nor verifies credential issuance.

## 1. Review the runtime mapping

Copy [the example](bitwarden-bootstrap.example.yaml) to an ignored, operator-owned
0600 runtime file. Set the exact target inventory environment, Bitwarden account
UUID/server URL/organization, immutable item UUID, expected item name, exact
collection membership and `username` or `password` Login field for each required
file. Verify each item's environment and purpose independently. A descriptive
name, membership in the imported set, or an import count does not establish that
an item belongs to this target. Missing/empty fields fail, with no fallback to
another item, field or generated password.

- `sources` keys are flat output filenames. Select the minimum required values.
- `purpose: initial` is local-only. Use this for bootstrap/recovery inputs that
  must not be stored in the secret engine they recover. Root tokens, unseal shares,
  Bitwarden sessions, CA signing keys and SSH private keys are not downstream data.
- `purpose: downstream` may be referenced by `platform[].fields`. Each destination
  is an explicit whole key/value record under `platform/bootstrap/<environment>/`.
  This MR does not assign actual production items or claim every imported item is
  needed. Username and password may reference the same Login item; it is read once.
- CA/SSH material and incomplete imported items require their own verified custody.
  This Login adapter does not read notes, custom fields, attachments or whole vault
  exports. Do not stuff unrelated recovery bundles into a downstream field.

Existing shared secret work is tracked in
[#31](https://github.com/perkforge/perkforge-platform/issues/31). The existing
`eso-home-portal` policy reads one **tenant** registry path and remains unchanged.
Do not widen that role or reuse it for platform seeding. New ESO consumers need
separately reviewed exact platform paths, namespaces/service accounts, auth roles
and SecretStore/ExternalSecret configuration. No consumer grants, workload restarts
or ESO activation are performed here. Until those are reviewed, seeding does not
prove downstream delivery or rotation.

## 2. Stage initial inputs independently of the cluster

Use a reviewed checkout on a protected workstation with trusted filesystem and
Ansible callbacks; never enable shell tracing or secret-debug callbacks. The
supported existing Password Manager CLI is `bw` 2026.10.1, supplied by an absolute
path. No install, server reconfiguration, login, unlock, sync or session creation
is performed by this procedure. The owner separately authenticates/unlocks and
syncs the intended vault, then provides its existing `BW_SESSION` through the
local process environment, never command arguments, chat, Git or a vars file.
Vault status must match the exact account/server and be unlocked. Review freshness
before recovery: the CLI's local cache is not independently proven current by
this adapter. A stale but valid vault value cannot be detected from its name.

After action-specific approval to retrieve these mapped fields and stage them:

```sh
ansible-playbook -i /ABSOLUTE/target-inventory.yaml \
  big-bang-bootstrap/configuration/ansible/bitwarden-bootstrap.yaml \
  -e @/ABSOLUTE/protected-runtime-inputs.yaml \
  -e bitwarden_bootstrap_stage=true
```

Output is `.secrets/bitwarden-bootstrap-<environment>/` in this checkout, protected
0700 with 0600 files and checked Git ignore coverage. Existing custody directories
must already have correct ownership/mode. Symlinks, hard-linked destination files,
unsafe modes, wrong item identities/ownership/collections and changed mappings are
refused. All selected values are validated and existing files compared before any
new output is written. Exact bytes, including final newlines, are preserved. An
identical repeat changes zero; differing values stop without replacing files.
The metadata-only `manifest.json` marks completed staging and binds the mapping.
No secret hashes or values are written to logs or this receipt.

Use individual staged file paths with the existing bootstrap/provisioning
entrypoints, for example `registry_credential_file` for the initial Flux pull
credential. This does not execute them. Published-release verification, cluster
identity, immutable image/chart refs, paused seed, explicit registry delivery and
separate resume/deployment approvals still apply. Do not rerun first-install
bootstrap on an active cluster. Never distribute RKE2 server tokens to agents.

## 3. Seed only missing downstream platform values

First recover/initialize/unseal OpenBao and its existing `platform/` KV-v2 mount
through their separately approved procedures. Do not initialize a restored store
again. Verify its trusted HTTPS origin, public CA and actual OpenBao cluster UUID,
not just its Kubernetes context. This play checks cluster identity **before**
sending its token and refuses redirects/proxies/TLS verification bypass.

Supply an existing short-lived token in an operator-owned 0600 file. It must have
only the explicitly named `bitwarden-bootstrap-<scope>` policy, no identity/default
policies, and at most one hour remaining TTL. Provisioning that scoped policy/token
is a separate security action; this play never creates or expands access. Do not
use the bootstrap root token or a human platform-admin token. A least-privilege
policy for the example's *one reviewed record* is:

```hcl
path "auth/token/lookup-self" { capabilities = ["read"] }
path "platform/data/bootstrap/ENVIRONMENT/registry" {
  capabilities = ["create", "read"]
}
```

Use one exact rule per approved record, no wildcard/list/tenant/update/delete/
metadata-destruction/policy/auth authority. OpenBao's internal UI mount endpoint
authorizes discovery from the destination data capability, without a broad mount
listing grant. The policy name is a guard, not proof of its contents: independently
review the actual ACL before issuing the scoped token. Existing mount/auth setup
and token issuance require their own approval and are not prerequisites for merely
reviewing this MR.

After separate approval for the exact OpenBao destination and mapped values:

```sh
ansible-playbook -i /ABSOLUTE/target-inventory.yaml \
  big-bang-bootstrap/configuration/ansible/bitwarden-bootstrap.yaml \
  -e @/ABSOLUTE/protected-runtime-inputs.yaml \
  -e bitwarden_bootstrap_seed=true
```

This phase does not call Bitwarden. It requires the complete unchanged staging
manifest, reads only downstream files, verifies every destination mount and reads
all exact destinations before writing. A present record must equal the **whole**
expected object; a mismatch or extra key stops for rotation/recovery review.
Missing records use KV-v2 `cas: 0`, so races and soft-deleted/destroyed versions
cannot silently overwrite/recreate existing history. Exact readback is required.
Same-value repeats create no new versions. There is no automatic rollback,
rotation, deletion, retry after an ambiguous write, or root-token fallback.

## 4. Resume and acceptance boundaries

If interrupted, preserve the staging directory and OpenBao values. A partial local
stage can be resumed with the same mapping and unchanged source fields; completed
files must match. Missing receipt means seeding refuses until staging succeeds.
After an uncertain server response, inspect the exact approved path through this
same create-only operation: equal data is reused, different data is refused, and
CAS zero prevents overwriting a version whose response was lost. A multi-record
seed is not a transaction; earlier successful records remain if a later one fails.
Never claim rollback or erase them to make a test pass.

A new mapping/credential version needs a separately reviewed fresh custody location
or explicit manual migration, not deletion to bypass these guards. Local retirement,
vault export to another provider, USB/offline custody changes, session/token
revocation and OpenBao root retirement (#33) are separate actions. Keep independent
recovery material until an isolated restore verifies it, including laptop-plus-
cluster loss. Bitwarden values alone are not etcd/Raft/PV backups; preserve matching
snapshots, tokens, encryption keys and independently recoverable vault access.

Offline tests use only synthetic values, a fake exact-ID `bw` and loopback TLS.
They cover inert modes, identity/environment/field/custody refusal, verbose/diff
redaction, exact bytes, no-overwrite repeats, TLS/cluster/token/mount checks, CAS,
interruption and downstream-only population. Native OpenBao tests separately verify
KV-v2/CAS/least-privilege behavior using the existing pinned 2.7.2 fixture. Neither
proves access to the real vault, environment assignments, live recovery, scoped
credential availability, actual ESO delivery or disaster-recovery acceptance.
