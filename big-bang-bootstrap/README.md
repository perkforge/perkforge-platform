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

The default local root selects Longhorn, Rancher and OpenBao. The reviewed
stage roots add Headlamp, then Keycloak and its database from the **same release**.
Publication alone does not promote the live source. The last recorded deployment
is v0.12.0 (Rancher/Longhorn); OpenBao, Headlamp, Keycloak and identity integration
are not deployed. See [ordered app stages](configuration/ansible/README.md#ordered-app-stages)
for approval and acceptance boundaries. Initial seeds remain paused; never rerun
bootstrap on the active cluster. This physical three-node lab is not HA or an IL2
authorization claim.

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
