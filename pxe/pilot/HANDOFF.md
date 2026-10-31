# Resume before the first physical boot

Corrected pilot activation succeeded and both dedicated units were active at the
operator's23:55UTC check. The operator paused before network boot and reported
"Stopped" at23:58:38 after the shutdown instruction. **Shutdown recap and explicit
guard/listener verification remain pending**; do not equate that word with complete
cleanup. First read the latest journal entry and native current status.

## Completed

- Verified RHEL10.2 x86_64 DVD, root-owned read-only full tree and TFTP boot assets.
- Secure Boot/UEFIOnly/IPv4 PXE enabled per console report; no settings changed.
- GRUB signature verified against CA8 embedded in ISO shim; firmware trust pending.
- Native namespace fixture: four PASS phases and namespaces ABSENT.
- First activation PID-check failure diagnosed/reproduced; bounded rollback checked.
- Original state/logs preserved in held20261030-2337 roots. PID fix validates numeric
  tokens and preserves exclusion/identity comparison. Safe-menu retry mode tested.
- Corrected live workstation retry succeeded; default nginx masked/inactive and
  original system/libvirt dnsmasq identities preserved at activation checks.
- No physical PXE boot, installer/kernel acceptance, disk write, node SSH/RKE2 action.

## Return checklist — no blind activation

1. Current native read-only status for dedicated pilot units, reserved listeners
   and table names. If shutdown succeeded, confirm units inactive/MainPID0,
   no69/4011/8080/20000–20009 listeners and no inet perkforge_pxe_pilot.
   Existing system/libvirt DNS/DHCP is expected to remain.
2. Shutdown retains /run/perkforge-pxe-pilot and /var/log/perkforge-pxe-pilot.
   Do not run activate/retry yet: both deliberately refuse those roots.
   Inspect this successful attempt's protected record/menu hashes and choose
   **new absent held names**; never reuse/overwrite held20261030-2337.
   Any further quarantine/reset requires exact approval; preserve all evidence.
3. Review ignored private inputs and ephemeral review-source existence/checksums.
   If /tmp sources are gone or code/inputs changed, render new review files and
   refresh reviewed snapshots offline before approval. No secret reads are needed.
4. After approved reset and its verification, reviewed short command shape:
   `bash "$REPO_ROOT/pxe/pilot/pilot.sh" retry`. Same30minute service limit, guard
   before LAN bind/listen, no default-service restart or node boot. Confirm current
   active units/timer and read-only readiness; do not extend timers automatically.
5. **Separate first-boot approval:** only control-1, one-time F12 UEFI wired IPv4
   entry, Secure Boot stays ON. Stop at the indefinite GRUB menu; do not choose the
   installer. Record actual option93/request/firmware result or exact error.
   Workers remain excluded. No boot-order/security workaround without review.
6. Use the reviewed shutdown command and confirm pilot resources gone before
   leaving. Preserve logs and safe menu. A timer expiring is not complete cleanup.

Commands above are shapes using REPO_ROOT; the parent supplies complete native
paths after the relevant approval. Do not source scripts or paste historical
staging heredocs. Never rerun ISO staging or nginx installation to check readiness.

Detailed execution/provenance: [journal](../../infrastructure/EXECUTION-JOURNAL.md).
Activation/reset/rollback details: [contract](ACTIVATION-PROPOSAL.md).

## Branch verification at pause

Offline checks passed:25 PXE tests,18 infrastructure tests,8 evidence tests;
nine Ansible entrypoint syntax checks; both shell entrypoints bash-n; packet
verifier compilation; local documentation links; diff and private-identifier scan.
Tests used synthetic fixtures/temporary mocks, not a native network rerun.
Native operator results are separately attributed in the execution journal.
Ignored inputs, keys, raw logs and held runtime/log evidence are excluded from Git.
