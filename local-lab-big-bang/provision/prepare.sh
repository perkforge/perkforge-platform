#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
mode="${1:-plan}"
assets=/home/corey/src/perkforge-platform
case "$mode" in
  plan)
    printf '%s\n' 'Preparation only: cks-control (30 GiB), cks-worker (100 GiB).' \
      "Disks: $assets/images/cks-control.qcow2, $assets/images/cks-worker.qcow2" \
      'No teardown or deployment is performed by this entrypoint.'
    exit 0 ;;
  rhel|rke2) ;;
  *) echo 'Usage: prepare.sh [plan|rhel|rke2]' >&2; exit 2 ;;
esac
[[ "${LOCAL_TRIAL_APPROVED:-}" == yes ]] || { echo 'Action-time approval required; see README.md.' >&2; exit 2; }
: "${LOCAL_TRIAL_STATE:?Set an absolute NEW ignored .secrets subdirectory for this trial}"
[[ "$LOCAL_TRIAL_STATE" == "$assets/.secrets/"* && "$LOCAL_TRIAL_STATE" != *..* ]] || exit 2
export LOCAL_LAB_STATE_DIR="$LOCAL_TRIAL_STATE"
export LOCAL_LAB_IMAGE_DIR="$assets/images"
export LOCAL_LAB_SSH_KEY="$assets/.secrets/rke2-lab-ed25519"
export LOCAL_LAB_CONSOLE_PASSWORD_FILE="$assets/.secrets/rhel-lab-console-password"
export LOCAL_LAB_REQUIRE_EXISTING_CREDENTIALS=true
export LOCAL_LAB_RETRY_NEW_INSTALL=false
export LOCAL_LAB_USE_SUDO=never
if [[ "$mode" == rhel ]]; then
  [[ ! -e "$LOCAL_TRIAL_STATE" ]] || { echo 'Choose a new trial state directory.' >&2; exit 2; }
  virsh -c qemu:///system uri >/dev/null
  for vm in cks-control cks-worker; do
    if virsh -c qemu:///system dominfo "$vm" >/dev/null 2>&1; then
      echo "Refusing existing VM $vm; teardown is a separately approved action." >&2; exit 2
    fi
    [[ ! -e "$assets/images/$vm.qcow2" ]] || exit 2
  done
  exec "$root/local-lab/scripts/provision-vms.sh"
fi
[[ -d "$LOCAL_TRIAL_STATE" && ! -L "$LOCAL_TRIAL_STATE" ]] || exit 2
cd "$root"
export ANSIBLE_CONFIG="$root/local-lab/ansible/ansible.cfg"
export ANSIBLE_PRIVATE_KEY_FILE="$LOCAL_LAB_SSH_KEY"
export ANSIBLE_SSH_ARGS="-o UserKnownHostsFile=$LOCAL_TRIAL_STATE/known_hosts -o IdentitiesOnly=yes"
ansible-playbook -i "$root/local-lab/ansible/inventory/hosts.yml" \
  --become-password-file "$LOCAL_LAB_CONSOLE_PASSWORD_FILE" \
  -e "local_rke2_output_dir=$LOCAL_TRIAL_STATE" \
  "$root/local-lab-big-bang/provision/rke2.yaml"
"$LOCAL_TRIAL_STATE/kubectl" --kubeconfig "$LOCAL_TRIAL_STATE/rke2.yaml" \
  wait --for=condition=Ready nodes --all --timeout=10m
