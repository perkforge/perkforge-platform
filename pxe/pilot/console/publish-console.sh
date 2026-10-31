#!/usr/bin/env bash
# Native workstation publication only. No nginx/firewall/service configuration.
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
fail() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
[[ $# == 1 ]] || fail 'Usage: sudo bash publish-console.sh EXISTING_PUBLIC_KEY'
[[ $EUID == 0 ]] || fail 'Run through sudo on the workstation'
key=$1
script=$(dirname -- "$(readlink -f -- "$0")")/enroll-key.sh
parent=/srv/perkforge-pxe-pilot/http/rhel-10.2
target=$parent/console
[[ -f $key && ! -L $key ]] || fail 'Expected existing regular public key'
awk 'NR != 1 || $1 != "ssh-ed25519" || $2 !~ /^[A-Za-z0-9+\/]+=*$/ {bad=1}
     END {exit (NR != 1 || bad)}' "$key" || fail 'Expected one Ed25519 public key'
ssh-keygen -lf "$key"
bash -n "$script"
[[ $(realpath -e -- "$parent") == "$parent" ]] || fail 'Serving path contains symlink'
for directory in /srv /srv/perkforge-pxe-pilot /srv/perkforge-pxe-pilot/http "$parent"; do
  [[ -d $directory && $(stat -c %u "$directory") == 0 ]] || fail 'Unexpected serving-directory ownership/type'
done
[[ ! -e $target && ! -L $target ]] || fail 'Delivery directory exists; inspect before retry'
mkdir -m 0755 -- "$target"
install -o 0 -g 0 -m 0444 -- "$script" "$target/setup.sh"
install -o 0 -g 0 -m 0444 -- "$key" "$target/key.pub"
cmp -- "$script" "$target/setup.sh"
cmp -- "$key" "$target/key.pub"
sha256sum "$target/setup.sh" "$target/key.pub"
ssh-keygen -lf "$target/key.pub"
printf 'Published only two public files. No service/firewall changes. Verify downloaded hashes independently before execution.\n'
