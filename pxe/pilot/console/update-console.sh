#!/usr/bin/env bash
# Replace only the known first enrollment script; no service/config changes.
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
fail() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
[[ $EUID == 0 && $# == 0 ]] || fail 'Run through sudo without arguments'
base=/srv/perkforge-pxe-pilot/http/rhel-10.2/console
source=$(dirname -- "$(readlink -f -- "$0")")/enroll-key.sh
old=f753d44d0b742fc250e41556208841a7af685905181954021e3d2aa9107c7872
new=33a7fb21d780a469f0a107690a37393c52465cc11cee96c2d9622b004749f5fb
[[ $(realpath -e -- "$base") == "$base" && $(stat -c %u "$base") == 0 ]] || fail 'Unexpected delivery directory'
for file in setup.sh key.pub; do
  [[ -f $base/$file && ! -L $base/$file && $(stat -c %u:%a:%h "$base/$file") == 0:444:1 ]] || fail 'Unexpected delivery file metadata'
done
[[ $(sha256sum "$base/setup.sh" | cut -d ' ' -f1) == "$old" ]] || fail 'Published script differs; inspect before retry'
[[ $(sha256sum "$source" | cut -d ' ' -f1) == "$new" ]] || fail 'Replacement source differs from reviewed hash'
bash -n "$source"
key_before=$(sha256sum "$base/key.pub")
[[ ! -e $base/.setup-replacement && ! -L $base/.setup-replacement ]] || fail 'Replacement temporary file exists'
install -o 0 -g 0 -m 0444 -- "$source" "$base/.setup-replacement"
cmp -- "$source" "$base/.setup-replacement"
mv -T -- "$base/.setup-replacement" "$base/setup.sh"
[[ $(sha256sum "$base/key.pub") == "$key_before" ]] || fail 'Public key changed unexpectedly'
sha256sum "$base/setup.sh" "$base/key.pub"
printf 'Updated setup.sh only. Re-download and independently verify before any node retry.\n'
