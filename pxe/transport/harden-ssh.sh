#!/usr/bin/env bash
# Run only after independently verified key-only login; retain recovery session.
set -euo pipefail
[[ $EUID == 0 && $# == 2 ]] || { echo 'Usage: sudo bash harden-ssh.sh OPERATOR WORKSTATION_IPV4' >&2; exit 1; }
operator=$1
client=$2
[[ $operator =~ ^[a-z_][a-z0-9_-]*$ && $operator != root ]] || { echo 'STOP: invalid operator' >&2; exit 1; }
[[ $client =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || { echo 'STOP: invalid client address' >&2; exit 1; }
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
