#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
secrets_dir="${repo_root}/.secrets"
kubeconfig="${secrets_dir}/rke2.yaml"
kubectl="${secrets_dir}/kubectl"

if [[ ! -x "${kubectl}" || ! -r "${kubeconfig}" ]]; then
  echo "Missing local cluster credentials. Run local-lab/ansible/playbooks/install-rke2.yml first." >&2
  exit 1
fi

"${repo_root}/local-lab/scripts/prepare-platform-secrets.sh"
"${kubectl}" --kubeconfig "${kubeconfig}" apply -f \
  "${repo_root}/local-lab/fleet/gitrepos/local-lab.yaml" \
  -f "${repo_root}/local-lab/fleet/gitrepos/platform-apps.yaml"

expected_commit="$(git -C "${repo_root}" rev-parse HEAD)"
expected_bundles=(
  local-lab-storage
  local-lab-tenant-foundation
  local-lab-cnpg-operator
  local-lab-keycloak-database
  local-lab-keycloak
  local-lab-gitlab-database
  local-lab-gitlab-valkey
)
deadline=$((SECONDS + 1800))
error_since=0
last_error_state=""
next_status_report=$((SECONDS + 60))

printf 'Waiting for Fleet to fetch %s and ready %s conservative-profile bundles' \
  "${expected_commit}" "${#expected_bundles[@]}"
while (( SECONDS < deadline )); do
  repo_rows="$("${kubectl}" --kubeconfig "${kubeconfig}" -n fleet-local \
    get gitrepos local-lab platform-apps -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.commit}{"\t"}{range .status.conditions[?(@.type=="Stalled")]}{.status}{end}{"\n"}{end}' 2>/dev/null || true)"
  bundle_states="$("${kubectl}" --kubeconfig "${kubeconfig}" -n fleet-local \
    get bundles --no-headers 2>/dev/null || true)"

  all_ready=true
  for name in local-lab platform-apps; do
    commit="$(awk -v name="${name}" '$1 == name { print $2; exit }' <<<"${repo_rows}")"
    stalled="$(awk -v name="${name}" '$1 == name { print $3; exit }' <<<"${repo_rows}")"
    [[ "${commit}" == "${expected_commit}" && "${stalled}" == "False" ]] || all_ready=false
  done
  for name in "${expected_bundles[@]}"; do
    ready="$(awk -v name="${name}" '$1 == name { print $2; exit }' <<<"${bundle_states}")"
    [[ "${ready}" == "1/1" ]] || all_ready=false
  done

  error_state="$(grep -E 'Err[A-Za-z]+|NotReady.*(failed|unable|invalid|error)' <<<"${bundle_states}" || true)"
  if [[ -n "${error_state}" ]]; then
    if [[ "${error_state}" != "${last_error_state}" ]]; then
      error_since="${SECONDS}"
      last_error_state="${error_state}"
      printf '\nFleet is reconciling dependencies; allowing up to three minutes for transient errors to clear.\n' >&2
    elif (( SECONDS - error_since >= 180 )); then
      printf '\nFleet bundle error persisted for three minutes:\n%s\n' "${bundle_states}" >&2
      "${kubectl}" --kubeconfig "${kubeconfig}" -n fleet-local get gitrepos,bundles >&2 || true
      exit 1
    fi
  else
    error_since=0
    last_error_state=""
  fi

  if [[ "${all_ready}" == true ]]; then
    printf '\nFleet fetched the requested revision and all conservative-profile bundles are Ready.\n'
    "${kubectl}" --kubeconfig "${kubeconfig}" -n keycloak get pods,pvc
    "${kubectl}" --kubeconfig "${kubeconfig}" -n gitlab get pods,pvc
    exit 0
  fi

  printf '.'
  if (( SECONDS >= next_status_report )); then
    printf '\nFleet source status:\n%s\nBundle readiness:\n%s\n' "${repo_rows}" "${bundle_states}" >&2
    next_status_report=$((SECONDS + 60))
  fi
  sleep 10
done

printf '\nThe conservative platform profile did not become Ready before timeout. Current status:\n' >&2
"${kubectl}" --kubeconfig "${kubeconfig}" -n fleet-local get gitrepos,bundles >&2 || true
"${kubectl}" --kubeconfig "${kubeconfig}" -n keycloak get pods,pvc >&2 || true
"${kubectl}" --kubeconfig "${kubeconfig}" -n gitlab get pods,pvc >&2 || true
exit 1
