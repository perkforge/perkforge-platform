#!/usr/bin/env bash
set -euo pipefail
# Arguments contain paths only, never credential values. No action by default.
if [[ ${1:-} != --apply && ${1:-} != --validate ]]; then
  printf '%s\n' 'INERT: explicit --apply TOKEN_FILE RECEIPT_FILE INPUTS_FILE required.'
  exit 0
fi
[[ $# == 4 ]] || exit 2
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
if [[ $1 == --validate ]]; then
  exec python3 "$here/verify_group_paths.py" --token "$2" --receipt "$3" --inputs "$4" --paths-only
fi
python3 "$here/verify_group_paths.py" --token "$2" --receipt "$3" --inputs "$4" --prepare
# Native flock holds the lock for the entire child process; fail rather than queue.
export PERKFORGE_GROUP_LOCK_OWNER=$$
exec flock --no-fork --exclusive --nonblock "$3.lock" \
  ansible-playbook -i localhost, "$here/ensure-groups.yaml" -e "@$4" \
  -e "gitlab_native_token_file=$2" -e "gitlab_group_receipt_file=$3"
