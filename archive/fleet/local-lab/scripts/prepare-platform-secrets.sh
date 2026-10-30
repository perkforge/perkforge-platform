#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
secrets_dir="${repo_root}/.secrets"
kubectl="${secrets_dir}/kubectl"
kubeconfig="${secrets_dir}/rke2.yaml"

[[ -x "${kubectl}" && -r "${kubeconfig}" ]] || {
  echo "Missing local-lab kubectl or kubeconfig under .secrets/." >&2
  exit 1
}
command -v openssl >/dev/null 2>&1 || { echo "openssl is required." >&2; exit 1; }
chmod 0700 "${secrets_dir}"
umask 077

credential() {
  local name="$1" namespace="$2" secret="$3" key="$4"
  local file="${secrets_dir}/${name}"
  if [[ ! -s "${file}" ]]; then
    if "${kubectl}" --kubeconfig "${kubeconfig}" -n "${namespace}" \
      get secret "${secret}" -o "jsonpath={.data.${key}}" 2>/dev/null | base64 --decode > "${file}" && [[ -s "${file}" ]]; then
      :
    else
      rm -f "${file}"
      openssl rand -hex 24 > "${file}"
    fi
  fi
  chmod 0600 "${file}"
}

for namespace in keycloak gitlab harbor; do
  "${kubectl}" --kubeconfig "${kubeconfig}" create namespace "${namespace}" \
    --dry-run=client -o yaml | "${kubectl}" --kubeconfig "${kubeconfig}" apply -f - >/dev/null
done

credential keycloak-db-password keycloak keycloak-db-app password
credential keycloak-admin-password keycloak keycloak-admin password
credential gitlab-db-password gitlab gitlab-db-app password
credential harbor-admin-password harbor harbor-admin HARBOR_ADMIN_PASSWORD

for entry in 'keycloak keycloak-db-app keycloak keycloak-db-password' \
  'gitlab gitlab-db-app gitlab gitlab-db-password'; do
  read -r namespace name username password_file <<<"${entry}"
  env_file="$(mktemp "${secrets_dir}/platform-secret.XXXXXX")"
  printf 'username=%s\npassword=%s\n' "${username}" "$(cat "${secrets_dir}/${password_file}")" > "${env_file}"
  "${kubectl}" --kubeconfig "${kubeconfig}" -n "${namespace}" create secret generic "${name}" \
    --from-env-file="${env_file}" --dry-run=client -o yaml \
    | "${kubectl}" --kubeconfig "${kubeconfig}" apply -f - >/dev/null
  rm -f "${env_file}"
done

keycloak_env_file="$(mktemp "${secrets_dir}/platform-secret.XXXXXX")"
printf 'password=%s\n' "$(cat "${secrets_dir}/keycloak-admin-password")" > "${keycloak_env_file}"
"${kubectl}" --kubeconfig "${kubeconfig}" -n keycloak create secret generic keycloak-admin \
  --from-env-file="${keycloak_env_file}" --dry-run=client -o yaml \
  | "${kubectl}" --kubeconfig "${kubeconfig}" apply -f - >/dev/null
rm -f "${keycloak_env_file}"

"${kubectl}" --kubeconfig "${kubeconfig}" -n harbor create secret generic harbor-admin \
  --from-literal="HARBOR_ADMIN_PASSWORD=$(cat "${secrets_dir}/harbor-admin-password")" \
  --dry-run=client -o yaml | "${kubectl}" --kubeconfig "${kubeconfig}" apply -f - >/dev/null

echo "Platform namespaces and local-only chart credentials are ready."
