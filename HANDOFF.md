# Current operator handoff

Use this existing `docs/physical-execution-journal` feature worktree. Publish only
to `origin` when explicitly asked; never push main or merge.

## Physical state

- control-1, worker-1 and worker-2 have RHEL 10.2 and verified key-only SSH as corey.
  Named administrator uses password-authenticated sudo; root/password/keyboard-
  interactive SSH are disabled by the verified policy.
- Each has 600 MiB EFI, 2 GiB XFS /boot and remaining XFS root on LVM; no active swap.
- Worker-1's no-OS/PXE loop resolved after Automatic Boot Sequence was made
  disk-first as well as Primary. Ethernet-connected boot and fresh SSH succeeded.
  Verify other boot paths if needed; do not assume every node's firmware was retested.
- Workstation dedicated PXE services/listeners/guard are stopped. Verified media
  remains under `/srv/perkforge-pxe-pilot`; retained native records remain under
  `/run/perkforge-pxe-pilot` and `/var/log/perkforge-pxe-pilot`. Repository cleanup
  does not authorize changing those resources or any node.
- Current addresses/MACs are in the [inventory](infrastructure/ansible/inventory/hosts.yml)
  and [C4 topology](docs/architecture/README.md). Current host trust is retained in
  ignored `infrastructure/ansible/inventory/known_hosts.local`; actual private key
  remains in the workstation SSH store, outside this working tree.

## Maintained workflow

[pxe/README.md](pxe/README.md) is the human-run physical installation/access runbook.
`pxe/transport` contains operator-invoked serving/access tools; `pxe/tests` retains
focused checks for that code. C4 contains architecture, repeat steps and topology,
not session journals or planning archives. Unattended bootstrap/Kickstart and VM
rehearsal code are not part of the process.

Current maintenance scope removes obsolete source/planning, `.secrets` and generated
`pxe/local` after retaining necessary current inventory/trust. It does not delete
workstation SSH keys, verified ISO/media or native runtime state, create archives,
perform live provisioning, or commit/push automatically.
