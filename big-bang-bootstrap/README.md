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

## Current physical target and reusable stages

Earlier roots remain reusable installation building blocks, not the current target
selection. The physical target has advanced to scoped logging and Mattermost
composition, with Viewer-only Portal log access selected separately. Do not
reapply the earlier integrated pilot to add features. Always inspect the exact
selected source/path before serializing a new reviewed pin.

The [current handoff](../HANDOFF.md#current-scoped-observability-checkpoint-2026-11-14)
separates actual cluster-wide discovery, scoped OpenBao/ESO custody, platform
queries and controlled Viewer denial proof from actual human-login/lifecycle, durable
transport/replay and full alert recovery acceptance. Grafana/Prometheus, Portal,
Nextcloud and Mattermost are preserved. Native Big Bang/Registry One images and
reviewed target values remain the BODA path; no environment-specific rebuild.

Portal's published v0.7.0/configuration v2.3.3 C4 baseline is not yet a live image
selection. Final current-state modeling and coordinated release pins remain
underway; preserve compiled-asset authentication and disabled tenant-request
preview inputs. Do not infer acceptance from an image release or Ready pod.

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
