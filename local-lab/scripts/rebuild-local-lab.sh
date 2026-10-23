#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
scripts_dir="$repo_root/local-lab/scripts"
secrets_dir="$repo_root/.secrets"
state_file="$secrets_dir/local-lab-rebuild-state"
image_dir="$repo_root/images"
iso="$image_dir/rhel-10.2-x86_64-dvd.iso"
expected_iso_sha256="e15cb333529c332e76e4b1b946efe3515c99f996546675aec18e8effdf2540a5"
volume_label="RHEL-10-2-BaseOS-x86_64"
mode=""

usage() {
  cat <<'USAGE'
Usage:
  local-lab/scripts/rebuild-local-lab.sh --confirm-destroy
  local-lab/scripts/rebuild-local-lab.sh --resume

Runs the complete local VM rebuild without interactive prompts:
  1. Tears down only cks-control and cks-worker and their same-named disks.
  2. Installs RHEL and waits for both VMs.
  3. Completes Ansible host configuration.
  4. Installs RKE2 and waits for both Kubernetes nodes to become Ready.
  5. Installs Rancher and waits for its deployments.
  6. Deploys the conservative Fleet profile (Keycloak and GitLab dependencies) and waits for its bundles to be Ready.

--confirm-destroy deletes all cluster data stored on the VM disks. --resume
continues without deleting VM data, and is accepted only after a completed
teardown checkpoint. The RHEL ISO and .secrets/ are preserved. The script
exits at the first failure and saves a log in .secrets/.
USAGE
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

[[ $# == 1 ]] || { usage >&2; exit 2; }
case "$1" in
  --confirm-destroy) mode="rebuild" ;;
  --resume) mode="resume" ;;
  *) usage >&2; exit 2 ;;
esac

umask 077
mkdir -p "$secrets_dir"
chmod 0700 "$secrets_dir"
log_file="$secrets_dir/local-lab-rebuild-$(date +%Y%m%d-%H%M%S)-$$.log"
exec > >(tee -a "$log_file") 2>&1
trap 'result=$?; trap - ERR; printf "\nFAILED (exit %s) near: %s\nLog: %s\n" "$result" "$BASH_COMMAND" "$log_file" >&2; exit "$result"' ERR

cd "$repo_root"
export PATH="/usr/sbin:/usr/bin:/bin:$PATH"
export LOCAL_LAB_USE_SUDO=never
export GIT_TERMINAL_PROMPT=0
export GCM_INTERACTIVE=never

printf 'Local lab %s starting at %s\n' "$mode" "$(date --iso-8601=seconds)"
if [[ "$mode" == "rebuild" ]]; then
  printf 'This deletes both VM disks and all cluster data stored on them.\n'
else
  printf 'Resume mode preserves VM disks and all data on them.\n'
fi
printf 'Progress log: %s\n\n' "$log_file"

for utility in ansible-playbook virsh python3 virt-install sha256sum blkid openssl \
  ssh-keygen ssh-keyscan git tee awk curl; do
  command -v "$utility" >/dev/null 2>&1 || die "Required command not found: $utility"
done

[[ -r "$iso" ]] || die "RHEL DVD ISO is missing or unreadable: $iso"
actual_iso_sha256="$(sha256sum "$iso" | awk '{print $1}')"
[[ "$actual_iso_sha256" == "$expected_iso_sha256" ]] || die "RHEL ISO checksum mismatch; refusing to delete the existing VMs."
actual_volume_label="$(blkid -p -s LABEL -o value "$iso" 2>/dev/null || true)"
[[ "$actual_volume_label" == "$volume_label" ]] || die "Unexpected RHEL ISO volume label '$actual_volume_label'; refusing teardown."

virsh -c qemu:///system uri >/dev/null 2>&1 || die "Direct access to system libvirt is unavailable. Configure libvirt access first; this script will not stop for a sudo prompt."
[[ -w "$image_dir" ]] || die "The images directory is not writable by the current user; configure disk permissions before rebuilding."
[[ -f local-lab/ansible/ansible.cfg && -f local-lab/ansible/inventory/hosts.yml ]] || die "Local-lab Ansible configuration is missing."
[[ -x "$scripts_dir/deploy-platform-profile.sh" ]] || die "The conservative Fleet profile deployment script is missing or not executable."

git remote get-url origin >/dev/null 2>&1 || die "Git remote 'origin' is required for Fleet to fetch the configured local profile."
git fetch --quiet origin main || die "Could not fetch origin/main; refusing to proceed because Fleet needs that branch."
fleet_expected_commit="$(git rev-parse FETCH_HEAD)"
git diff --quiet FETCH_HEAD -- local-lab/fleet || die "Local Fleet files differ from origin/main; push the intended Fleet configuration before rebuilding."
untracked_fleet_files="$(git ls-files --others --exclude-standard -- local-lab/fleet)"
[[ -z "$untracked_fleet_files" ]] || die "Untracked Fleet files exist; commit and push the intended configuration before rebuilding."
for fleet_file in \
  local-lab/fleet/gitrepos/local-lab.yaml \
  local-lab/fleet/gitrepos/platform-apps.yaml \
  local-lab/fleet/bundles/storage/fleet.yaml \
  local-lab/fleet/bundles/tenant-foundation/fleet.yaml \
  local-lab/fleet/bundles/cnpg-operator/fleet.yaml \
  local-lab/fleet/bundles/keycloak-db/fleet.yaml \
  local-lab/fleet/bundles/keycloak-db/cluster.yaml \
  local-lab/fleet/bundles/keycloak/fleet.yaml \
  local-lab/fleet/bundles/keycloak/values.yaml \
  local-lab/fleet/bundles/gitlab-dependencies/database/fleet.yaml \
  local-lab/fleet/bundles/gitlab-dependencies/database/cluster.yaml \
  local-lab/fleet/bundles/gitlab-dependencies/valkey/fleet.yaml \
  local-lab/fleet/bundles/gitlab-dependencies/valkey/values.yaml \
  local-lab/fleet/bundles/gitlab/fleet.yaml \
  local-lab/fleet/bundles/harbor/fleet.yaml \
  local-lab/fleet/bundles/mattermost-operator/fleet.yaml \
  local-lab/fleet/bundles/mattermost/fleet.yaml; do
  git cat-file -e "FETCH_HEAD:$fleet_file" 2>/dev/null || die "origin/main is missing $fleet_file; refusing teardown."
done

if [[ "$mode" == "resume" ]]; then
  [[ -r "$state_file" ]] || die "No successful teardown checkpoint exists. Use --confirm-destroy for a full rebuild."
  rebuild_state="$(<"$state_file")"
  case "$rebuild_state" in
    teardown-complete|rhel-provisioned|hosts-configured|rke2-ready|rancher-ready|profile-deployed|completed)
      printf 'Resuming from checkpoint: %s (VM disks will be preserved).\n' "$rebuild_state" ;;
    teardown-in-progress)
      die "The previous run stopped during teardown. Review VM and disk state, then run --confirm-destroy to restart safely." ;;
    *) die "Unknown rebuild checkpoint '$rebuild_state'; inspect $state_file before proceeding." ;;
  esac
fi

write_state() {
  local next_state="$1" temporary_file
  temporary_file="$(mktemp "$secrets_dir/local-lab-rebuild-state.XXXXXX")"
  printf '%s\n' "$next_state" > "$temporary_file"
  chmod 0600 "$temporary_file"
  mv -f -- "$temporary_file" "$state_file"
}

printf '%s\n' 'Preflight passed: tools, ISO, libvirt access, Ansible files, and Fleet content are available.'
if [[ "$mode" == "rebuild" ]]; then
  printf '\n%s\n' 'Stage 1/6: inspect the exact VM teardown scope.'
  "$scripts_dir/teardown-vms.sh"

  printf '\n%s\n' 'Stage 2/6: tear down the two local VMs and their data disks.'
  write_state teardown-in-progress
  "$scripts_dir/teardown-vms.sh" --apply --yes
  write_state teardown-complete
else
  printf '\n%s\n' 'Resume mode: preserving VM definitions and disks; rerunning idempotent provisioning and deployment stages.'
fi

printf '\n%s\n' 'Provision RHEL and wait for both VMs.'
"$scripts_dir/provision-vms.sh"
write_state rhel-provisioned

printf '\n%s\n' 'Configure RHEL host prerequisites.'
ANSIBLE_CONFIG="$repo_root/local-lab/ansible/ansible.cfg" \
  ansible-playbook --become-password-file "$secrets_dir/rhel-lab-console-password" \
  local-lab/ansible/playbooks/configure-hosts.yml
write_state hosts-configured

printf '\n%s\n' 'Install RKE2 and wait for both nodes.'
ANSIBLE_CONFIG="$repo_root/local-lab/ansible/ansible.cfg" \
  ansible-playbook --become-password-file "$secrets_dir/rhel-lab-console-password" \
  local-lab/ansible/playbooks/install-rke2.yml

"$secrets_dir/kubectl" --kubeconfig "$secrets_dir/rke2.yaml" \
  wait --for=condition=Ready nodes --all --timeout=10m
"$secrets_dir/kubectl" --kubeconfig "$secrets_dir/rke2.yaml" get nodes -o wide
write_state rke2-ready

printf '\n%s\n' 'Install Rancher and deploy the conservative platform profile through Fleet.'
ANSIBLE_CONFIG="$repo_root/local-lab/ansible/ansible.cfg" \
  ansible-playbook local-lab/ansible/playbooks/install-rancher.yml
write_state rancher-ready

FLEET_EXPECTED_COMMIT="$fleet_expected_commit" "$scripts_dir/deploy-platform-profile.sh"
write_state profile-deployed

printf 'Checking Rancher UI endpoint.\n'
curl --silent --show-error --insecure --fail --retry 60 --retry-delay 5 --retry-connrefused \
  --max-time 5 --resolve rancher.local-lab.test:443:192.168.122.201 \
  https://rancher.local-lab.test/ping -o /dev/null || die "Rancher UI endpoint did not respond successfully."
printf 'Rancher UI endpoint: ready.\n'

printf '\nLocal lab rebuild completed at %s.\n' "$(date --iso-8601=seconds)"
printf 'RHEL host configuration, RKE2, Rancher, and the conservative Fleet profile are ready.\n'
printf 'Rancher: https://rancher.local-lab.test (admin password file: %s/rancher-bootstrap-password)\n' "$secrets_dir"
printf 'Keycloak: http://keycloak.local-lab.test/auth/\n'
printf 'Keycloak and Valkey readiness checks passed.\n'
printf 'GitLab application, Harbor Fleet bundle, and Mattermost are opt-in profiles.\n'
printf 'Full log: %s\n' "$log_file"
write_state completed
