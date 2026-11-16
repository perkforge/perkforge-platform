#!/bin/bash
# Explicit local artifact build; never installs, uploads, selects or deploys it.
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
[[ $# == 2 ]] || { echo 'usage: build.sh PREPARED_CHECKOUT NEW_OUTPUT_DIRECTORY' >&2; exit 2; }
SOURCE=$(realpath -- "$1")
OUT=$(realpath -m -- "$2")
[[ ! -e "$OUT" && ! -L "$OUT" ]]
python3 -I "$HERE/verify.py"
TREE=$(python3 -I -c 'import json,sys;print(json.load(open(sys.argv[1]))["patched_tree"])' "$HERE/source.json")
[[ $(git -C "$SOURCE" write-tree) == "$TREE" ]]
git -C "$SOURCE" diff --exit-code
[[ -z $(git -C "$SOURCE" ls-files --others) ]]
[[ $(go env GOVERSION) == go1.26.8 ]]
# Disable ambient workspace/flag overrides; use verified module checksums.
export GOWORK=off GOFLAGS= GOENV=off GOTOOLCHAIN=local
export GOPROXY=https://proxy.golang.org GOSUMDB=sum.golang.org GOPRIVATE= GONOSUMDB= GONOPROXY=
(cd "$SOURCE" && go mod verify && go test -mod=readonly -race ./...)
mkdir -m 0700 -- "$OUT"
(cd "$SOURCE" && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -mod=readonly -trimpath -buildvcs=false -ldflags=-buildid= -o "$OUT/gitlab-ci-pipelines-exporter" ./cmd/gitlab-ci-pipelines-exporter)
cp -- "$HERE/LICENSE.upstream" "$OUT/LICENSE"
cp -- "$HERE/source.json" "$OUT/source.json"
(cd "$OUT" && sha256sum gitlab-ci-pipelines-exporter LICENSE source.json > SHA256SUMS)
echo 'Local artifact built; independent reproducibility, image provenance and deployment gates remain'
