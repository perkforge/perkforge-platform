# Operator-invoked PXE and SSH tools

Follow the single [physical installation runbook](../README.md).

- `workspace.yml` and its input schema/templates prepare a fresh private run offline.
- `prepare.yml` validates/renders only proxy/TFTP/HTTP/guard review files.
- `activate.yml`, placement/copy checks and `shutdown.yml` own dedicated serving
  resources with exact identity checks and explicit action gates.
- `preserve-session.yml` preserves only an identified stopped transaction; no reset.
- `stage-media.sh` and `install-nginx.yml` are separately approved workstation setup.
- `access.sh` and `harden-ssh.sh` perform the explicitly approved installed-host
  key-only/password-sudo handoff using standard SSH and the existing key.
- `../tests/` contains focused offline checks for these retained implementations.

All host/disk/credential actions remain operator decisions. No unattended installer,
bootstrap account, VM rehearsal, historical runner or AI-generated per-node launcher
is part of this process. Existing compatibility resource names under /srv, /run and
/var/log are unchanged by source cleanup; do not rename or delete native state as
part of repository maintenance.
