# OpenBao — platform secrets control-plane

OpenBao is the platform's **secrets control-plane**. External Secrets Operator (ESO) reads
app/tenant secrets from it, and humans sign in through **Keycloak (OIDC)**. Its whole
configuration is **source-controlled and regenerable from Ansible** — a fresh adopter
provisions it by running the playbooks, not by hand-entering state.

All paths below are relative to the platform repo
(`big-bang-bootstrap/configuration/ansible/platform-config/`).

## Provision — create the config from Ansible

The config reconciler is idempotent and is the source of truth. It:

- reconciles the dedicated Keycloak **`openbao`** OIDC client (+ `groups` group-membership mapper),
- enables the `oidc` and `kubernetes` auth mounts,
- writes the OIDC config (discovery URL, client, secret) and the Kubernetes auth config,
- creates the OIDC roles (`home`, `platform`) and the Kubernetes role,
- applies the reviewed ACL policies (`human-home`, `human-platform`,
  `human-platform-tenant-access`, `eso-home-portal`, `snapshot-reader`).

Run:

```sh
# validate first (no API changes)
ansible-playbook configure.yaml \
  -e platform_checkout=/path/to/checkout -e keycloak_admin_username=<admin>

# apply
ansible-playbook configure.yaml \
  -e platform_checkout=/path/to/checkout -e keycloak_admin_username=<admin> \
  -e platform_api_apply=true
```

The playbook requires 0600 owner-private inputs (Keycloak admin password,
`openbao/recovery/bootstrap-token`) and a valid TLS CA (`-e public_ca_file=<lab-root-ca>`).
The desired client/roles/policies live in `packages/openbao/operations/{config,roles,policies}`.

Human access is granted by enrolling a user into the intended Keycloak group
(e.g. `/platform/admins` for the `platform` OIDC role).

## Operate

- **Human login:** both **platform users** and **tenant users** authenticate to OpenBao
  through Keycloak (OIDC). At the OpenBao UI, choose the OIDC method and pick the role that
  matches your Keycloak role:
  - **Platform role `platform`** → grants `human-platform` (+ `human-platform-tenant-access`).
  - **Tenant role `home`** → grants `human-home` (that tenant's own app secrets).
  - (Add a per-tenant OIDC role for any other tenant you onboard, mirroring `home`.)
  Sign in as your enrolled Keycloak user; the role you pick must match a group you belong to
  (see the authorization model below).

### Authorization model — OpenBao roles align to Keycloak roles

Keycloak owns the platform/tenant role hierarchy; each OpenBao OIDC role binds to the
group of the same name (via `bound_claims.groups`) so adopters reason in one place:

- **Platform roles:** `/platform/{admins,engineers,viewers}`
  - `platform` OIDC role → `/platform/admins` → `human-platform` (+ `human-platform-tenant-access`)
- **Tenant roles:** `/tenants/<tenant>/{admins,developers,viewers}` per tenant
  (the home lab today has tenants **`home`** and **`portal`**)
  - e.g. `home` OIDC role → `/tenants/home/admins` → `human-home`

When you add a tenant, create its `/tenants/<tenant>/{admins,developers,viewers}`
group subtree in Keycloak so the matching OpenBao OIDC role finds a real binding; keep the
role's bound-claims group and its policy's KV paths scoped to that tenant.
- **Unseal:** Shamir, 2-of-N. **Record the unseal shares, root token and TLS CA in the
  organization secret store (Bitwarden) at init/rekey time.** Never leave the only copy on
  a single host.
- **Backup:** the live server runs `storage "pebbledb"` with HA off, so raft-snapshot save is
  not available on the hot path. Back up by taking a **cold, age-encrypted copy of the sealed
  storage volume** (scale the StatefulSet to 0, tar + age-encrypt `/openbao/data/pebbledb`,
  restart) on a schedule, then **upload the archive to a durable off-site store and verify by
  independent round-trip** (upload → download → hash match → receipt). The storage is
  encrypted-at-rest, so the archive + the 2-of-3 keys is a complete restorable backup. The home
  lab uploads weekly to a private Proton Drive folder via a systemd timer; the same pattern
  applies to any off-site target.

## Recover (sealed / lost keys)

**If shares are recoverable:** `vault operator unseal` with 2 shares — done.

**If the key set is genuinely lost** (no share anywhere reachable), recover by
**clean re-init + re-seed** (do **not** attempt a hot raft-snapshot restore — see caveat):

1. **Preserve the recovery source first (before any destructive step):** snapshot every
   ESO-materialized k8s Secret (those hold the current secret values) and age-encrypt it.
2. Set the sealed storage aside on the PVC (keep it; it is only unsealable with lost keys).
3. Fresh re-init (throwaway threshold-1), then `vault operator rotate-keys` to your
   production 2-of-3. **Immediately store the new shares, root token and CA in Bitwarden.**
4. Enable KV v2 at `platform/` + `tenants/`; seed the referenced paths from the export.
5. Re-run `configure.yaml` (above) to rebuild OIDC/K8s auth, roles, policies and the
   Keycloak client; re-create the user/group enrollment.
6. If ESO SecretStores report `Unable to create client`, fix their `caProvider` ConfigMaps
   (each store trusts OpenBao via a per-store `caProvider`; a CA drift on those exactly
   surfaces that way), restart ESO, and verify every ExternalSecret is `Ready`.

**raft-snapshot restore caveat:** the live server runs `storage "pebbledb"` with HA off,
which disables the raft-snapshot API on the hot path. Snapshot restore is only validated on
an isolated `storage "raft"` instance, so it is not the primary recovery route.

## Security principles

- Unseal keys / root token / TLS CA / the OpenBao **backup age key** live in the org secret
  store (Bitwarden), not on a single host; the backup job keeps only a working copy of the
  public recipient (and age binary) in `~/.config/perkforge-recovery/openbao-backup/`.
- Never put certs or decrypted material under `/tmp`.
- Configuration is Ansible-owned and idempotent — an adopter reproduces it from the playbooks,
  not from an existing instance.

For this installation's concrete incident record, see the home-lab recovery repo's
`recovery/openbao/OPENBAO-RECOVERY.md`.
