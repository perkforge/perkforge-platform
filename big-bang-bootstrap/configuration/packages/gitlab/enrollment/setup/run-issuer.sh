#!/usr/bin/env bash
set -euo pipefail
umask 077
if [[ ${1:-} != --apply && ${1:-} != --validate && ${1:-} != --cleanup ]]; then echo INERT; exit 0; fi
[[ $# == 4 ]] || exit 2
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
python3 "$here/issuer-state.py" validate "$2" "$3" "$4"
[[ $1 != --validate ]] || exit 0
play=issuer.yaml
[[ $1 != --cleanup ]] || play=issuer-clean.yaml
python3 "$here/issuer-state.py" prepare "$2" "$3" "$4"
export PERKFORGE_GROUP_LOCK_OWNER=$$
exec flock --no-fork --exclusive --nonblock "$3.lock" ansible-playbook -i localhost, "$here/$play" -e "@$4" -e "issuer_root_file=$2" -e "issuer_receipt_file=$3" -e "issuer_inputs_file=$4"
