# Physical RHEL provisioning

**Active approach: one controlled worker-1 pilot.** Reuse the proven PXE transport,
standard RHEL10 Kickstart and the short Ansible SSH/sudo handoff. A full VM rehearsal
is **not a prerequisite**. Correct bounded defects during the approved pilot;
stop for unexpected disks, credential exposure or broader network/security scope.
No live installation, service or credential action is authorized by these files.

Follow the [ordered C4 walkthrough](../docs/architecture/README.md) and
[current readiness / approval checklist](../infrastructure/TOMORROW-READINESS.md).
Worker working files belong in ignored protected `pxe/local/worker-1/`; shared
local files/tools belong in `pxe/local/`. Actual private keys/passwords stay outside
working metadata in protected custody. No directory refactor is part of this pilot.

| Existing artifact | Use now |
|---|---|
| [ansible/prepare.yml](ansible/prepare.yml) | Offline plan and BLOCKED candidate; no connection/service/disk operation |
| [kickstart/rhel10.ks.j2](kickstart/rhel10.ks.j2) | Default physical draft always aborts; final target-specific file still needs exact inputs and review |
| [kickstart/storage.ks.j2](kickstart/storage.ks.j2) | Standard exact-disk directives and read-only identity/capacity guard |
| [kickstart/bootstrap-post.ks.j2](kickstart/bootstrap-post.ks.j2) | Initial key-only SSH/root-sudo policy; no password/hash/private key in HTTP |
| [bootstrap/handoff.yml](bootstrap/handoff.yml) | Default-off workstation access caller; trusted host key and private password checkpoint |
| [pilot/](pilot/HANDOFF.md) | Proven boot/source templates and existing activation/shutdown evidence; retarget and review exact worker config before launch |

From this worktree, offline preparation only:

```sh
ansible-playbook -i localhost, -c local pxe/ansible/prepare.yml -e @pxe/local/worker-1/inputs.yml
```

Existing output is preserved; choose a fresh run path in inputs before rerendering.
The default candidate never becomes deployable merely by filling metadata. Finish
its exact disk/layout/identity inputs, validate the actual proposed Kickstart with
RHEL10 ksvalidator, then review one concrete install/service/access batch.

## Red Hat solution and nginx

Red Hat documents DHCP plus PXE/TFTP (or UEFI HTTP when supported), with an HTTP(S)
installation/Kickstart source. Nginx is suitable for the static source. Our router
continues allocating addresses; the reviewed dnsmasq supplies proxy boot metadata.
The physical pilot proved the TFTP path; do not switch protocols, disable Secure
Boot or change household DHCP. [Vendor guidance](../infrastructure/RHEL-PROVISIONING-GUIDANCE.md).

## Scope and retained work

Keep control-1's working OS/access, worker-2, existing workstation services and
historical trial untouched. Only worker-1 may be armed after its exact disk and
scope approval. Firmware/router acceptance and real Kickstart/PAM/package behavior
remain untested for that worker; disclose that pilot risk rather than claim a
rehearsal passed. RKE2/Rancher/Flux are separate later work.

The unfinished custom namespace/QEMU runner and its recovery framework are parked,
not operating instructions or worker gates. Their code/tests/evidence are preserved;
never run `pilot/history/rehearsal/runner.yml` as part of this pilot. Proven packet and access
fixtures remain useful without rebuilding a general provisioning system.

Active bounded checks:

```sh
python3 -m unittest discover -s pxe/tests -p 'test_prepare.py'
python3 -m unittest discover -s pxe/bootstrap/tests -p 'test_*.py'
python3 -m unittest discover -s pxe/pilot/tests -p 'test_kickstart_candidate.py'
```

Private metadata, media, held evidence and the existing pilot shutdown path are
preserved. No broad cleanup, source moves, credential migration or publishing.
