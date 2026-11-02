# Headlamp API OIDC maintenance — separate approval required

`playbooks/configure-api-oidc.yml` is maintenance, not installation. It selects
only `control-1` from the explicitly supplied private physical inventory. Default
and check mode select no SSH hosts and read no credentials or APIs. It requires
an immutable published release, its exact clean checkout, exact cluster/install
identity, reviewed issuer/client/public CA and independent recovery approval.
Only the owner enters sudo through Ansible's existing `--ask-become-pass` prompt.
SSH uses the existing key/agent, strict known hosts and no forwarding or trust
updates. Never save sudo/password values, enable passwordless sudo or assume a
`sudo -v` in another terminal authorizes this process.

## Owner-local procedure

Do not run these commands merely because source CI passed. Publish/verify the
release containing both maintenance and routing entrypoints first. Keep the
existing client-certificate kubeconfig and SSH recovery independent of Keycloak;
confirm recovery custody and the current single-control-plane outage window.
Author a private input file from `api-oidc.example.yml`, using the reviewed public
CA and actual install/cluster identities. No private signing key, client secret
or sudo password belongs in this host input file.

After approval for read-only inspection, run from the clean released checkout:

```sh
ansible-playbook -i /ABSOLUTE/PATH/TO/private-physical-inventory.yml infrastructure/ansible/playbooks/configure-api-oidc.yml --ask-become-pass -e @/ABSOLUTE/PATH/TO/reviewed-api-oidc.yml -e api_oidc_run=true -e api_oidc_operation=inspect
```

Inspection checks the owned installation, base/drop-in/service environment and
independent certificate access; it reports only base SHA256 and journal phase.
Review the reported base checksum and set `api_oidc_expected_base_sha256` privately
before seeking apply approval. Nothing is installed or backed up by inspection.
Use the same command with **`api_oidc_operation=apply` only after approval**.
This is one local invocation/prompt; do not send the password to chat or to an
agent. The operator remains present for this privileged batch. Both source and
live approval are required; `api_oidc_recovery_verified` is an acknowledgement,
not a substitute for testing recovery.

## Exact host writes and readbacks

The playbook never rewrites `/etc/rancher/rke2/config.yaml`, other drop-ins,
service units/environment files, DNS, firewall, OS trust, credentials, workers,
RKE2 version or datastore. It refuses pre-existing authentication settings,
service config/API-argument overrides, duplicate CA mounts, later drop-ins that
would reset API arguments, unknown installation/journal ownership, links or
baseline drift. Configuration and environment contents remain under `no_log`.

It creates only root-owned `config.yaml.d/90-perkforge-oidc-v1.yaml` (0600), public
`identity/ca.crt` (0644), and a `perkforge-oidc-v1/` journal/backup directory (0700,
files 0600). Missing parent directories are created; existing directory modes are
preserved. No existing CA or OIDC file is adopted, rotated or overwritten. Backups
of base/other YAML files stay on the host; they may contain credentials and must
never be fetched or published. Retain them for separately reviewed cleanup.

The drop-in appends exact issuer, audience/client, required azp, sub/oidc:
username, groups/oidc: groups, RS256 and CA-file arguments. It adds no hosts-file
or duplicate CA mount. RKE2 supplies its automatic read-only CA-file mount. Actual
host HTTPS discovery must validate using this CA and match issuer/S256/RS256
before the drop-in is written. Only then is **rke2-server restarted**. This lab
has one control-plane, so API/Flux control operations are temporarily unavailable;
workload continuity is not guaranteed. The play verifies independent certificate
API readiness/cluster UID, exact runtime OIDC arguments/read-only CA mount, every
inventory node Ready and unchanged unrelated configuration bytes.

An active repeat makes no restart or config changes. Prepared transactions resume
only matching partial files; drift stops. A failed restart/health check leaves an
owned inspectable journal, not an automatic second restart or broad repair. If
API access is unavailable, use the separately approved rollback below rather than
retrying apply. A crash between journal-directory creation and its owner record
leaves an ambiguous directory and deliberately requires operator review. Serialize
maintenance runs; do not run apply/rollback concurrently.

## Recovery and rollback

Use the same owner-local command with **`api_oidc_operation=rollback` only after
explicit rollback approval**. It uses the exact clean original source commit and matching host journal;
rollback performs no GitHub release lookup, so an unrelated GitHub outage does
not block host recovery. Apply/inspect verify the published immutable release. It
it needs neither initial API availability nor a client secret/public-CA file.
Keep the original issuer/client/cluster/base-hash inputs. It first verifies exact
owned file hashes, unchanged base/drop-ins/service environment and root ownership.
It removes only the transaction's CA/drop-in, restarts rke2-server and verifies
certificate API recovery, cluster UID, absence of OIDC flags and nodes Ready.
A persisted rollback-pending phase can resume after interruption; repeats verify
health without another restart. It keeps the root journal/backups and empty
parent directories. Apply after completed rollback requires a new reviewed
transaction, not silent reactivation. If an unrelated file or owned file drifted,
stop for manual SSH review; never restore whole backups over unrelated changes.

Application rollback is separate: remove only Headlamp's owned Kubernetes grant,
disable/unmap only its Keycloak client, restore the prior approved GitOps stage,
then remove its exact expected-client contract after readback. Preserve existing
realm-admin, master, other applications, certificate recovery and referenced TLS
objects. Offline JWT claims may survive until expiry; no blanket logout or
instant revocation is claimed. None of these steps is an authorization to restore
etcd, reinstall, reboot nodes or retire independent recovery.

Offline tests execute the actual Ansible modules against private temporary files,
synthetic service/API state and trusted loopback HTTPS. They establish transaction
behavior, not live RKE2 restart compatibility or owner MFA/browser acceptance.
