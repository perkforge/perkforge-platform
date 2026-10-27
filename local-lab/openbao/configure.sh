#!/usr/bin/env bash
# Explicit operator action after initialization/unseal and reviewed live approval.
# Native bao CLI configuration only: no credential issuance or secret migration.
set -euo pipefail
set +x
if [[ ${1:-} != --apply || $# != 3 ]]; then
  echo 'Plan only. After approval: configure.sh --apply /private/openbao-client-secret /public/lab-ca.pem'
  exit 0
fi
: "${BAO_ADDR:?Use the reviewed HTTPS OpenBao address}"
[[ $BAO_ADDR == https://* && ${BAO_SKIP_VERIFY:-false} != true && ${VAULT_SKIP_VERIFY:-false} != true ]] || { echo 'Verified HTTPS is required' >&2; exit 1; }
secret_file=$2
ca_file=$3
[[ -f $secret_file && ! -L $secret_file && -s $secret_file && $(stat -c %a "$secret_file") == 600 && $(stat -c %u "$secret_file") == "$(id -u)" ]] || { echo 'Client secret must be an owned mode-600 regular file' >&2; exit 1; }
[[ -f $ca_file && ! -L $ca_file && -s $ca_file ]] || { echo 'Public CA file is required' >&2; exit 1; }
export BAO_CACERT=$ca_file
config_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# Use a preapproved operator session (CLI token helper or BAO_TOKEN). Never log it.
quiet() { if ! "$@" >/dev/null 2>/dev/null; then echo "OpenBao operation failed: $1 $2 (sensitive output suppressed)" >&2; exit 1; fi; }
mounts=$(bao secrets list -format=json)
for mount in platform tenants; do
  if jq -e --arg key "$mount/" 'has($key)' <<<"$mounts" >/dev/null; then
    jq -e --arg key "$mount/" '.[$key].type == "kv" and .[$key].options.version == "2"' <<<"$mounts" >/dev/null || { echo 'Existing mount conflicts; refusing conversion' >&2; exit 1; }
  else
    quiet bao secrets enable -path="$mount" -version=2 kv
  fi
done
auths=$(bao auth list -format=json)
for spec in oidc:oidc kubernetes:kubernetes; do
  path=${spec%:*}; type=${spec#*:}
  if jq -e --arg key "$path/" 'has($key)' <<<"$auths" >/dev/null; then
    jq -e --arg key "$path/" --arg type "$type" '.[$key].type == $type' <<<"$auths" >/dev/null || { echo 'Existing auth mount conflicts' >&2; exit 1; }
  else
    quiet bao auth enable -path="$path" "$type"
  fi
done
for policy in "$config_root"/policies/*.hcl; do
  quiet bao policy write "$(basename "$policy" .hcl)" "$policy"
done
quiet bao write auth/oidc/config \
  oidc_discovery_url=https://keycloak.local-lab.test/auth/realms/perkforge \
  oidc_client_id=openbao oidc_client_secret=@"$secret_file" oidc_discovery_ca_pem=@"$ca_file" \
  default_role=
quiet bao write auth/oidc/role/home @"$config_root/roles/human-home.json"
quiet bao write auth/oidc/role/platform @"$config_root/roles/human-platform.json"
quiet bao write auth/kubernetes/config @"$config_root/config/kubernetes.json"
quiet bao write auth/kubernetes/role/eso-home-portal @"$config_root/roles/eso-home-portal.json"
echo 'Applied reviewed mounts, policies and auth configuration. No initialization, user grant or app secret migration performed.'
