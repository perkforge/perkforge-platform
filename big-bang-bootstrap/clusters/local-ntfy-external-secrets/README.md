# ntfy with native External Secrets

This composed root preserves the `local-ntfy` application set and enables only
Big Bang's native `addons.externalSecrets` integration. It adds no custom ESO
package and does not activate query consumers.

Before selecting this root, run the approved release's guarded
`configuration/ansible/external-secrets-inputs.yaml` and
`configuration/ansible/openbao-eso.yaml` procedures. Supply operator-owned
registry, public CA, provider network and auth inputs; do not put credentials or
physical endpoints in this root. The auth baseline is create-only: do not rerun
it after adding separately approved consumer roles.

Publish and verify an immutable Git commit, then select this path with that
commit in the cluster's Flux source. Confirm the native controller is Ready and
existing apps remain healthy. Secret delivery is a separate scoped consumer
step; controller readiness alone does not prove synchronization.
