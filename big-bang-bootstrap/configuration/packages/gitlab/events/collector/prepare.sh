#!/bin/bash
# Explicit operator step: apply only to an isolated clean checkout of the pinned upstream.
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
[[ $# == 1 ]] || { echo 'usage: prepare.sh ISOLATED_UPSTREAM_CHECKOUT' >&2; exit 2; }
SOURCE=$(realpath -- "$1")
python3 -I "$HERE/verify.py"
mapfile -t PIN < <(python3 -I - "$HERE/source.json" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]));print(m['upstream_commit']);print(m['patched_tree'])
PY
)
[[ $(git -C "$SOURCE" rev-parse --show-toplevel) == "$SOURCE" ]]
[[ $(git -C "$SOURCE" rev-parse HEAD) == "${PIN[0]}" ]]
[[ -z $(git -C "$SOURCE" status --porcelain --untracked-files=all) ]]
[[ -z $(git -C "$SOURCE" ls-files --others) ]]
git -C "$SOURCE" apply --index --check "$HERE/snapshot.patch"
git -C "$SOURCE" apply --index "$HERE/snapshot.patch"
[[ $(git -C "$SOURCE" write-tree) == "${PIN[1]}" ]]
echo 'PASS exact patched Git tree; no upstream publication or build performed'
