#!/bin/bash
# Shared approved host-trust/key-only handoff. No configuration generator.
# Never source, trace, tee, record terminal input or accept passwords as arguments.
set -euo pipefail
[[ $# == 7 && $1 == approved ]] || {
  echo 'Usage: bash access.sh approved HOST_IPV4 USER EXISTING_KEY WORKSTATION_IPV4 TRUST_RUN_DIR EXPECTED_HOSTNAME' >&2; exit 2;
}
host=$2
operator=$3
key=$4
client=$5
run_arg=$6
expected_hostname=$7
[[ $expected_hostname =~ ^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$ ]] || { echo 'STOP: expected hostname required.' >&2; exit 2; }
valid_ip() {
  [[ $1 =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || return 1
  local octet
  local -a parts
  IFS=. read -r -a parts <<< "$1"
  for octet in "${parts[@]}"; do (( 10#$octet <= 255 )) || return 1; done
}
valid_ip "$host" && valid_ip "$client" && [[ $host != "$client" ]] || { echo 'STOP: invalid host/client IPv4.' >&2; exit 2; }
[[ $operator =~ ^[a-z_][a-z0-9_-]*$ && $operator != root ]] || { echo 'STOP: named non-root operator required.' >&2; exit 2; }
[[ -d "$run_arg" && ! -L "$run_arg" && -f "$key" && -f "$key.pub" ]] || { echo 'STOP: existing key and private trust directory required.' >&2; exit 2; }
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
run=$(cd -- "$run_arg" && pwd -P)
helper="$here/harden-ssh.sh"
[[ -f "$run/trust-confirmed.txt" && ! -L "$run/trust-confirmed.txt" && -f "$run/known_hosts" && ! -L "$run/known_hosts" && -f "$helper" ]]
[[ $(stat -c %a "$run") == 700 && $(stat -c %a "$run/known_hosts") == 600 && $(stat -c %a "$run/trust-confirmed.txt") == 600 ]] || { echo 'STOP: private trust-directory/file modes required.' >&2; exit 2; }
[[ $(wc -l < "$run/known_hosts") == 1 ]] || { echo 'STOP: exactly one pinned host key required.' >&2; exit 2; }
read -r pinned_host pinned_type pinned_key pinned_extra < "$run/known_hosts"
[[ $pinned_host == "$host" && $pinned_type == ssh-ed25519 && $pinned_key =~ ^[A-Za-z0-9+/=]+$ && -z $pinned_extra ]] || { echo 'STOP: pinned Ed25519 key must name this exact host.' >&2; exit 2; }
ssh-keygen -lf "$run/known_hosts" >/dev/null
umask 077
log_file=$(mktemp "$run/access-output-XXXXXXXX.log")
summary="${log_file%.log}.summary.txt"
stage=preflight
finish() {
 rc=$?
 trap - EXIT
 { printf 'Action: approved SSH key-only handoff\nExit status: %s\nFinal stage: %s\n' "$rc" "$stage"; printf 'Step results only; terminal/password input not recorded. Physical console retained.\n'; } > "$summary"
 chmod 0600 "$log_file" "$summary"
 printf '\nPrivate result summary: %s (exit %s)\n' "$summary" "$rc"
 [[ $rc == 0 ]] || printf 'STOP: preserve console/current access and inspect before any retry.\n'
 exit "$rc"
}
trap finish EXIT
mark() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$1" >> "$log_file"; }
base=(-o "UserKnownHostsFile=$run/known_hosts" -o GlobalKnownHostsFile=/dev/null -o StrictHostKeyChecking=yes -o HostKeyAlgorithms=ssh-ed25519 -o UpdateHostKeys=no -o IdentitiesOnly=yes -o ControlMaster=no -o ControlPath=none -o ConnectTimeout=10)
keyonly=("${base[@]}" -i "$key" -o PreferredAuthentications=publickey -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no)
endpoint="$operator@$host"
mark 'START: physical-console-confirmed pinned key; no credentials logged'
stage=public-key-enrollment
printf 'Enroll existing public key. Enter host password/key passphrase locally if prompted.\n'
ssh-copy-id -i "$key.pub" "${base[@]}" "$endpoint"
mark 'PASS: public-key enrollment command completed'
stage=fresh-key-only-login-and-transfer
inspection=$(mktemp "$run/installed-host-XXXXXXXX.txt")
helper_sha=$(sha256sum "$helper"); helper_sha=${helper_sha%% *}
printf '\nVerify fresh key-only access and transfer the reviewed policy helper.\n'
# SSH reads any key passphrase from the local tty; stdin contains only this public script.
ssh -T "${keyonly[@]}" "$endpoint" "set -eu; test \"\$(id -un)\" = '$operator'; test \"\${SSH_CONNECTION%% *}\" = '$client'; test ! -e /etc/ssh/sshd_config.d/00-perkforge-key-only.conf; test ! -L /etc/ssh/sshd_config.d/00-perkforge-key-only.conf; d=\$(umask 077; mktemp -d /tmp/perkforge-access-XXXXXXXX); cat > \"\$d/harden-ssh.sh\"; printf '%s  %s\\n' '$helper_sha' \"\$d/harden-ssh.sh\" | sha256sum -c -; printf 'Hostname: '; hostname; printf 'User: '; id -un; lsblk -b -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS; for mount in / /boot /boot/efi; do findmnt -n \"\$mount\"; done; printf 'Remote helper: %s\\n' \"\$d/harden-ssh.sh\"" < "$helper" > "$inspection"
remote_helper=$(sed -n 's/^Remote helper: //p' "$inspection")
[[ $remote_helper =~ ^/tmp/perkforge-access-[A-Za-z0-9]{8}/harden-ssh\.sh$ ]]
[[ $(sed -n 's/^Hostname: //p' "$inspection") == "$expected_hostname" ]]
mark 'PASS: fresh key-only login, expected operator/client, no prior policy, remote helper SHA256 and private read-only inspection'
stage=key-only-policy
printf '\nApply approved key-only policy. Enter host sudo password locally.\n'
ssh -tt "${keyonly[@]}" "$endpoint" "test \"\$(hostname)\" = '$expected_hostname' && test \"\${SSH_CONNECTION%% *}\" = '$client' || exit 1; if sudo bash '$remote_helper' '$operator' '$client'; then exit 0; else printf 'STOP: helper failed; retain this recovery session and physical console.\\n'; bash; exit 1; fi"
mark 'PASS: reviewed helper validated SSH syntax/effective policy and reloaded SSH'
stage=fresh-key-login-and-password-sudo
printf '\nFinal fresh key-only login and password-authenticated sudo check.\n'
ssh -tt "${keyonly[@]}" "$endpoint" "set -eu; test \"\$(hostname)\" = '$expected_hostname'; test \"\$(id -un)\" = '$operator'; sudo -k; if sudo -n true 2>/dev/null; then echo 'STOP: sudo did not require a password'; exit 1; fi; sudo -v; test \"\$(sudo -n hostname)\" = '$expected_hostname'; echo 'PASS: fresh key-only login and password-authenticated sudo'"
mark 'PASS: separate fresh key-only login, password required for sudo and privileged hostname verified'
stage=complete
printf '\nSSH handoff completed; physical console remains available.\n'
