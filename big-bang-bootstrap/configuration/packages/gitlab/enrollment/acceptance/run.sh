#!/usr/bin/env bash
set -euo pipefail
if [[ ${1:-} != --project && ${1:-} != --runner && ${1:-} != --seed && ${1:-} != --validate ]]; then echo 'INERT'; exit 0; fi
[[ $# == 4 ]] || exit 2
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
python3 "$here/validate.py" validate "$2" "$3" "$4"
[[ $1 != --validate ]] || exit 0
python3 "$here/validate.py" prepare "$2" "$3" "$4"
play="$here/project.yaml"
[[ $1 != --runner ]] || play="$here/../../../gitlab-runner/prepare-tenant-acceptance.yaml"
[[ $1 != --seed ]] || play="$here/seed.yaml"
export PERKFORGE_GROUP_LOCK_OWNER=$$
exec flock --no-fork --exclusive --nonblock "$3.lock" ansible-playbook -i localhost, "$play" -e "@$4" -e "gitlab_acceptance_token=$2" -e "gitlab_acceptance_receipt=$3" -e "gitlab_acceptance_inputs=$4"
