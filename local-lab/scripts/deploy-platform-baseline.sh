#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
secrets_dir="${repo_root}/.secrets"
kubeconfig="${secrets_dir}/rke2.yaml"
kubectl="${secrets_dir}/kubectl"
helm="${secrets_dir}/bin/helm"

if [[ ! -x "${kubectl}" || ! -x "${helm}" || ! -r "${kubeconfig}" ]]; then
  echo "Missing local-lab kubectl, Helm, or kubeconfig under .secrets/." >&2
  exit 1
fi
if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl is required to generate local-only credentials." >&2
  exit 1
fi

chmod 0700 "${secrets_dir}"
"${kubectl}" --kubeconfig "${kubeconfig}" get nodes
"${repo_root}/local-lab/scripts/prepare-platform-secrets.sh"

release_status() {
  local namespace="$1" release="$2"
  if ! "${helm}" --kubeconfig "${kubeconfig}" -n "${namespace}" status "${release}" >/dev/null 2>&1; then
    printf 'absent'
    return
  fi
  "${helm}" --kubeconfig "${kubeconfig}" -n "${namespace}" status "${release}" \
    | awk -F': ' '/^STATUS:/ { print $2; exit }'
}

require_installable_release() {
  local namespace="$1" release="$2" status
  status="$(release_status "${namespace}" "${release}")"
  case "${status}" in
    absent) return 0 ;;
    deployed)
      echo "${release} in ${namespace} is already deployed; leaving it untouched."
      return 1
      ;;
    *)
      echo "${release} in ${namespace} has Helm status '${status}'. Stopping for review; no release or data will be removed." >&2
      exit 1
      ;;
  esac
}

"${kubectl}" --kubeconfig "${kubeconfig}" apply -f \
  "${repo_root}/local-lab/fleet/bundles/keycloak-db/cluster.yaml"
"${kubectl}" --kubeconfig "${kubeconfig}" apply -f \
  "${repo_root}/local-lab/fleet/bundles/gitlab-dependencies/cluster.yaml"

"${helm}" repo add codecentric https://codecentric.github.io/helm-charts --force-update
"${helm}" repo add harbor https://helm.goharbor.io --force-update
"${helm}" repo add gitlab https://charts.gitlab.io --force-update
"${helm}" repo add valkey https://valkey.io/valkey-helm/ --force-update
"${helm}" repo update

echo "Waiting for Keycloak and GitLab PostgreSQL clusters."
"${kubectl}" --kubeconfig "${kubeconfig}" -n keycloak wait \
  --for=condition=Ready clusters.postgresql.cnpg.io/keycloak-db --timeout=10m
"${kubectl}" --kubeconfig "${kubeconfig}" -n gitlab wait \
  --for=condition=Ready clusters.postgresql.cnpg.io/gitlab-db --timeout=10m

echo "Installing the Keycloak PostgreSQL database."
if require_installable_release keycloak keycloak; then
  "${helm}" --kubeconfig "${kubeconfig}" upgrade --install keycloak codecentric/keycloakx --version 7.4.0 \
    --namespace keycloak --values "${repo_root}/local-lab/fleet/bundles/keycloak/values.yaml" \
    --wait --timeout 8m
fi

echo "Installing the Harbor container registry."
if require_installable_release harbor harbor; then
  "${helm}" --kubeconfig "${kubeconfig}" upgrade --install harbor harbor/harbor --version 1.19.2 \
    --namespace harbor --values "${repo_root}/local-lab/fleet/bundles/harbor/values.yaml" \
    --wait --timeout 15m
fi

echo "Installing Valkey for GitLab."
if require_installable_release gitlab valkey; then
  "${helm}" --kubeconfig "${kubeconfig}" upgrade --install valkey valkey/valkey --version 0.12.0 \
    --namespace gitlab \
    --values "${repo_root}/local-lab/fleet/bundles/gitlab-dependencies/valkey-values.yaml" \
    --wait --timeout 10m
fi

echo "Installing the reduced-footprint GitLab profile."
if require_installable_release gitlab gitlab; then
  "${helm}" --kubeconfig "${kubeconfig}" upgrade --install gitlab gitlab/gitlab --version 10.5.1 \
    --namespace gitlab --values "${repo_root}/local-lab/fleet/bundles/gitlab/values.yaml" \
    --wait --timeout 30m
fi

if "${kubectl}" --kubeconfig "${kubeconfig}" -n gitlab get secret gitlab-gitlab-initial-root-password >/dev/null 2>&1; then
  umask 077
  "${kubectl}" --kubeconfig "${kubeconfig}" -n gitlab \
    get secret gitlab-gitlab-initial-root-password \
    -o jsonpath='{.data.password}' | base64 --decode > "${secrets_dir}/gitlab-root-password"
  chmod 0600 "${secrets_dir}/gitlab-root-password"
fi

echo "Workloads currently present in the platform namespaces:"
"${kubectl}" --kubeconfig "${kubeconfig}" -n keycloak get pods,ingress,pvc
"${kubectl}" --kubeconfig "${kubeconfig}" -n harbor get pods,ingress,pvc
"${kubectl}" --kubeconfig "${kubeconfig}" -n gitlab get pods,ingress,pvc
echo "Credentials are stored owner-only in .secrets/. No password values were printed."
