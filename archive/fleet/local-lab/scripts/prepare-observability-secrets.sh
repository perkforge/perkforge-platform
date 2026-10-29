#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
secrets_dir="${repo_root}/.secrets"
kubectl="${secrets_dir}/kubectl"
kubeconfig="${secrets_dir}/rke2.yaml"

[[ -x "${kubectl}" && -r "${kubeconfig}" ]] || {
  echo "Missing local cluster credentials. Run the local-lab RKE2 setup first." >&2
  exit 1
}
command -v openssl >/dev/null 2>&1 || { echo "openssl is required." >&2; exit 1; }

umask 077
mkdir -p "${secrets_dir}"
chmod 0700 "${secrets_dir}"
password_file="${secrets_dir}/grafana-admin-password"
if [[ ! -s "${password_file}" ]]; then
  if "${kubectl}" --kubeconfig "${kubeconfig}" -n monitoring \
    get secret grafana-admin -o 'jsonpath={.data.admin-password}' 2>/dev/null \
    | base64 --decode > "${password_file}" && [[ -s "${password_file}" ]]; then
    :
  else
    rm -f "${password_file}"
    openssl rand -hex 32 > "${password_file}"
  fi
fi
chmod 0600 "${password_file}"

"${kubectl}" --kubeconfig "${kubeconfig}" create namespace monitoring \
  --dry-run=client -o yaml | "${kubectl}" --kubeconfig "${kubeconfig}" apply -f - >/dev/null

secret_env="$(mktemp "${secrets_dir}/grafana-secret.XXXXXX")"
trap 'rm -f "${secret_env}"' EXIT
printf 'admin-user=admin\nadmin-password=%s\n' "$(cat "${password_file}")" > "${secret_env}"
"${kubectl}" --kubeconfig "${kubeconfig}" -n monitoring create secret generic grafana-admin \
  --from-env-file="${secret_env}" --dry-run=client -o yaml \
  | "${kubectl}" --kubeconfig "${kubeconfig}" apply -f - >/dev/null

echo "Grafana admin credentials are stored owner-only under .secrets/; values were not printed."
