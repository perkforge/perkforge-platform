#!/usr/bin/env bash
set -euo pipefail
umask 077
if [[ ${1:-} != --apply && ${1:-} != --validate ]]; then printf '%s\n' 'INERT: explicit phase execution required'; exit 0; fi
[[ $# == 3 ]] || exit 2
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
python3 "$here/paths.py" attest "$2" "$3" >/dev/null
[[ $1 == --apply ]] || { printf '%s\n' 'Validated; no authentication or native calls'; exit 0; }
w=$3
set -o noclobber
if ansible-playbook -i localhost, "$here/attest.yaml" -e "@$2" \
 -e "phase_inputs=$2" -e "phase_work=$w" \
 -e "phase_kc_id=$w/kc-client-id" -e "phase_kc_secret=$w/kc-client-secret" \
 -e "phase_gitlab_reader=$w/gitlab-reader" -e "phase_lab_ca=$w/lab-ca.crt" \
 -e "phase_api_token=$w/api-token" -e "phase_api_ca=$w/api-ca.crt" >"$w/run.log" 2>&1; then
 cat "$w/result.json"
else
 if [[ -f $w/result.json ]]; then cat "$w/result.json"; else printf '%s\n' '{"phase":"AttestationFailed","substage":"local-execution","category":"result-unavailable","membership_ready":false}'; fi
 exit 1
fi
