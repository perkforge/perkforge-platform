# Existing lab DNS: fixed app record scopes

`playbooks/maintain-lab-dns.yml` is a separate default-off maintenance operation;
never rerun the first-install DNS playbook against an existing service. This
operation adds only `gitlab.perkforge.home.arpa` and
`gitlab-objects.perkforge.home.arpa` at the reviewed ingress address. It preserves
the existing four records, other configuration bytes, upstream, listening
address, service unit, firewall, DHCP/PXE/TFTP/RA state and CA trust.

The same transaction also supports the fixed `nextcloud-dns-record-v1` scope.
It adds only `nextcloud.perkforge.home.arpa` at the reviewed worker-1 ingress
address, requires all six existing records above to remain present, and uses a
separate owned `Nextcloud DNS v1` block. It accepts no caller-supplied record
names or addresses beyond the existing reviewed inventory. GitLab's scope and
appended bytes are unchanged. Select exactly one scope per run; record a fresh
base checksum after any preceding maintenance operation.

Before a live run, obtain explicit owner approval for the selected fixed records and
one DNS-service restart (a brief DNS interruption is possible). Use a clean
checkout of a reviewed published release, matching release evidence, the existing
ignored physical inventory and verified SSH host keys/agent. Inspect the current
root-owned service unit and configuration read-only, and record the SHA256 of
`/etc/dnsmasq.d/perkforge-lab.conf` as the approved base. Do not guess a hash or
reuse one after an unexplained edit. The existing installed unit must match the
reviewed source exactly; foreign files, permissions, records or a busy lock stop.
The loaded unit must use that exact fragment, have no drop-ins and require no
daemon reload; this operation never adopts overrides or reloads changed units.

The owner-local invocation is:

```sh
ansible-playbook -i "$physical_inventory" \
  infrastructure/ansible/playbooks/maintain-lab-dns.yml \
  --ask-become-pass -e @"$reviewed_dns_inputs"
```

The private input file contains `lab_dns_maintenance_apply: true`, scope
`gitlab-dns-records-v1`, `nextcloud-dns-record-v1`, `grafana-dns-record-v1` or
`harbor-dns-record-v1` or `portal-dns-record-v1` or `ntfy-dns-record-v1`, `lab_dns_maintenance_expected_sha256` and the absolute
`lab_dns_maintenance_release_evidence` path. Release evidence identifies the
repository, stable tag and resolved commit. The checked-out commit must match,
and the tree must be clean. No password belongs in that file or chat: enter sudo
only at the local Ansible prompt. Do not configure passwordless sudo or weaken
SSH verification. Default and check modes make no host connections.

Maintenance validates current UDP/TCP records and service health before writes,
keeps an exact root0600 base backup under root0700
`/var/backups/perkforge-lab-dns`, uses a fail-closed cooperative lock, rechecks the
configuration checksum, and validates the candidate with `dnsmasq --test` before
atomic replacement. It restores the vendor SELinux context and restarts only
`perkforge-lab-dns`. Success requires all selected existing and added A records over UDP/TCP and external
resolution. A repeat using the same reviewed base hash makes zero remote
configuration/service changes and does not restart the service; the exact owned
appended block is recognized. Localhost may report the in-memory inventory
addition from `add_host`; that does not edit a host or its configuration.

If validation fails before a write, preserve the current config/service. If a
changed candidate fails service or answer checks, restore the exact base only
while the current file still matches this operation's known bytes, then verify
the original records and report failure. A concurrent edit, symlink, service
failure after restoration or incomplete cleanup must stop for owner inspection;
never overwrite foreign state or blindly retry. Backups are not automatically
pruned. After success also verify new names from an actual pod and workstation;
fake-command tests are not live DNS evidence.

This maintenance does not activate an ingress or application. CoreDNS forwarding
already resolved existing lab/public names during preflight; do not change it
without separate evidence and approval. Keep the data and app source selections
as independently approved steps after DNS and certificate verification.

Grafana uses the separate fixed `grafana-dns-record-v1` scope: only
`grafana.perkforge.home.arpa` at that same reviewed worker-1 ingress address.
It requires the existing seven records, including Nextcloud, preserves their
bytes and uses its own `Grafana DNS v1` block. The same checksum, release,
restart, rollback and explicit approval boundaries apply. This does not activate
Grafana routing. See the [Grafana UI procedure](../../big-bang-bootstrap/configuration/observability/grafana-ui/README.md)
for dedicated leaf issuance, Secret delivery, access and route approvals.

Harbor uses the separate fixed `harbor-dns-record-v1` scope: only
`harbor.perkforge.home.arpa` at that same reviewed worker-1 ingress address from
the private inventory. It requires all eight prior names: Headlamp, Keycloak,
Rancher, OpenBao, GitLab, GitLab Objects, Nextcloud and Grafana. Their bytes are
preserved; the only addition is the owned `Harbor DNS v1` block. An existing
foreign Harbor record is refused, even at the expected address. No caller-selected
record names, new listener, upstream, unit, firewall or client-resolver changes
are included. The clean release, approved base checksum, backup, single restart,
UDP/TCP verification and own-bytes-only rollback guards above also apply.

Keep Harbor DNS in the [combined Harbor review](../../big-bang-bootstrap/configuration/packages/harbor/README.md),
but obtain separate network-change approval before running this scope. Enter sudo
only at the operator's hidden Ansible prompt. DNS success does not prove Harbor
startup, HTTPS/core health, SSO or image push/pull acceptance; verify those
separately after the application is healthy.

Portal uses the separate fixed `portal-dns-record-v1` scope: only
`portal.perkforge.home.arpa` at worker-1's ingress address from the protected
inventory. It requires all nine preceding records: Headlamp, Keycloak, Rancher,
OpenBao, GitLab, GitLab Objects, Nextcloud, Grafana and Harbor. Their exact bytes,
including predecessor blocks and unrelated comments, are preserved; only the
owned `Portal DNS v1` block is appended. The same release/checksum/unit/backup,
UDP/TCP, single-successful-restart and own-bytes rollback controls apply.

**The DNS restart affects a shared service, including Nextcloud resolution.**
Do not run this maintenance during the active Toshiba-to-Nextcloud transfer
without a separately approved safe window, even though the record is Portal-only.
A failed changed candidate can require an additional rollback restart. No DNS,
certificate, credential, ingress or application activation is authorized by this
source candidate. See [Portal physical release gates](../../big-bang-bootstrap/enrollments/PORTAL-PHYSICAL.md).

Offline regression checks (fake executables and temporary local files, no live DNS):

```sh
python3 -m unittest discover -s infrastructure/ansible/tests -p 'test_*dns*.py' -v
ansible-playbook -i infrastructure/ansible/inventory/hosts.yml \
  infrastructure/ansible/playbooks/maintain-lab-dns.yml --syntax-check
```

ntfy uses the fixed `ntfy-dns-record-v1` scope, adding only
`ntfy.perkforge.home.arpa` at the existing reviewed ingress address. All nine prior
records through Harbor and all predecessor bytes are required and preserved.
Portal is an independent rollout: if present its bytes are preserved, but its
record and resolution are not required or queried by the ntfy scope.
Only the owned `Ntfy DNS v1` block is appended. The same release, fresh base hash,
backup, repeat/no-restart, UDP/TCP verification and guarded rollback apply.
Explicit approval covers the shared DNS restart; a failed changed candidate can
also require a rollback restart. This source does not activate ntfy or authorize
an unreviewed live run.

## Explicit fix-forward maintenance

The default `lab_dns_maintenance_failure_strategy: restore` retains the existing
bounded automatic restore behavior. When the operator has explicitly chosen to
repair forward, set `lab_dns_maintenance_failure_strategy: fix-forward` in the
reviewed maintenance inputs. All scope, release, checksum, lock, validation and
backup gates remain required. A failed write/restart/answer check exits failed
without restoring bytes or attempting another restart; the lock is released and
the private checksum-named backup remains available for diagnosis. This can leave
DNS unavailable, so inspect the original error and repair forward promptly. Do
not treat a failed run as success or blindly retry a restart failure: an unchanged
candidate does not restart the service on repeat. Diagnose service state first,
then review a fresh checksum before another maintenance run. No setting here
authorizes unrelated host changes or silently changes other operators' defaults.
