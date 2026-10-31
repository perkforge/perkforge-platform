# Historical interactive PXE pilot and recovery

New provisioning starts with [offline Ansible preparation](../ansible/README.md).
This folder is retained for pilot evidence and compatible recovery/shutdown, not
as the normal worker or control-node reinstall workflow. Do not copy its manual
GUI/HTTP enrollment sequence into the replacement.

Start with [the current handoff](HANDOFF.md). Media staging, isolated packet tests
and corrected workstation activation have user-supplied success evidence.
The pilot has since completed physical boot, RHEL installation and key-only SSH/
sudo verification; shutdown was reported successful. See the handoff for limits.
Before workers, use the [redesign proposal](../../infrastructure/PROVISIONING-REDESIGN.md);
it is not implemented by these interactive pilot files.
Source preparation/tests do not grant permission to run native entrypoints.

## Files and execution boundaries

| File | Purpose / authorization |
|---|---|
| inputs.example.yml, prepare.yml | Local-only Ansible validation/rendering; new private /tmp review output; no service/package/network tasks |
| templates/ | Actual shared dnsmasq/nginx/GRUB/nft configuration, used by fixture and pilot |
| stage-media.sh | Reviewed non-mount staging; operator completed it; refuse rerun over populated roots |
| install-nginx.yml | Exact pinned install with temporary start denial/default mask; operator completed it; do not rerun as a status check |
| packet-fixture.yml + task helpers | Separately approved namespace/service/packet fixture; default execution flagfalse |
| probe_packets.py | Standard-library protocol verification, not configuration generation; namespace guard before sockets |
| activate.yml + placement/hash helpers | Approved workstation placement/guard/listen/services; default approvalfalse |
| shutdown.yml + tasks | Verify transaction/unit/guard identities before stopping/removing only this pilot |
| pilot.sh | Short Ansible dispatch: activate, explicit retry, rearm, shutdown; never source |
| tests/ | Offline rendering, protocol codecs, gates and temporary command mocks; no native fixture/activation |
| EXECUTION-JOURNAL.md | The actual journal is [under infrastructure](../../infrastructure/EXECUTION-JOURNAL.md); no raw private evidence in Git |

Read the [staging reference](STAGING-PROPOSAL.md), [packet test contract](PACKET-VALIDATION-PROPOSAL.md)
and [activation/shutdown contract](ACTIVATION-PROPOSAL.md) before native commands.
No automatic service includes, enablement or activation occur when files are edited.

## Safe offline checks

From repository root, with existing Python/PyYAML/Ansible only:

```sh
python3 -m unittest discover -s pxe/pilot/tests -v
ANSIBLE_LOCAL_TEMP=/tmp/perkforge-pxe-syntax ansible-playbook -i localhost, pxe/pilot/prepare.yml --syntax-check
ANSIBLE_LOCAL_TEMP=/tmp/perkforge-pxe-syntax ansible-playbook -i localhost, pxe/pilot/activate.yml --syntax-check
ANSIBLE_LOCAL_TEMP=/tmp/perkforge-pxe-syntax ansible-playbook -i localhost, pxe/pilot/shutdown.yml --syntax-check
bash -n pxe/pilot/stage-media.sh pxe/pilot/pilot.sh
```

Defaults fail closed. Real operator network inputs and SHA256 review snapshots are
ignored0600 files, not committed. Renderer creates only a new mode0700 /tmp review
directory/files0600 and refuses existing output. It never writes live roots.

## Reviewed source candidates versus runtime evidence

The documented RHEL10 candidates are architecture7, EFI/BOOT/BOOTX64.EFI and
EFI/BOOT/grub.cfg, with DVD kernel/initrd and linuxefi/initrdefi. Installed
dnsmasq2.91 docs and [version-tagged source](https://raw.githubusercontent.com/imp/dnsmasq/v2.91/src/option.c)
map7=x86-64_EFI and9=BC_EFI; pilot chooses7 only. Do not advertise every architecture
or treat the boot-item handler as an authentication boundary.

pxe_media_layout_reviewed and pxe_boot_candidates_reviewed attest source review,
not successful firmware boot. Rendered candidate manifests record preparation-time pending fields; they are not
updated runtime attestations. Actual boot/installer observations are in the journal;
db/dbx/SBAT inspection and full attestation remain unproven. ISO identity and
GRUB CA8 signature verification do not prove target firmware trust. Do not disable
Secure Boot or enroll keys to work around a failed first boot.

## Paths, service scope and permissions

Dedicated /srv/perkforge-pxe-pilot/{tftp,http} contain nonsecret media only.
Root0555 directories/root0444 files keep services read-only. tftp-secure is omitted
under explicit root-readonly policy: that option instead requires service ownership,
whose owner could chmod files. No symlinks, shared service group or media chown.

Runtime/log parents are root0711, config/session childroot0700/files0600, with
separate service0700 state/log/temp children. This gives required traversal without
exposing protected configs. Explicit dnsmasq lease and nginx lock paths prevent
default host-state use. Service PID files are not trusted shutdown identity;
recorded systemd InvocationID/ExecStart/MainPID and root-owned records are.

| Traffic | Restriction |
|---|---|
| UDP67/client68 | IPv4 proxy only, selected wired interface/pilot MAC; pre-address source0.0.0.0 allowed; router allocates |
| UDP4011 | Pilot boot-server requests, independent interface/IP/MAC guards |
| UDP69,20000–20009 | Dedicated TFTP root and transfer ingress guards |
| TCP8080 | Wired IPv4 bind, nft interface/IP/MAC guards, nginx pilot-IP allowlist, GET/HEAD only |

Only inet perkforge_pxe_pilot input table is added; priority-10/defaultaccept.
It filters reserved pilot ports/selected-interface DHCP, not general host traffic,
NAT or forwarding. It does not override other-chain drops. System/libvirt remain
untouched; MAC/IP checks are spoofable. LAN/config/HTTP trust is still a limitation.

## Validation evidence and limits

Operator isolated fixture phases daemon, guarded, wrong-interface, final-controls
all PASS; namespace cleanup ABSENT. It exercises current shared templates, server
observations for DHCP/PXE negatives and positive controls around denials.
It does not emulate complete firmware, real router or Secure Boot.

Operator native nginx/nft checks and corrected bounded activation succeeded.
An earlier activation failed due to over-escaped PID extraction; rollback was
confirmed, evidence preserved via approved quarantine, numeric-token fix tested,
and retry succeeded. The journal preserves all failures and provenance.

Nginx-t is **not** a pure read-only parser: it creates files and can briefly
bind/listen before exiting. Native checks/activation need their explicit scope.
Nft-c checks without applying; never omit -c outside approved apply steps.
Future worker boots/reinstalls and host/platform changes remain separate approvals.

## Pause and resume

Use [HANDOFF.md](HANDOFF.md). Shutdown retains runtime/log records and the safe
indefinite menu; timer expiry alone leaves guard rules. Do not restore the stock
timeout menu. Fresh activation/retry refuses retained roots intentionally.
Never overwrite the first held attempt; choose new absent hold names only after
inspection and explicit approval, or review another precise recovery plan.
