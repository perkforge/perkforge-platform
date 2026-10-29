#!/usr/bin/env bash
# Deliver only the reviewed issued leaf and public CA; never the Issuer's CA key.
set -euo pipefail
set +x
if [[ ${1:-} != --apply || $# != 3 ]]; then
  echo 'Plan only. After approval: deliver-tls.sh --apply /path/kubectl /private/rke2.yaml'
  exit 0
fi
kubectl_path=$2
kubeconfig_path=$3
k() { "$kubectl_path" --kubeconfig "$kubeconfig_path" --context default --request-timeout=20s "$@"; }
umask 077
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
k get certificate openbao-lab -n cattle-system -o json > "$work/certificate.json"
jq -e '.spec.secretName == "openbao-lab-issued" and .spec.issuerRef.name == "rancher" and .spec.issuerRef.kind == "Issuer" and any(.status.conditions[]; .type == "Ready" and .status == "True")' "$work/certificate.json" >/dev/null
# Only the Certificate-named leaf is read; no lookup of the Issuer Secret.
k get secret openbao-lab-issued -n cattle-system -o json > "$work/issued.json"
jq -e '.type == "kubernetes.io/tls" and (.data | has("tls.crt") and has("tls.key") and has("ca.crt"))' "$work/issued.json" >/dev/null
for key in tls.crt tls.key ca.crt; do
  jq -r --arg key "$key" '.data[$key]' "$work/issued.json" | base64 -d > "$work/$key"
done
openssl verify -CAfile "$work/ca.crt" -verify_hostname openbao.openbao.svc "$work/tls.crt" >/dev/null
openssl x509 -in "$work/tls.crt" -checkhost openbao.local-lab.test -noout >/dev/null
# Preflight every destination before writing anything: no unowned adoption.
for spec in 'secret:openbao:openbao-server-tls' 'configmap:openbao:openbao-ca' 'configmap:tenant-home-portal:openbao-ca'; do
  IFS=: read -r kind namespace name <<<"$spec"
  k get "$kind" "$name" -n "$namespace" --ignore-not-found -o json > "$work/existing.json"
  if [[ -s $work/existing.json ]]; then
    jq -e '.metadata.labels["platform.perkforge.io/managed-by"] == "openbao-operator"' "$work/existing.json" >/dev/null || { echo 'Refusing unowned TLS destination' >&2; exit 1; }
  fi
done
# Secret input stays in files/stdin. Only leaf key/cert enter the OpenBao namespace.
k create secret tls openbao-server-tls -n openbao --cert="$work/tls.crt" --key="$work/tls.key" --dry-run=client -o json |
  jq '.metadata.labels={"platform.perkforge.io/managed-by":"openbao-operator"}' | k apply -f - >/dev/null
for namespace in openbao tenant-home-portal; do
  k create configmap openbao-ca -n "$namespace" --from-file=ca.crt="$work/ca.crt" --dry-run=client -o json |
    jq '.metadata.labels={"platform.perkforge.io/managed-by":"openbao-operator"}' | k apply -f - >/dev/null
done
echo 'Delivered issued OpenBao leaf and public CA only; no CA private-key access. Repeat after leaf renewal; server reload requires verification.'
