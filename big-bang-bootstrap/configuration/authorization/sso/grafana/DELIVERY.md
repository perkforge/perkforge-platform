# Dedicated Grafana OAuth inputs (source only)

`ansible-playbook deliver-inputs.yaml` is default-off. Check mode, even with run
requested, neither contacts Kubernetes nor reads private files. No root selects
this entrypoint. The existing Grafana package and native OAuth settings do not
change; this is not activation or owner login acceptance.

## Separate approval and exact inputs

Use a clean reviewed/published source, the established owner kubeconfig and a
protected variables file (not secrets in shell arguments). Before a live run,
approve transmission of the specific existing client credential to
`monitoring/grafana-oidc-client` and the public CA to
`monitoring/grafana-identity-ca`. Grant/persistent-access approval is not implied
by source review or the approval string. No secret is generated or obtained from
Keycloak; client preparation and its credential agreement are separate gates.

Required variables:

- `grafana_delivery_run: true` and
  `grafana_delivery_approval: grafana-sso-input-delivery-v1`.
- Absolute `grafana_kubectl`, `grafana_kubeconfig`, explicit `grafana_context`,
  HTTPS `grafana_expected_api`, and exact namespace UIDs
  `grafana_expected_cluster_uid` (kube-system) and
  `grafana_expected_monitoring_uid` (monitoring), independently verified first.
- Absolute `grafana_client_secret_file`: existing operator-owned 0600 regular
  file with the exact separately prepared Grafana confidential-client secret.
- Absolute `grafana_ca_file`: one public CA certificate, no private key; pin its
  exact file SHA256 as `grafana_expected_ca_sha256` after independent validation.
  The source checks parseability, CA:TRUE and at least one day of validity, not
  the complete issuer/TLS path. Discovery and actual Grafana TLS remain separate.

The kubeconfig and secret must have operator-owned 0700 parent directories; the kubeconfig must be operator-owned 0600; symlink inputs, insecure Kubernetes
TLS and configured proxy URLs are refused. Use the established trusted config,
not a new executable credential plugin. Calls are limited to config metadata,
those two namespace UIDs and those two exact named objects. Named Secret content
is read only to verify ownership and byte equality; no broad Secret list/read or
admin/registry credential access is performed. The credential goes over private
stdin, never argv or normal Ansible output. Run without debug/callback tracing.

Both objects are immutable, with owner label `perkforge.io/owner: grafana-sso-v1`.
The Secret is Opaque with exactly `GRAFANA_OIDC_CLIENT_SECRET`; the public
ConfigMap contains exactly `ca.crt`, matching the existing pinned native mount
contract. All collisions and terminating objects are checked before either create. Every absent object must pass server dry-run before either is persisted. Existing exact owned
objects permit a no-change rerun or resume after partial creation. Foreign,
mutable, mismatched or rotated inputs stop without replacement. A race or failed
readback stops, leaves evidence/resources intact and requires inspection; no
automatic delete/rollback is attempted. Rotation needs a separately reviewed
versioned replacement and workload/source change.

This entrypoint grants no RBAC, creates no namespace, and never patches a
Deployment, HelmRelease, source root, TLS route, claim, datasource or dashboard.
It preserves existing monitoring and local Grafana recovery. Keeping the client
and native OAuth disabled is mandatory until a paired own-client claim/role
policy and account-linking/recovery behavior are reviewed. Tenant, engineer and
viewer access are not approved here. Later source selection must verify the
pinned chart, deployment effects, exact existing identities and rollback before
separate activation and positive/denied/session acceptance.
