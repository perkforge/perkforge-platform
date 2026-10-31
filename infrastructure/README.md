# Physical infrastructure

Use the [human-operated RHEL procedure](../pxe/README.md) for installation and SSH.
[Current state](../HANDOFF.md) records readiness; the [C4 views](../docs/architecture/README.md)
show architecture, the local topology and operating boundaries.

[Ansible entrypoints](ansible/README.md) own explicit host/RKE2 operations; optional Rancher/Longhorn Helm deployment belongs to Big Bang/Flux.
The [public inventory skeleton](ansible/inventory/hosts.yml) contains no physical identifiers.
The ignored `ansible/inventory/.topology.yml` holds the actual IP/MAC map and SSH references. Private key bytes/passwords are not in the repository.
The ignored `ansible/inventory/known_hosts.local` retains current verified host trust;
re-establish it through a physical fingerprint check on a new workstation.

Before installing RKE2, review repositories/entitlement, SELinux, NetworkManager/CNI,
firewall/forwarding, time, swap, storage/capacity and [credential custody](CREDENTIALS.md).
Working SSH alone is insufficient. Host and cluster changes require a concrete,
reviewed action and separate operator authorization.

Rancher is platform-admin cluster lifecycle management. Flux owns GitOps; Big Bang
supplies curated platform packages. No repository maintenance command changes nodes,
workstation services or a running cluster.

[RKE2 operator procedure](ansible/RKE2.md) covers reviewed host preparation, pinned
installation, token export and private local custody. Before platform activation, verify
workload networking, off-node recovery material, reboot behavior and a persistent-
storage decision; see the current handoff for completed checks and remaining scope.

## Home-lab storage design

Growth targets are Harbor with scanned-image retention, a small portal PostgreSQL
DB, Nextcloud personal photos/files and OpenBao secrets. Selected design is
Longhorn with two replicas on different workers, no application-data replicas on
control-1, using existing filesystems initially. Keep the single control plane and
etcd capacity independent; replicated storage does not make this cluster HA.
Start with an approximate 80–100GiB total logical-volume budget, not a claimed quota
or guaranteed usable capacity; replicas double data footprint before snapshots and
other overhead. Size actual claims after measuring the existing photo/file import.
Avoid overprovisioning, retain at least 25% root-disk free space, and review capacity
around 30% free rather than waiting for disk pressure. Add larger dedicated worker
SSDs when measured growth requires them; no immediate NAS/network upgrade is chosen.
Use bounded image/snapshot retention and an independent protected backup destination
for personal files, databases and secret-service recovery, with restore checks.

Pinned Big Bang 3.35.1 has no built-in Longhorn package. Its custom-package mechanism
can declare an upstream pinned Longhorn chart, reconciled by Flux, ordered before
stateful applications. Infrastructure Ansible owns host prerequisites. Optional Longhorn 1.13.0 and Rancher 2.15.2 inputs and prerequisites are prepared
under big-bang-bootstrap/configuration/packages; both remain unselected/suspended.
Host compatibility, actual scheduling/labels and backup details still need review
before any installation. The existing static Keycloak PV remains an unconfigured
specimen until deliberately replaced; no storage implementation has been applied.
See [Big Bang storage guidance](https://docs-bigbang.dso.mil/latest/docs/community/development/bigbang-storage-options/),
[custom packages](https://docs-bigbang.dso.mil/latest/docs/installation/environments/extra-package-deployment/)
and [Longhorn recommendations](https://longhorn.io/docs/1.13.0/best-practices/).

## Local application DNS

The selected DNS owner is a host service on control-1, independent of Kubernetes.
`ansible/playbooks/configure-lab-dns.yml` installs dnsmasq/bind-utils and
starts/enables a dedicated `perkforge-lab-dns` unit after explicit approval. It is
a first-install operation: existing unit/configuration or any port53 listener
causes refusal before changes. Review partial failure and maintenance separately;
never delete existing files merely to bypass the guard.

The daemon binds only control-1's explicit LAN IPv4 address, serves the four
application names under perkforge.home.arpa and forwards ordinary queries to the
explicit gateway address. All home.arpa queries stay local. The selected initial
ingress endpoint is worker-1's existing Traefik host ports; a worker outage requires
a deliberate endpoint update. Actual IPs stay in ignored topology/private inputs.
No wildcard records, query logging, DHCP, PXE, TFTP or router advertisements are
enabled. No service is deployed in Kubernetes. SELinux remains enforcing; only the
vendor configuration file label is restored, with no custom policy installed.
The dedicated service uses one explicit configuration, ignoring vendor snippets,
/etc/hosts and resolver settings to avoid forwarding loops after client changes.

After separate approval, provide the gateway IPv4 in a protected ignored vars file
as `lab_dns_upstream`, then run from the repository root:

```sh
ansible-playbook -i infrastructure/ansible/inventory/.topology.yml \
  infrastructure/ansible/playbooks/configure-lab-dns.yml --ask-become-pass \
  -e @/ABSOLUTE/PATH/TO/private-dns-inputs.yml \
  -e lab_dns_apply=true -e lab_dns_reviewed=true
```

Defaults/check mode contact no server. The live operation verifies host identity,
RHEL/SELinux, bound address, safe first-install paths, config syntax and all four
records via UDP/TCP. Next independently verify gateway forwarding, unknown local
names, LAN reachability and listener scope. Client DNS migration is a separate
reviewed action for the workstation and three nodes, including IPv6/DHCP resolver
behavior, NetworkManager persistence, CoreDNS and host-network API-server lookups.
Client resolver settings, router DHCP, node services and workstation configuration
are unchanged by this server operation. Other household clients retain router DNS.
Host DNS survives Kubernetes downtime but still depends on control-1 and its LAN;
this does not add DNS or control-plane HA. TLS/CA preparation remains separate.

Current installation is active/enabled on control-1 with restart-on-failure.
Direct LAN UDP/TCP application records, negative/AAAA responses, forwarding and
listener scope passed verification; client resolvers are not yet migrated. Boot
unit enablement is verified, not actual reboot recovery for this new service.

### Workstation split DNS

The approved workstation setup uses its existing boot-enabled loopback dnsmasq
service. `/etc/dnsmasq.d/90-perkforge-lab.conf` routes perkforge.home.arpa to
control-1 and explicitly routes other queries to the gateway, avoiding a recursive
loop through /etc/resolv.conf. NetworkManager's reviewed wired profile uses
127.0.0.1 DNS, ignores automatic DNS for both address families and gives IPv4 DNS
priority -50. This excludes lingering gateway IPv6 DNS from the active resolver
list without disabling IPv6 networking. Libvirt's separate resolver is unchanged.

Repeat via `ansible/playbooks/configure-workstation-dns.yml`, default-off and
hostname/profile guarded. Supply protected external vars for
workstation_dns_expected_hostname, workstation_dns_profile (UUID),
workstation_dns_device, workstation_lab_dns_server, workstation_lab_ingress_ip and
workstation_dns_gateway, then run locally with --ask-become-pass and
workstation_dns_apply=true after action-specific approval. The existing dnsmasq,
NetworkManager and dig must be installed; this does not install another daemon.
The playbook refuses an existing dedicated file, captures only changed profile
properties for rollback, validates configuration and restarts only dnsmasq. It
reapplies the active device and refreshes DNS without reconnecting or restarting
NetworkManager. Verification requires only loopback in resolv.conf, all four lab
names through ordinary DNS and working public lookup. Failure restores captured
profile properties and removes the new file. First-install refusal also applies
after successful installation: review maintenance rather than rerunning blindly.

The live workstation checks passed normal DNS plus OS name resolution for all four
names and ordinary internet DNS. Configuration is persistent, but workstation
reboot recovery and browser-specific secure-DNS overrides have not been tested.
All three nodes now use control-1 directly, as described below. DNS resolution alone does not
create application routes, install the platform or issue trusted certificates.

### Node DNS and CoreDNS resolver inheritance

`ansible/playbooks/configure-node-dns.yml` migrates worker-1, worker-2, then
control-1, serially. Defaults/check mode contact no hosts. After action-specific
approval, use the private inventory, --ask-become-pass, node_dns_apply=true,
node_dns_reviewed=true and an explicit fresh mode0700 node_dns_evidence_dir.
The playbook checks the responding DNS endpoint, exact node/OS identity, one wired
default-route profile and active RKE2 before saving only original DNS properties
(mode0600) into private workstation evidence. It sets the control-1 LAN address as
the sole IPv4 resolver, ignores automatic DNS from both families and uses priority
-50 to prevent gateway bypass without disabling IPv6 networking. Device reapply
and DNS refresh do not reconnect physical networking or restart RKE2. Each node
must resolve all four application names and public DNS; failure restores that
node's DNS properties and stops the sequence. Already completed nodes remain
migrated; their saved properties support deliberate rollback if required.

The completed live migration passed all host checks and all three nodes remained
Ready. CoreDNS uses dnsPolicy Default and forwards to its pod's /etc/resolv.conf;
existing pods required a separately approved rolling refresh to acquire the
changed host resolver. Before refresh a direct service query returned no lab A
answer; after refresh all service-level DNS checks passed. New host-network
pods can inherit updated host DNS, but existing static/API pods have not been
restarted or verified; API OIDC activation remains separate.

A separately gated `ansible/playbooks/refresh-coredns.yml` checks explicit
kubeconfig/client paths and expected kube-system UID, then requires the current
healthy two-replica RollingUpdate deployment (maxUnavailable=1). After separate
approval, set coredns_refresh_apply=true with protected vars for
coredns_refresh_kubeconfig, coredns_refresh_kubectl and
coredns_refresh_expected_cluster_uid. It rolls only the existing CoreDNS deployment
and waits up to 180 seconds for completion. It does not change the chart/Corefile,
node services, application deployment or API authentication. Verify lab and public
lookups through the CoreDNS service and from workloads afterward; rollout success
alone does not prove DNS resolution. The approved refresh completed with two updated/Ready/available replicas and all
three nodes Ready.

Repeat read-only service verification with `ansible/tests/coredns-resolution.yml`,
the private physical inventory, protected coredns_refresh_* inputs and
coredns_resolution_verify=true. Default/check mode contacts no cluster/hosts.
The live verification passed eight lab A queries over UDP/TCP, Kubernetes internal
service discovery and public forwarding from control-1 through the actual CoreDNS
service address. It creates no workload and does not validate every pod/host-network
DNS policy or API OIDC. No static/API pod or RKE2 restart was performed.

## Private CA and application TLS

`ansible/playbooks/create-lab-pki.yml` performs local issuance only after
separate approval. The lab uses one RSA4096 ten-year root named PerkForge Home Lab
Root CA, encrypted with a locally entered/confirmed passphrase (minimum16 characters),
and independent RSA3072 one-year server certificates for Headlamp, Keycloak,
Rancher and OpenBao under perkforge.home.arpa. Each leaf has only its exact DNS SAN,
CA:false and serverAuth purpose; no wildcard, IP or localhost SAN is added. Root
pathlen0 prevents intermediate CA issuance. This small lab uses direct root signing;
no continuously online CA, ACME or automatic renewal service is introduced.

After explicit local credential-creation approval, run:

```sh
ansible-playbook -i localhost, infrastructure/ansible/playbooks/create-lab-pki.yml \
  -e lab_pki_apply=true \
  -e lab_pki_output_parent=/ABSOLUTE/PATH/TO/inventory/.rke2-state
```

The output parent must exist, be operator-owned mode0700, canonical and not a
symlink. Default/check mode neither prompts nor issues keys. Each run creates a
fresh private directory and never overwrites an existing key. Enter the passphrase
locally, never in chat, command arguments or tracked input files. It is passed to
OpenSSL over stdin under no_log, not saved to disk, then cleared from subsequent
task facts. Output contains encrypted root-ca.key.pem, public root-ca.crt, four
application subdirectories with tls.key/tls.crt and a fingerprint/status summary.
Leaf keys are unencrypted for server use, mode0600 inside private directories.
Temporary requests/extension copies are removed after chain/hostname/purpose checks.
Renewal, expiry monitoring and CA compromise/revocation recovery remain explicit
operator procedures to design before long-term personal-data use; rerunning the
first-issuance play creates a new CA, not a renewal under the existing trust root.

Keep the encrypted signing key offline between issuance operations, with independent
protected backup and passphrase custody. The earlier RKE2 token ZIP contains none
of these new assets. Do not distribute the signing key to nodes or Kubernetes.
Only public CA certificates and each service's own leaf/key pair belong in their
respective trust/TLS destinations. Creating certificates does not authorize trust
installation or cluster Secret writes.

| Consumer | Prepared contract / later delivery |
|---|---|
| Workstation and nodes | Public root certificate in reviewed OS/browser trust; browser-specific stores need verification |
| Headlamp ingress | headlamp/headlamp-local-tls with its leaf/key |
| Keycloak ingress | keycloak/keycloak-local-tls with its leaf/key |
| Headlamp OIDC | headlamp/identity-ca ConfigMap, ca.crt, mounted by existing values |
| RKE2 API OIDC | Public CA at /etc/rancher/rke2/identity/ca.crt; activation/restart separately approved |
| Rancher ingress/agents | cattle-system/tls-rancher-ingress leaf/key and tls-ca with cacerts.pem; staged privateCA:true |
| Rancher outbound trust | cattle-system/tls-ca-additional with ca-additional.pem; staged additionalTrustedCAs:true for Keycloak |
| OpenBao | Hostname certificate is prepared, but ingress/backend/internal TLS and delivery remain unresolved |

OpenBao's current localhost HTTPS port-forward setting is not covered by its DNS-only
certificate. Do not disable verification or assume ingress TLS also secures Raft/
internal listeners. Review its selected chart/listener configuration before delivery.
Rancher still uses strict agent TLS. No CA key is generated in a cluster Secret,
no certificate controller is installed and neither private CA flag activates Helm.
The issuance playbook installs no OS trust, files on nodes, ingress routes or Secrets.

Current issuance completed with all four hostname/chain/purpose and matching-key
checks passed. The encrypted root and leaf keys remain in protected workstation
storage; independent/offline custody is unconfirmed. OS trust installation is now complete as described below; cluster Secrets remain
absent. See the handoff for the ignored bundle location. Trust and
leaf delivery remain separately reviewed actions; the prior token ZIP is unchanged.

### Public CA trust installation

`ansible/playbooks/install-lab-ca-trust.yml` is default-off/check-mode inert. Supply
protected external vars lab_ca_public_file, lab_ca_expected_fingerprint,
lab_ca_leaf_bundle and lab_ca_expected_workstation_hostname. After action-specific
approval, use the private physical inventory, --ask-become-pass and
lab_ca_trust_apply=true with either lab_ca_trust_workstation=true or
lab_ca_trust_nodes=true. Separate invocations allow different sudo credentials.
The recorded root fingerprint and CA constraint are checked before target selection.
Only the public root and public service certificates are read for distribution/
verification; no signing or service private key is sent to a node.

The Debian workstation anchor is
/usr/local/share/ca-certificates/perkforge-home-lab-root.crt, activated with
update-ca-certificates. RHEL anchors are
/etc/pki/ca-trust/source/anchors/perkforge-home-lab-root.crt, activated with
update-ca-trust extract. RHEL's openssl CLI is installed for verification; it is
not present in the original minimal node image. Existing anchors are accepted only
when root-owned, regular and fingerprint-identical; a different CA requires rotation
review. Each target verifies all four leaves using its default OS trust bundle.
The approved run passed all16 leaf checks and matching fingerprints; nodes stayed
Ready. No services or browsers were restarted.

Firefox ESR on this Linux workstation has an explicit Certificates.Install policy
in /etc/firefox/policies/policies.json referencing the public anchor. The playbook
refuses existing policy files for merge review, preserving unrelated settings.
The policy takes effect on Firefox restart; the user closed Firefox during this
operation. Reopen it and inspect about:policies, then verify real HTTPS once leaf
certificates/routes are delivered. Policy presence alone is not live browser TLS
verification. ImportEnterpriseRoots is not used as Linux trust configuration.
See [Mozilla Certificates policy](https://firefox-admin-docs.mozilla.org/reference/policies/certificates/).

OS trust does not automatically configure containers, Headlamp's identity-ca mount,
Rancher CA Secrets or API-server OIDC's explicit CA path. Those deliveries and
OpenBao listener/TLS still require separate reviewed actions. Independent encrypted
CA backup/passphrase custody is still unconfirmed; no private key backup or token
ZIP update was performed by trust installation.
