#!/usr/bin/env bash
# Reviewed console bootstrap only; run from a verified local file, never curl|bash.
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
fail() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
[[ $# == 2 ]] || fail 'Usage: sudo bash enroll-key.sh PUBLIC_KEY WORKSTATION_IPV4'
key=$1
client=$2
[[ $client =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || fail 'Expected workstation IPv4 address'
IFS=. read -r a b c d <<< "$client"
for octet in "$a" "$b" "$c" "$d"; do
  (( 10#$octet <= 255 )) || fail 'Invalid IPv4 octet'
done
[[ -f $key && ! -L $key ]] || fail 'Public key must be a regular non-symlink file'
# Exactly one ordinary Ed25519 public key, with optional printable comment.
awk 'NR != 1 || $1 != "ssh-ed25519" || $2 !~ /^[A-Za-z0-9+\/]+=*$/ {bad=1}
     END {exit (NR != 1 || bad)}' "$key" || fail 'Expected one Ed25519 public key'
ssh-keygen -lf "$key" || fail 'Invalid public key'
[[ $EUID == 0 ]] || fail 'Run through sudo from the intended administrator console'
user=${SUDO_USER:-}
[[ $user =~ ^[a-z_][a-z0-9_-]*\$?$ && $user != root ]] || fail 'Require a named sudo operator'
entry=$(getent passwd "$user") || fail 'Operator not found'
IFS=: read -r account unused uid gid gecos home shell <<< "$entry"
[[ $account == "$user" && $uid -gt 0 && $home == /home/"$user" ]] || fail 'Unexpected operator home/account'
[[ -d $home && ! -L $home && $(stat -c %u "$home") == "$uid" ]] || fail 'Unsafe home directory'
for tool in systemctl ss sshd install restorecon; do
  command -v "$tool" >/dev/null || fail "Missing required tool: $tool"
done
# Refuse rather than opening a password-authentication window.
[[ $(systemctl is-active sshd.service || :) == inactive ]] || fail 'sshd must already be inactive'
sockets=$(systemctl list-units --type=socket --state=active,activating --no-legend)
unit_files=$(systemctl list-unit-files --no-legend --no-pager) || fail 'Cannot enumerate unit files'
enabled_sockets=$(awk '$1 ~ /[.]socket$/ && $2 ~ /^enabled(-runtime)?$/ {print $1}' <<< "$unit_files")
if grep -Eiq 'ssh' <<< "$sockets$enabled_sockets"; then
  fail 'Active or enabled SSH socket present; inspect separately'
fi
listeners=$(ss -H -ltn 'sport = :22')
[[ -z $listeners ]] || fail 'TCP22 listener remains'
sshd -t || fail 'Existing sshd configuration/host keys invalid; do not generate keys automatically'
sshdir=$home/.ssh
auth=$sshdir/authorized_keys
config=/etc/ssh/sshd_config.d/00-perkforge-console-key.conf
[[ -d /etc/ssh/sshd_config.d && ! -L /etc/ssh/sshd_config.d ]] || fail 'Unsafe sshd drop-in directory'
[[ ! -e $config && ! -L $config ]] || fail 'Managed drop-in already exists; inspect before retry'
if [[ -e $sshdir || -L $sshdir ]]; then
  [[ -d $sshdir && ! -L $sshdir && $(stat -c %u "$sshdir") == "$uid" ]] || fail 'Unsafe .ssh directory'
fi
if [[ -e $auth || -L $auth ]]; then
  [[ -f $auth && ! -L $auth && $(stat -c %u "$auth") == "$uid" && $(stat -c %h "$auth") == 1 ]] || fail 'Unsafe authorized_keys'
fi
# All preflight gates passed. Existing authorized keys are retained.
cleanup() {
  result=$?
  if (( result != 0 )); then
    systemctl stop sshd.service || printf 'WARNING: could not confirm sshd stopped; inspect at console.\n' >&2
    printf 'STOP: enrollment did not finish; keep console open. Inspect the named drop-in before retry.\n' >&2
  fi
}
trap cleanup EXIT
install -d -m 0700 -o "$uid" -g "$gid" "$sshdir"
if [[ ! -e $auth ]]; then install -m 0600 -o "$uid" -g "$gid" /dev/null "$auth"; fi
if ! grep -qxF -- "$(cat "$key")" "$auth"; then
  printf '\n' >> "$auth"
  cat "$key" >> "$auth"
  printf '\n' >> "$auth"
fi
chmod 0600 "$auth"
restorecon -RF "$sshdir"
( set -o noclobber
  cat > "$config" <<'POLICY'
# Console-enrolled pilot: keep PAM and distribution crypto policy intact.
PubkeyAuthentication yes
AuthenticationMethods publickey
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
POLICY
)
chmod 0600 "$config"
restorecon "$config"
sshd -t
policy=$(sshd -T -C "user=$user,host=$client,addr=$client")
for expected in 'pubkeyauthentication yes' 'authenticationmethods publickey' 'passwordauthentication no' 'kbdinteractiveauthentication no' 'permitrootlogin no' 'usepam yes'; do
  grep -qxF "$expected" <<< "$policy" || fail "Effective policy differs: $expected; SSH remains stopped"
done
# Require authorization to use the expected conventional file for this user.
grep -qE '^authorizedkeysfile \.ssh/authorized_keys( |$)' <<< "$policy" || fail 'Unexpected AuthorizedKeysFile; SSH remains stopped'
systemctl start sshd.service
[[ $(systemctl is-active sshd.service) == active ]] || fail 'sshd failed to become active'
trap - EXIT
printf 'Key enrolled; effective key-only policy validated; sshd active. Keep console open for pinned-host-key login test.\n'
