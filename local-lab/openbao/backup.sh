#!/usr/bin/env bash
# Operator-driven encrypted off-VM snapshot; no token creation, retention deletion or restore.
set -euo pipefail
set +x
if [[ ${1:-} != --apply || $# != 1 ]]; then
  echo 'Plan only. After approval set BAO_ADDR, BAO_CACERT, OPENBAO_BACKUP_DIR and AGE_RECIPIENT, then backup.sh --apply.'
  exit 0
fi
: "${BAO_ADDR:?Reviewed HTTPS address required}"
: "${BAO_CACERT:?Public CA file required}"
: "${OPENBAO_BACKUP_DIR:?Approved off-VM directory required}"
: "${AGE_RECIPIENT:?Public age recipient required}"
[[ $BAO_ADDR == https://* && ${BAO_SKIP_VERIFY:-false} != true && ${VAULT_SKIP_VERIFY:-false} != true ]] || { echo 'Verified HTTPS required' >&2; exit 1; }
[[ -d $OPENBAO_BACKUP_DIR && ! -L $OPENBAO_BACKUP_DIR && $(stat -c %a "$OPENBAO_BACKUP_DIR") == 700 && $(stat -c %u "$OPENBAO_BACKUP_DIR") == "$(id -u)" ]] || { echo 'Approved backup directory must be owned mode 700' >&2; exit 1; }
umask 077
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
bao operator raft snapshot save "$work/raft.snap" >/dev/null 2>/dev/null || { echo 'Snapshot failed; output suppressed' >&2; exit 1; }
output="$OPENBAO_BACKUP_DIR/openbao-$(date -u +%Y%m%dT%H%M%SZ).snap.age"
[[ ! -e $output ]] || { echo 'Refusing existing backup filename' >&2; exit 1; }
age -r "$AGE_RECIPIENT" -o "$work/encrypted" "$work/raft.snap"
# Use noclobber so a concurrent run cannot replace an existing snapshot.
(set -o noclobber; cat "$work/encrypted" > "$output")
sha256sum "$output" > "$output.sha256"
echo 'Encrypted snapshot saved; no plaintext snapshot retained. Retention and restore require separate reviewed actions.'
