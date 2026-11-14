#!/usr/bin/env bash
set -euo pipefail
umask 077
if [[ ${1:-} != --apply && ${1:-} != --validate ]]; then printf '%s\n' 'INERT: explicit KC reader setup required'; exit 0; fi
[[ $# == 4 ]] || exit 2
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
python3 "$here/validate-kc-reader.py" "$2" "$3" "$4" --validate
[[ $1 == --apply ]] || exit 0
python3 "$here/validate-kc-reader.py" "$2" "$3" "$4" --prepare
export PERKFORGE_GROUP_LOCK_OWNER=$$
exec flock --no-fork --exclusive --nonblock "$3.lock" ansible-playbook -i localhost, "$here/keycloak-reader.yaml" -e "@$4" -e "kc_setup_token_file=$2" -e "kc_setup_receipt_file=$3" -e "kc_setup_inputs_file=$4"
