# Physical-cluster preparation and handoff

For issue [#13](https://github.com/perkforge/perkforge-platform/issues/13).
Preparation is offline; no running VM trial, host, credential or LAN is changed.
Local is the portable physical target; `profiles/il2` remains a separate selection,
and IL2 readiness/hardening is deferred.

## Tonight: completed review and remaining decisions

- PXE is a partial installer example. It lacks service provisioning, trusted loader
  selection, network bindings and MAC allowlisting. See [PXE steps](../pxe/README.md).
- Private inventory is retained at the existing ignored physical inventory path
  (`.secrets/physical/hosts.yaml` in the operator checkout), mode 0600: one server,
  two agents, reserved addresses checked offline. SSH remains `UNCONFIGURED`.
  Do not copy that inventory into this document or commit it. No secret read is
  needed to verify these nonsecret inventory fields.
- Decide exact RHEL 9 minor/media/entitlement, provisioning network/server, UEFI
  trust/NIC MACs, disks/Windows recovery, SSH admin/public keys/sudo and credential
  custody/backup destinations before live installation. No missing choice is
  inferred from the historical VM trial.
- `configure-hosts.yml` is a connection-free report, not an implementation of
  host hardening. NetworkManager, firewall/CNI, DNS/time, storage and package
  repository preparation remain explicit prerequisites, not automated claims.

## Offline commands (repository root)

These need existing Ansible/Python/PyYAML; do not install packages implicitly.
The committed inventory is empty and safe for these checks:

```sh
python3 -m unittest discover -s infrastructure/ansible/tests -v
ansible-playbook -i infrastructure/ansible/inventory/hosts.yml infrastructure/ansible/playbooks/configure-hosts.yml --check
ansible-playbook -i infrastructure/ansible/inventory/hosts.yml infrastructure/ansible/playbooks/install-rke2.yml --syntax-check
ansible-playbook -i infrastructure/ansible/inventory/hosts.yml infrastructure/ansible/playbooks/install-rke2.yml --check
ansible-playbook -i infrastructure/ansible/inventory/hosts.yml infrastructure/ansible/playbooks/install-rancher.yml --check
ansible-playbook -i infrastructure/ansible/inventory/hosts.yml infrastructure/ansible/playbooks/configure-rancher-oidc.yml --check
```

Set `ANSIBLE_LOCAL_TEMP` to a private temporary directory if the default is not
writable. Tests use synthetic data and stubbed clients. They establish controller
gates and rendering behavior, not actual package installation or cluster readiness.

## Tomorrow: one stage at a time

1. **Boot preparation:** review decisions in `pxe/README.md`; approve named boot
   services and network changes separately. Start with control-1 only, using the
   Lenovo one-time UEFI boot menu before Windows.
2. **Disk approval:** inspect serials/Windows backup at the console; stop before
   any write. Approve the exact target disk and data loss separately. Complete
   the first RHEL installation manually; confirm OS and public-key SSH handoff.
3. **Host preparation:** approve named SSH connections and OS changes separately.
   Review RHEL/RKE2 supported combinations, SELinux policy, required ports,
   NetworkManager/CNI exclusions, firewall policy, free disk/RAM and repositories.
   Do not blindly disable the firewall. See RKE2 [requirements](https://docs.rke2.io/install/requirements)
   and [known issues](https://docs.rke2.io/known_issues).
4. **Credential stop:** accept the [credential proposal](CREDENTIALS.md), demonstrate
   encrypted backup recovery, and supply the reviewed dedicated agent credential
   file before setting `rke2_credential_lifecycle_reviewed=true`. The installer now
   configures a separate agent token and refuses identical server/agent tokens.
   This flag records review; it does not implement backup or rotation. Installer
   defaults remain blocked; live token behavior still requires approved validation.
5. **RKE2:** review `ansible/RKE2.md` and nonsecret external vars: unique cluster ID,
   private output directory, CIDRs/TLS SANs, selected nodes and all apply gates.
   Use an inventory containing only the approved server for a server-only first
   stage; retain localhost. Do not use `--limit control-1` (it removes controller
   preflight/readiness). After a separate approval, the exact command shape is
   `ansible-playbook -i <private-inventory> infrastructure/ansible/playbooks/install-rke2.yml -e @<reviewed-private-vars>`.
   Do not run it tonight. Wait for that stage's evidence before enrolling workers.
6. **Rancher:** separately approve its capacity, supported RKE2 version, ingress,
   trusted TLS and recovery credentials; use `ansible/rancher/README.md`. Pinned
   chart versions are retained, not a new compatibility certification. Rancher
   manages platform clusters; Fleet stays an internal dependency with Continuous
   Delivery disabled.
7. **Flux/Big Bang:** follow `../big-bang-bootstrap/configuration/ansible/README.md`;
   inspect selected cluster/context/release pins, keep seed/reconciliation paused
   until its separate approval. Flux owns application GitOps. Validate each stage
   before advancing; no command here activates the historical VM trial.

## Audit findings and limits

Corrected host-preparation implicit facts, iPXE shell menu return, text-only disk
UI assumptions, automatic post-install reboot and
private destination creation before credential fetch. Refuse unowned existing
RKE2 config as well as data/binary state. Keep exact installer version/checksum,
serial agent joins, ownership/version/drift checks, no-log token/template tasks,
protected controller outputs and check/default gates.

Existing RKE2 partial-install state requires recovery review; it is not silently
adopted or upgraded. One server is supported; HA is not. Ownership markers are
accidental-target guards, not cryptographic identity or a backup system. Parent
directories and controller filesystem/umask must be private; no symlink race or
malicious local administrator protection is claimed. Rancher OIDC secret-file
changes alone do not rotate the client secret; a separate workflow is required.
Helm chart version pins are retained; chart digest/provenance policy is a later
review decision. Offline tests do not prove Secure Boot, Windows fallback,
Anaconda UI, SSH/sudo, SELinux/RPM availability, network/CNI, restart behavior,
Rancher login, restore or workload capacity.
