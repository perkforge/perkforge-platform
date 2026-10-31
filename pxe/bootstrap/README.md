# Temporary key-only bootstrap design

Approved for offline implementation/rehearsal planning only. No credentials,
privileges, physical installation or rehearsal execution are approved here.
`credential_mode: TEMPORARY_KEY_ONLY_BOOTSTRAP` records this decision in the blocked
plan; it does not remove the unconditional Kickstart abort or install anything.

## Proposed implementation contract

1. Dedicated bootstrap account/public key, separate from the human administrator.
   Only the public key enters Kickstart (`sshkey`); private key remains in protected
   credential storage. Never put human password/hash in served files. Do not start
   installer SSH (`inst.sshd`). Locked-account/PAM key login remains untested on
   RHEL10.2; `user --lock` alone is not proof of usable key authentication.
2. Before installed sshd starts: root-owned key-only SSH configuration, effective
   `sshd -t`/`sshd -T` validation, SELinux labels, and root-owned0440 sudoers entry
   validated by `visudo -cf`. Intended entry: `BOOTSTRAP ALL=(root) NOPASSWD: ALL`.
   This is explicitly **root-equivalent** temporary access, not least privilege.
   BOOTSTRAP is a placeholder, not a runnable sudoers file.
3. Workstation verifies host identity through trusted physical/console evidence,
   then uses bootstrap SSH to create the human account/key. Supply its password
   privately through encrypted SSH/stdin with no logs/argument values; the
   controller caller now has mocked tests, while native behavior remains unproven. Keep password-sudo and disable password SSH.
4. Verify a *fresh* human key login and password-authenticated sudo independently.
   Only then remove bootstrap authorized key and sudoers entry, disable account,
   and prove bootstrap key/sudo rejected while human access remains valid.
5. Lifetime is one provisioning handoff, not indefinite operation. No automatic
   expiry exists yet. Failed/interrupted runs must report account/key/sudo grant
   status as outstanding or unknown until verified revoked. Preserve evidence;
   resume through verified human access or physical console. Do not blindly remove
   the last working access path. Lost bootstrap private key requires approved
   console recovery, not enabling password SSH by default.

## Implemented Ansible components

This directory is a standard Ansible role with `defaults/main.yml`, `tasks/` and
`templates/`; no Python configuration generator or daemon. Default apply gate is
false. [handoff.yml](handoff.yml) is the default-off installed-host access caller; the
blocked candidate renders the initial Kickstart adapter separately. There is no
install/session/rehearsal runner. The physical Kickstart
unconditional abort remains unchanged. These are code components, not a runnable
installer or permission to target an existing host.

| Order / source | Executes where | Actual behavior |
|---|---|---|
| [main.yml](tasks/main.yml) | target | Gate action; protected root-owned0700 ledger directory/0600 state. Record intent before account/grant operations. Failure stays outstanding/unknown; reject existing setup ledger. |
| [setup.yml](tasks/setup.yml) | installed target, before SSH exposure | Require stopped exact sshd.service/socket and disabled/masked/absent exact socket. Refuse existing account/home/policy. Create locked account/public key, root-owned key-only SSH and validated0440 root-equivalent sudo policy; validate public-key structure with ssh-keygen, restore labels, check sshd syntax/effective policy for account and root connection contexts. Never start/reload services. |
| [handoff.yml](tasks/handoff.yml) | target through bootstrap admin channel | Refuse existing human account; add separate human public key and wheel/password-sudo identity. Password is hidden runtime input; target chpasswd receives it via encrypted SSH stdin/no_log using target PAM policy, never Kickstart/HTTP. Preserve bootstrap authorization. |
| [verify-human.yml](tasks/verify-human.yml) | controller (`delegate_to: localhost`) | Fresh nonmultiplexed key-only SSH with strict preverified known-host file and40second command bound. Clear sudo timestamp, reject passwordless sudo, then verify password-sudo using stdin/no_log. |
| [revoke.yml](tasks/revoke.yml) | target through verified human SSH/become | Require fresh human proof first. Remove only matching original key/sudo file; lock/expire account, set nologin, terminate its account-owned processes with bounded residual check. Fresh bootstrap authentication must be rejected explicitly, then human key/password-sudo must still work. Only then mark revoked. |

The revoke caller must switch Ansible to the **human** identity and password-become
before removing bootstrap sudo; reusing the bootstrap management connection would
break mid-operation. Main task variables are prefixed `bootstrap_`; defaults list
nonsecret paths/identities. Human password/hash values are absent from saved schemas. The caller prompts
privately at the controller for an existing approved password from protected
custody, then sends it to target chpasswd over SSH stdin with no_log; it neither
creates a password/hash on the controller nor writes one to metadata. Target PAM
sets the hash, without overriding its algorithm. Do not pass secrets using `-e`,
shell arguments, local plan files or the viewer.

## Evidence / failure contract

Run only offline fixtures from the worktree:

```sh
python3 -m unittest discover -s pxe/bootstrap/tests -p 'test_*.py'
```

Fixtures execute real Ansible task flow, templates, file writes, validations and
rescue paths inside fresh temporary directories. Account/getent effects are
replaced by fixture files/facts. systemctl/sshd/visudo/restorecon/SSH/process tools
are mock executables. Synthetic keys/hash/password are intentionally unusable.
Positive setup/handoff/revoke, invalid policy/sudoers, active/enabled SSH, existing
account, human-login/passwordless failure, modified grant, timeout, residual
process, controller interruption and failed final human verification are covered.
These prove task flow, **not real account/PAM/SELinux/SSH/sudo correctness**.

Intent is recorded before privilege changes. A controller kill/unreachable target
can leave `in_progress` with `outstanding_or_unknown`; rescue cannot be guaranteed
to run. Rescue failures also require inspecting retained state, never assuming
revocation. Automatic retry is intentionally absent: partial accounts/files need
reviewed reconciliation, not overwrite. The ledger is current local state, not a
full immutable audit log; the install/session runner still needs retained per-run evidence.

New SSH authentication, authorization and account-owned process checks do not
prove arbitrary root processes previously launched by a trusted bootstrap identity
are gone. Root-equivalent access cannot be retroactively sandboxed; suspected
compromise requires rebuild/recovery, not a claim of complete revocation. Secrets
necessarily enter trusted controller/host process memory; no_log is output
suppression, not a zero-exposure guarantee.

## Initial Kickstart adapter now implemented offline

[bootstrap-post.ks.j2](../kickstart/bootstrap-post.ks.j2) is the vendor-native
`%post --erroronfail` installed-root adapter, rendered by Ansible from the SAME
SSH/sudo templates. It checks the account/key created by standard `user`/`sshkey`,
records intent, writes policy/permissions, validates public key/sudo/SSH, restores
labels and enables SSH **offline for first disk boot only** as the final success
step. It never runs Ansible/systemd-manager commands in the chroot. `--root=/`
unit enable/disable/mask operations edit installed unit links, not running services.

Kickstart defaults sshd disabled. The adapter masks the exact sshd.socket,
validates SSH for bootstrap/root numeric source-address contexts with UseDNS no,
and invokes standard `ssh-keygen -A` on the NEW target to allow complete sshd
validation before first exposure. No host keys are generated during preparation;
that command is mocked in tests and real execution requires install approval.
Failure attempts offline disable, preserves an outstanding/unknown ledger and
halts Anaconda. Failed disable/ledger writes are not silently treated as recovery
success; retain installer/console and inspect before reboot. Existing ledger is
never overwritten by initial adapter preconditions.

The candidate remains physically unarmed: an unconditional earlier `%pre exit1`
prevents this adapter or any storage directive from executing. Missing bootstrap
identity/public key/source context also renders an inert failing adapter. There
is no production install/apply switch. `setup.yml` remains the standalone target
component/reference fixture; the normal initial install uses `%post`, **not**
Ansible inside the installer. Handoff/revocation use installed-host Ansible later.

The [storage adapter](../kickstart/storage.ks.j2) now has standard single-disk
ignoredisk/clearpart/part/LVM directives and a read-only pre-check for exact
persistent ID, serial and byte capacity. It renders no storage directives while
identity/layout is unresolved. Physical disk identification/erasure approval is
still missing; fixture metadata is not a substitute.

## Installed-host caller and remaining gates

[handoff.yml](handoff.yml) and [nonsecret access references](access.example.yml)
now implement the controller-to-bootstrap-to-human connection sequence. Default
apply false fails before public-key lookup, password prompt or any node contact.
Only explicit reviewed execution may use it, after initial policy/host boot and
independent host-key trust. Private-key paths are references, never read/copied by
preparation; runtime OpenSSH uses those identities (encrypted keys need an approved
loaded agent). Strict known-host verification, no config-file/multiplex reuse and
public-key-only SSH are explicit. Separate inventory aliases force the management
identity switch before revocation. Existing human accounts/partial state require
reviewed recovery rather than blind overwrite/retry.

The caller has a complete mocked positive fixture from the actual initial post
adapter through human handoff/revocation, plus default-off and password-failure
checks. Target connections, account operations, password update, host keys and
policy tools remain mocked: no native RHEL security or network behavior proven.

Remaining before the controlled worker pilot:

- Complete exact worker disk/layout/account/public-key inputs, final target-specific
  file/parser/script checks and reviewed worker-only service/access batch.
- Keep one workstation checkpoint: trusted physical host fingerprint and private
  human password entry into the short caller. No automated secret provider or
  serial-trust machinery is required for this pilot.
- Native RHEL10.2 PAM/SSH/sudo/package behavior is untested. User selected a
  controlled physical pilot, accepting possible reinstall rather than making full
  VM rehearsal mandatory. Stop for consequential surprises, preserve recovery.
- Actual key generation, node/service/security/disk actions still require explicit
  scope approval. Nothing live follows from design agreement.

The custom VM/session runner is deferred, with code/evidence retained in pilot
history. Do not require it or its test-password-file path for normal worker access.

## Vendor basis

[RHEL10 post-install script semantics](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/kickstart-script-file-format-reference)
places post scripts in the installed chroot before reboot; erroronfail halts on
failure. This is why the adapter performs installed-file work, not service-manager
queries. [systemctl --root](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html#--root=)
uses direct filesystem operations for unit enable/disable. [OpenSSH UseDNS](https://man.openbsd.org/sshd_config#UseDNS)
allows the deterministic numeric source context used by the effective-policy checks.

[Red Hat RHEL10 sudo access](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/security_hardening/managing-sudo-access)
uses separate sudoers.d policy and visudo validation. The broad temporary rule
here is explicitly a provisioning tradeoff, not a least-privilege example.
[Red Hat SELinux home labeling](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/using_selinux/managing-confined-and-unconfined-users)
uses restorecon after home setup.
[Shadow-utils chpasswd](https://man7.org/linux/man-pages/man8/chpasswd.8.html)
accepts username/password on stdin and uses PAM by default; the caller does not
select an ad hoc controller hash algorithm.
[RHEL10 Kickstart reference](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/kickstart-commands-and-options-reference)
provides sshkey/user and script stages; it does not prove this handoff works.
[Ansible user module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/user_module.html)
distinguishes password locking from account disabling; expiry/key removal are also
required here. [OpenSSH client options](https://man.openbsd.org/ssh_config)
provide strict host checking, identity selection and disabled connection reuse.

See the [current pilot checklist](../../infrastructure/TOMORROW-READINESS.md).
[Earlier rehearsal proposal](REHEARSAL.md) is deferred optional history, not a gate.

## Documentation after proof

Planning/code-status distinctions remain useful during review. After successful
rehearsal and installation, replace this working proposal with a concise tested
runbook and matching current-state C4; retire superseded planning then. Keep useful
execution evidence separately. No planning/evidence is deleted at this checkpoint.
