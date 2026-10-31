# Physical RKE2 installation

The reusable RPM install/configuration/join/readiness primitives come from v0.7.0's former local-lab Ansible. This port removes DVD/libvirt/address assumptions and retains a single server with zero or more serially joined agents. It rejects multiple server hosts rather than pretending to implement HA.

## Operator inputs

- A reviewed inventory with `rke2_servers` and `rke2_agents`, explicit `ansible_host` and SSH user/authentication. Actual topology and SSH references are in ignored inventory/.topology.yml; public hosts.yml is an empty skeleton. Credentials and private key bytes remain excluded.
- Installed RHEL with Python/SSH/become, working OS repositories, enforcing SELinux and reviewed physical firewall/CNI/NetworkManager prerequisites. PXE/OS setup is separate; these playbooks do not wake or scan nodes.
- A unique `rke2_cluster_id`, protected `rke2_private_output_dir`, reviewed pod/service CIDRs and optional API TLS SANs. RKE2 is pinned to v1.36.5+rke2r1; the release-tagged installer is SHA256-checked. A version change needs compatibility review.
- Deliberate `physical_operator_inputs_complete`, `rke2_network_prerequisites_reviewed`, `rke2_credential_lifecycle_reviewed` and `rke2_install_apply` gates, supplied only after action-specific approval.

Syntax/default checks use no nodes:

```sh
ansible-playbook -i infrastructure/ansible/inventory/hosts.yml infrastructure/ansible/playbooks/install-rke2.yml --syntax-check
ansible-playbook -i infrastructure/ansible/inventory/hosts.yml infrastructure/ansible/playbooks/install-rke2.yml --check
```

## Existing state and recovery

Controller preflight runs before dynamic approved groups are formed; defaults/check mode gather no remote facts. The remote installer refuses unowned existing RKE2 state, a mismatched installation marker or version, and managed config drift. It never wipes data, silently adopts a cluster, upgrades an existing release or restarts it to apply changes. Interrupted unmarked installations require a separate recovery review.

Server readiness precedes token transfer and agent joining. Join credentials remain in no_log runtime variables, the protected controller input file and root-only node config; no fact cache is enabled by this code. The installation writes kubeconfig and bundled kubectl only to protected operator-selected state; it never replaces `~/.kube/config` implicitly. Existing output requires matching ownership; output directory/file modes are 0700/0600. Shared/private credential parent paths must also be protected.

The approved install would create credentials and start RKE2 services, then wait for the exact selected nodes Ready. The current physical installation has completed; see the handoff for its last verified state. Synthetic/default-gate tests and template checks do not establish physical OS/package/network compatibility, startup, HA or backup/recovery readiness.

## Dedicated agent credentials and custody gate

Supply `rke2_agent_token_file` via reviewed external vars: an absolute, nonsymlink,
operator-owned 0600 file with a single raw token of at least 32 URL-safe characters
(`A-Z`, `a-z`, `0-9`, `_`, `-`), no newline. It is a separate agent-only credential,
not a copy of the server token. The controller validates it before SSH, templates
`agent-token` into the server's root-only config, then reads `server/agent-token`
in secure format after startup. It compares that value against `server/token` and
refuses identical credentials before any agent enrollment. Only the agent token
is passed to workers. No credential default or generation is supplied.

The installation retains the server token server-side except for a no-log
comparison in runtime memory; it is never written to worker configuration. A
separately approved token-export playbook can save it in protected local custody.
It can join servers and decrypt bootstrap data, which can enable administrative
access; it is not itself a Kubernetes API bearer credential. Back it up with its
matching snapshots through a separately approved recovery process.

`rke2_credential_lifecycle_reviewed` stays false until custody and backup/restore
are reviewed. See [credential handling](../CREDENTIALS.md). No rotation is implemented;
changing the file on an existing installation triggers the config-drift refusal
and requires explicit maintenance. Server-only staging is supported with an
inventory containing only the server; retain localhost for controller preflight.

## Reviewed host preparation

`playbooks/configure-hosts.yml` is default-off and selects no remote hosts in
check mode. For the current one-server/two-worker RHEL 10 x86_64 target, it requires
explicit `physical_host_prepare_apply`, `physical_host_prepare_reviewed`, and
`physical_disable_firewalld_approved` flags before any connection. It verifies
registration, BaseOS/AppStream, enforcing SELinux, no swap, synchronized time and
absence of RKE2 before writes. It installs prerequisites without a full OS upgrade,
persists overlay/br_netfilter/nf_conntrack and forwarding/bridge sysctls, tells
NetworkManager to ignore only Canal virtual interfaces, reloads its configuration,
and stops/disables firewalld for Canal compatibility. Physical NICs remain managed.
No RKE2 service, token or kubeconfig is created by host preparation.

Use `-i infrastructure/ansible/inventory/.topology.yml` explicitly for approved
local runs; use `--ask-become-pass` so sudo credentials are entered locally.
Host preparation requires separate action-specific approval, especially the firewall
change. See https://docs.rke2.io/known_issues and https://docs.rke2.io/install/requirements.
RPM installation uses `/usr/bin/rke2`; an existing `/usr/local/bin/rke2` is refused.

## Private access and token custody

Keep a mode0700 ignored inventory/.rke2-state directory. Create a dedicated raw
agent token before installation with `umask 077`, a fresh destination (no overwrite),
and `openssl rand -hex 32 | tr -d '\n'`; it must be a mode0600 file. Author private
install.yml with cluster id, absolute credential/output paths and reviewed CIDRs.
Run install-rke2.yml with explicit private inventory/vars, --ask-become-pass and
the reviewed apply/input/network/custody flags. Never put token values on the CLI.
The server starts before workers join serially; the final task waits for all selected
node names Ready. Use the protected bundled kubectl and rke2.yaml explicitly for
status checks. The operator may separately authorize replacing the workstation's default kubeconfig; secure it with mode0600 and verify the selected cluster.

After installation, export-rke2-tokens.yml accepts the same inventory/private vars
and explicit rke2_token_export_apply=true with --ask-become-pass. Default/check mode
contacts no node. It verifies private output ownership and fresh token destinations,
then saves complete server-token.secure and agent-token.secure with no_log and
mode0600. Both workers use the same separate agent-only token. Save these in your
password manager; do not paste them into chat, commit them or discard the files
before independent custody is confirmed. Server token plus matching etcd snapshots
are required for recovery. Local token exports alone are not a tested backup plan.

## Human-run commands

Run from the repository root, after reviewing and authoring ignored .topology.yml
and .rke2-state/install.yml as described above. These are separate approved stages,
not a blanket approval to run all commands. Enter sudo passwords at the prompt.

Before RKE2 exists:

```sh
ansible-playbook -i infrastructure/ansible/inventory/.topology.yml infrastructure/ansible/playbooks/configure-hosts.yml --ask-become-pass -e physical_host_prepare_apply=true -e physical_host_prepare_reviewed=true -e physical_disable_firewalld_approved=true
```

Install the reviewed server and join the agents:

```sh
ansible-playbook -i infrastructure/ansible/inventory/.topology.yml infrastructure/ansible/playbooks/install-rke2.yml --ask-become-pass -e @infrastructure/ansible/inventory/.rke2-state/install.yml -e rke2_install_apply=true -e physical_operator_inputs_complete=true -e rke2_network_prerequisites_reviewed=true -e rke2_credential_lifecycle_reviewed=true
```

Export tokens to fresh protected destinations, only when separately requested:

```sh
ansible-playbook -i infrastructure/ansible/inventory/.topology.yml infrastructure/ansible/playbooks/export-rke2-tokens.yml --ask-become-pass -e @infrastructure/ansible/inventory/.rke2-state/install.yml -e rke2_token_export_apply=true
```

Read-only checks after installation:

```sh
infrastructure/ansible/inventory/.rke2-state/cluster/kubectl --kubeconfig infrastructure/ansible/inventory/.rke2-state/cluster/rke2.yaml get nodes
infrastructure/ansible/inventory/.rke2-state/cluster/kubectl --kubeconfig infrastructure/ansible/inventory/.rke2-state/cluster/rke2.yaml get pods -n kube-system
```

Keep install.yml, the raw agent-token, cluster/perkforge-cluster-id and the complete
token exports. The kubeconfig and bundled client can be fetched again. A credential
ZIP is unencrypted unless explicitly encrypted separately; restrict it to mode0600,
keep it ignored and transfer it only to protected storage. No archive or exported
token contains the etcd datastore unless a separate snapshot operation was performed.
