# Key-only policy after a verified key login

For the fatigued-console workflow, prefer the equivalent standalone
`harden-ssh.sh`: transfer it with scp over the already verified SSH connection,
then run `sudo bash harden-ssh.sh <OPERATOR_LOGIN> <WORKSTATION_IPV4>` in the
retained session. No HTTP download or manual checksum transcription is needed.
Do not execute until the independent key-only login succeeds. The block below
is the reviewable policy reference, not an instruction to hand-type it.

Use only after the operator verifies a separate public-key-only login. Keep the
existing SSH session and console open. This is a contained subprocess: its
strict shell options cannot exit the caller's interactive shell. It refuses an
existing drop-in rather than overwriting it. Replace the three labeled input
values with the reviewed operator and workstation identity before execution.
Do not run unresolved placeholders. No private key belongs on the node.

```bash
sudo bash <<'POLICY_SETUP'
set -euo pipefail
operator='<OPERATOR_LOGIN>'
client='<WORKSTATION_IPV4>'
config=/etc/ssh/sshd_config.d/00-perkforge-key-only.conf
trap 'echo "STOP: keep this session open; inspect the error before any further reload." >&2' ERR
if test -e "$config" || test -L "$config"; then
  echo 'STOP: drop-in exists; inspect it before changing anything.' >&2
  exit 1
fi
( set -o noclobber
  cat > "$config" <<'SSH_POLICY'
PubkeyAuthentication yes
AuthenticationMethods publickey
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
SSH_POLICY
)
chmod 0600 "$config"
restorecon "$config"
/usr/sbin/sshd -t
policy=$(/usr/sbin/sshd -T -C "user=$operator,host=$client,addr=$client")
for expected in 'pubkeyauthentication yes' 'authenticationmethods publickey' 'passwordauthentication no' 'kbdinteractiveauthentication no' 'permitrootlogin no' 'usepam yes'; do
  if ! grep -qxF "$expected" <<< "$policy"; then
    printf 'STOP: effective policy differs: %s; no reload performed.\n' "$expected" >&2
    exit 1
  fi
done
root_policy=$(/usr/sbin/sshd -T -C "user=root,host=$client,addr=$client")
grep -qxF 'permitrootlogin no' <<< "$root_policy"
systemctl reload sshd.service
printf 'Key-only policy validated and SSH reloaded. Keep this session open; test a fresh key-only login and sudo.\n'
POLICY_SETUP
```

No enable/disable/mask changes, new keys, package installs or restarts. PAM and
vendor crypto policy remain intact. User/source Match policy is inspected for
the supplied address; hostname Match rules need separate review if present.
On failure, keep access and inspect the retained drop-in before any retry or
future reload. A failed reload is an uncertain live outcome, not proof that the
old policy remains active. Verify a new key-only connection and password-based
sudo before closing recovery access.
