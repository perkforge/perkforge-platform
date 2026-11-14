#!/usr/bin/env bash
set -euo pipefail
if [[ ${1:-} != --apply ]]; then printf '%s\n' 'INERT: --apply WRITER ATTESTATION GROUP_RECEIPT INPUTS GRANT_RECEIPT required'; exit 0; fi
[[ $# == 6 ]] || exit 2
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
python3 "$here/verification/membership_inputs.py" "$2" "$3" "$4" "$5" "$6" --prepare
export PERKFORGE_GROUP_LOCK_OWNER=$$
exec flock --no-fork --exclusive --nonblock "$4.lock" ansible-playbook -i localhost, "$here/reconcile-membership.yaml" -e "@$5" -e "gitlab_native_token_file=$2" -e "gitlab_native_attestation_file=$3" -e "gitlab_native_group_receipt_file=$4" -e "gitlab_native_membership_inputs_file=$5" -e "gitlab_native_grant_receipt_file=$6"
