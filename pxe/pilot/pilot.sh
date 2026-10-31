#!/bin/bash
# Short native entrypoint only. Never source. Configuration/lifecycle stays Ansible.
set -euo pipefail
task_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
if [[ $# != 1 ]]; then
    printf 'Usage: bash %s {activate|retry|shutdown}\n' "${BASH_SOURCE[0]}" >&2
    exit 2
fi
case "$1" in
    activate|retry)
        retry_menu=false
        [[ "$1" != retry ]] || retry_menu=true
        review="$task_root/.secrets/pxe-pilot/activation-review.yml"
        [[ -f "$review" ]] || { printf 'Missing reviewed private snapshot: %s\n' "$review" >&2; exit 2; }
        exec ansible-playbook -i localhost, -c local --ask-become-pass \
            "$task_root/pxe/pilot/activate.yml" -e "@$review" \
            -e pilot_activation_approved=true -e "pilot_retry_reviewed_menu=$retry_menu"
        ;;
    shutdown)
        exec ansible-playbook -i localhost, -c local --ask-become-pass \
            "$task_root/pxe/pilot/shutdown.yml" -e pilot_shutdown_approved=true
        ;;
    *)
        printf 'Unknown action; choose activate, retry or shutdown. Nothing executed.\n' >&2
        exit 2
        ;;
esac
