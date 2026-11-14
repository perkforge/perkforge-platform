# Big Bang bootstrap

One named cluster root composes authored values. Ansible bootstraps/configures; Flux reconciles Big Bang. Infrastructure Ansible owns host/RKE2; platform Ansible owns gated Rancher API configuration; optional Longhorn/Rancher Helm deployments belong to Big Bang/Flux, enrollment Git owns tenant foundations and registration, and app Git owns tenant deployments.

```text
clusters/local/                    physical target: values and identity inputs
enrollments/                       optional external enrollment wiring/prerequisites
profiles/il2/                      illustrative selection and existing guardrails
providers/rke2/                    distribution-specific values
configuration/
  defaults/                        shared authored values
  packages/                        umbrella, package values, realm and prerequisites
  identity/                        cross-system OIDC, trust, user access and routing
  ansible/                         default-off bootstrap/configuration/readiness
tests/                             configuration/bootstrap/security/integration
```

## Current physical pilot and reusable stages

The default `local` and earlier stage roots remain reusable installation building
blocks, not a statement of the current target selection. As verified on
2026-11-14, the physical target selects `local-integrated-logging` on Big Bang
3.35.1. It preserves Portal, Nextcloud, Mattermost, authenticated Grafana/Prometheus
query access and native notification routing while adding scoped Loki/Alloy.
Use the [current handoff](../HANDOFF.md#verified-integrated-pilot-snapshot-2026-11-14)
and [logging acceptance/runbook](configuration/observability/integrated-logging/README.md)
for deployed evidence versus remaining acceptance. The old v0.14.0 Keycloak-only
selection is historical, not the current runtime.

Grafana SSO, ntfy contact points and the Mattermost baseline are deployed; this
does not close the broader alert lifecycle/tenant work in #39, unresolved host
collector coverage in #383, or full logging acceptance in #38. Portal's read-only
enrollment baseline and final Portal v0.6.1 architecture-auth release are live
through platform `947f99cc`, enrollment v2.5.2 and configuration v2.3.2. The
[current handoff](../HANDOFF.md#mattermost-and-portal-baseline) records actual
anonymous asset/API denial and exact-artifact isolated browser checks; fresh
signed-in owner-browser acceptance remains pending. This supersedes the earlier
same-day publication-only checkpoint, not the remaining Portal #12/#10 criteria.
Do not infer deployment from a PR, release or offline render. Keep the same pinned images/charts across environments
and vary reviewed configuration only (BODA).

See [ordered app stages](configuration/ansible/README.md#ordered-app-stages)
for installation and acceptance boundaries. Never rerun initial bootstrap or
choose an older root to add a component to the active cluster. Promote only the
reviewed composition that preserves its existing applications. This physical
three-node pilot is not HA or an IL2 authorization claim.

Start with [platform maintenance](../docs/platform/README.md): [applications and values](../docs/platform/applications.md), [targets/environments](../docs/platform/targets.md), and [impact profiles](../docs/platform/profiles.md). Use [operation order](configuration/ansible/README.md), [verification commands](tests/README.md), [infrastructure prerequisites](../infrastructure/README.md).

Entrypoint: inventory gitops_path → paused Flux seed → clusters/<name>/kustomization.yaml → umbrella ordered valuesFrom → pinned child releases. Kustomize composition is not readiness. No merge, directory copy or successful offline render authorizes live activation.

Prepared storage/management inputs and activation boundaries are documented in
[Longhorn](configuration/packages/longhorn/README.md) and
[Rancher](configuration/packages/rancher/README.md). Nothing is bootstrapped by
adding or rendering these files.

For Longhorn activation, publish this source as a new release, select its verified
tag as runtime input, prepare the paused seed and installer foundations, then
separately approve seed resume. See [release and seed activation](configuration/ansible/README.md#longhorn-only-release-and-seed-activation).

Flux installation requires the pinned Iron Bank image-pull credential. The supported bootstrap stages its namespace and separately gated Secret delivery before controllers; existing Secrets can be reused without a local credential file. See the protected-input and repeat procedure in [platform operations](configuration/ansible/README.md#repeatable-flux-registry-preparation).

The default-off [Velero local baseline](configuration/packages/velero/README.md)
adds a dedicated small Longhorn-backed Garage instance, configurable scheduled
backups and an isolated copied-data exercise. It preserves the existing Grafana/
Harbor composition. This local PoC is not independent disaster recovery; AWS
values remain configurable. No host quota or reservation changes are required.
