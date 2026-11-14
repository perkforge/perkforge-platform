#!/usr/bin/env bash
set -euo pipefail
umask 077
if [[ ${1:-} != --apply && ${1:-} != --validate ]]; then printf '%s\n' 'INERT: explicit phase execution required'; exit 0; fi
[[ $# == 4 ]] || exit 2
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
python3 "$here/paths.py" memberships "$2" "$3" >/dev/null
python3 "$here/membership-state.py" "$2" "$3" "$4" >/dev/null
[[ $1 == --apply ]] || { printf '%s\n' 'Validated; no authentication or native calls'; exit 0; }
w=$3
# Standalone use and packaged use share the same stable cross-attempt lock.
if [[ -z ${PERKFORGE_PHASE_LOCK_OWNER:-} ]]; then
 python3 "$here/phase-lock.py" --prepare "$3" "$4"
 export PERKFORGE_PHASE_LOCK_OWNER=$$
 exec flock --no-fork --exclusive --nonblock "$(dirname -- "$4")/trigger.lock" bash "$0" "$@"
fi
python3 "$here/phase-lock.py" --locked "$3" "$4"
set -o noclobber
if ansible-playbook -i localhost, "$here/memberships.yaml" -e "@$2" -e "phase_inputs=$2" -e "phase_work=$w" -e "phase_group_receipt=$4" >"$w/run.log" 2>&1; then
 cat "$w/result.json"
else
 if [[ -f $w/result.json ]]; then cat "$w/result.json"; else printf '%s\n' '{"phase":"MembershipFailed","substage":"local-execution","category":"result-unavailable","membership_ready":false}'; fi
 exit 1
fi
