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

command -v curl >/dev/null 2>&1 || { echo "curl is required for the Keycloak ingress health check." >&2; exit 1; }
export GIT_TERMINAL_PROMPT=0
export GCM_INTERACTIVE=never

expected_commit="${FLEET_EXPECTED_COMMIT:-}"
if [[ -z "${expected_commit}" ]]; then
  git -C "${repo_root}" fetch --quiet origin main || {
    echo "Could not fetch origin/main; refusing to apply Fleet GitRepos." >&2
    exit 1
  }
  expected_commit="$(git -C "${repo_root}" rev-parse FETCH_HEAD)"
fi
git -C "${repo_root}" diff --quiet "${expected_commit}" -- local-lab/fleet || {
  echo "Local Fleet files differ from the revision Fleet will deploy (${expected_commit})." >&2
  exit 1
}
untracked_fleet_files="$(git -C "${repo_root}" ls-files --others --exclude-standard -- local-lab/fleet)"
[[ -z "${untracked_fleet_files}" ]] || {
  echo "Untracked Fleet files exist; publish the intended configuration before deploying." >&2
  exit 1
}

platform_apps_repo="${repo_root}/local-lab/fleet/gitrepos/platform-apps.yaml"
monitoring_enabled=false
opencost_enabled=false
if grep -Eq '^[[:space:]]*-[[:space:]]*local-lab/fleet/bundles/prometheus-grafana([[:space:]]|$)' \
  "${platform_apps_repo}"; then
  monitoring_enabled=true
fi
if grep -Eq '^[[:space:]]*-[[:space:]]*local-lab/fleet/bundles/opencost([[:space:]]|$)' \
  "${platform_apps_repo}"; then
  opencost_enabled=true
fi
if [[ "${opencost_enabled}" == true && "${monitoring_enabled}" != true ]]; then
  echo "OpenCost requires the prometheus-grafana Fleet path to be enabled." >&2
  exit 1
fi

"${repo_root}/local-lab/scripts/prepare-platform-secrets.sh"
if [[ "${monitoring_enabled}" == true ]]; then
  bash "${repo_root}/local-lab/scripts/prepare-observability-secrets.sh"
fi
"${kubectl}" --kubeconfig "${kubeconfig}" apply -f \
  "${repo_root}/local-lab/fleet/gitrepos/local-lab.yaml" \
  -f "${repo_root}/local-lab/fleet/gitrepos/platform-apps.yaml"

expected_bundles=(
  local-lab-storage
  local-lab-tenant-foundation
  local-lab-cnpg-operator
  local-lab-keycloak-database
  local-lab-keycloak
  local-lab-gitlab-database
  local-lab-gitlab-valkey
)
if [[ "${monitoring_enabled}" == true ]]; then
  expected_bundles+=(local-lab-prometheus-grafana)
fi
if [[ "${opencost_enabled}" == true ]]; then
  expected_bundles+=(local-lab-opencost)
fi
deadline=$((SECONDS + 1800))
error_since=0
last_error_state=""
next_status_report=$((SECONDS + 60))

printf 'Waiting for Fleet to fetch %s and ready %s enabled-profile bundles' \
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
    printf '\nFleet fetched the requested revision and all enabled profile bundles are Ready.\n'
    if [[ "${monitoring_enabled}" == true ]]; then
      printf 'Waiting for Prometheus, kube-state-metrics, and Grafana workloads.\n'
      for selector in \
        'app.kubernetes.io/name=prometheus' \
        'app.kubernetes.io/name=kube-state-metrics' \
        'app.kubernetes.io/name=grafana'; do
        "${kubectl}" --kubeconfig "${kubeconfig}" -n monitoring wait \
          --for=condition=Ready pods -l "${selector}" --timeout=10m
      done
    fi
    if [[ "${opencost_enabled}" == true ]]; then
      printf 'Waiting for OpenCost workloads.\n'
      "${kubectl}" --kubeconfig "${kubeconfig}" -n opencost wait \
        --for=condition=Ready pods -l app.kubernetes.io/name=opencost --timeout=10m
    fi
    printf 'Waiting for Keycloak, its database, GitLab database, and Valkey pods to become Ready.\n'
    "${kubectl}" --kubeconfig "${kubeconfig}" -n keycloak wait --for=condition=Ready pods --all --timeout=10m
    "${kubectl}" --kubeconfig "${kubeconfig}" -n gitlab wait --for=condition=Ready pods --all --timeout=10m

    valkey_pod="$("${kubectl}" --kubeconfig "${kubeconfig}" -n gitlab get pods \
      -l app.kubernetes.io/instance=valkey -o jsonpath='{.items[0].metadata.name}')"
    [[ -n "${valkey_pod}" ]] || { echo "No Valkey pod found with the expected Helm release label." >&2; exit 1; }
    valkey_response=""
    for attempt in $(seq 1 12); do
      valkey_response="$("${kubectl}" --kubeconfig "${kubeconfig}" -n gitlab exec "pod/${valkey_pod}" -- valkey-cli ping 2>/dev/null || true)"
      [[ "${valkey_response}" == "PONG" ]] && break
      sleep 5
    done
    [[ "${valkey_response}" == "PONG" ]] || { echo "Valkey PING returned '${valkey_response}', expected PONG." >&2; exit 1; }
    printf 'Valkey protocol check: PONG.\n'

    printf 'Checking Keycloak through the node ingress.\n'
    keycloak_ready=false
    for attempt in $(seq 1 60); do
      if curl --silent --show-error --fail --max-time 5 \
        --resolve keycloak.local-lab.test:80:192.168.122.201 \
        http://keycloak.local-lab.test/auth/ -o /dev/null 2>/dev/null; then
        keycloak_ready=true
        break
      fi
      sleep 5
    done
    [[ "${keycloak_ready}" == true ]] || { echo "Keycloak ingress did not respond successfully after five minutes." >&2; exit 1; }
    printf 'Keycloak ingress check: HTTP response received.\n'
    python3 "${repo_root}/local-lab/scripts/configure-keycloak-tenants.py" --apply \
      --kubectl "${kubectl}" --kubeconfig "${kubeconfig}"
    python3 "${repo_root}/local-lab/scripts/configure-rancher-oidc.py" --apply \
      --kubectl "${kubectl}" --kubeconfig "${kubeconfig}"
    python3 "${repo_root}/local-lab/scripts/reconcile-tenant-rancher-bindings.py" --apply \
      --kubectl "${kubectl}" --kubeconfig "${kubeconfig}"

    printf 'Running tenant authorization, admission, quota, and network verification.\n'
    python3 "${repo_root}/local-lab/scripts/verify-tenant-rbac.py" \
      --kubectl "${kubectl}" --kubeconfig "${kubeconfig}"
    python3 "${repo_root}/local-lab/scripts/verify-tenant-admission.py" --apply \
      --kubectl "${kubectl}" --kubeconfig "${kubeconfig}"
    python3 "${repo_root}/local-lab/scripts/verify-tenant-quota.py" --apply \
      --kubectl "${kubectl}" --kubeconfig "${kubeconfig}"
    python3 "${repo_root}/local-lab/scripts/verify-tenant-network.py" --apply \
      --kubectl "${kubectl}" --kubeconfig "${kubeconfig}"
    if [[ "${monitoring_enabled}" == true ]]; then
      python3 "${repo_root}/local-lab/scripts/verify-tenant-observability.py" --apply \
        --kubectl "${kubectl}" --kubeconfig "${kubeconfig}"
    fi

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
