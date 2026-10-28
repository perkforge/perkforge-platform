#!/usr/bin/env bash
# Read-only verification; optional expected commit comes from earlier release evidence.
set -euo pipefail
repo=${1:?Usage: verify-release-ref.sh owner/repo vMAJOR.MINOR.PATCH [expected-commit]}
tag=${2:?A published version tag is required}
expected=${3:-}
[[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || exit 2
[[ "$tag" =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]] || exit 2
[[ -z "$expected" || "$expected" =~ ^[0-9a-f]{40}$ ]] || exit 2
published=$(gh release view "$tag" -R "$repo" --json isDraft,isPrerelease,tagName --jq '[.tagName, .isDraft, .isPrerelease] | @tsv')
test "$published" = "$(printf '%s\tfalse\tfalse' "$tag")" || { echo 'Published stable release required' >&2; exit 1; }
refs=$(git ls-remote --exit-code "https://github.com/$repo.git" "refs/tags/$tag" "refs/tags/$tag^{}")
# Annotated tags resolve through ^{}; lightweight tags already identify the commit.
resolved=$(printf '%s\n' "$refs" | awk -v ref="refs/tags/$tag" '$2 == ref {base=$1} $2 == ref "^{}" {peeled=$1} END {print (peeled ? peeled : base)}')
[[ "$resolved" =~ ^[0-9a-f]{40}$ ]] || { echo 'Tag did not resolve' >&2; exit 1; }
commit=$(gh api "repos/$repo/commits/$tag" --jq .sha)
test "$resolved" = "$commit" || { echo 'Tag is not a consistent source commit' >&2; exit 1; }
if [[ -n "$expected" && "$resolved" != "$expected" ]]; then
  echo 'Tag resolution changed; reject and investigate, never retag' >&2
  exit 1
fi
printf 'Repository: %s\nTag: %s\nResolved source commit: %s\n' "$repo" "$tag" "$resolved"
