#!/usr/bin/env bash
set -euo pipefail
[[ ${1:-} == --render ]] || { echo INERT; exit 0; }
[[ $# == 2 ]] || exit 2
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
python3 "$here/validate.py" "$2"
exec ansible-playbook -i localhost, "$here/render.yaml" -e "@$2" -e manager_render=true
