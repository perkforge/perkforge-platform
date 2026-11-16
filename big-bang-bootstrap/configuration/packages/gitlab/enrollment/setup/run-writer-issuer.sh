#!/usr/bin/env bash
set -euo pipefail
umask 077
case ${1:-} in --apply|--validate|--cleanup) ;; *) echo INERT; exit 0;; esac
[[ $# == 4 ]] || exit 2
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
python3 "$here/writer-issuer-state.py" validate "$2" "$3" "$4"
[[ $1 != --validate ]] || exit 0
python3 "$here/writer-issuer-state.py" prepare "$2" "$3" "$4"
export PERKFORGE_GROUP_LOCK_OWNER=$$
mode=apply; [[ $1 != --cleanup ]] || mode=cleanup
exec flock --no-fork --exclusive --nonblock "$3.lock" ansible-playbook -i localhost, "$here/writer-issuer.yaml" -e "@$4" -e "issuer_root_file=$2" -e "issuer_receipt_file=$3" -e "issuer_inputs_file=$4" -e "issuer_mode=$mode"
