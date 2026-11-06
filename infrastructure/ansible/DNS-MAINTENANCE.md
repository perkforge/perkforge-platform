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
`gitlab-dns-records-v1` or `nextcloud-dns-record-v1`, `lab_dns_maintenance_expected_sha256` and the absolute
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
