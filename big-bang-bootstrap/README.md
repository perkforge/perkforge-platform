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

Local selects only Longhorn, with active outer/child Helm desired state behind a paused, release-pinned seed. Headlamp is disabled in shared defaults; Headlamp, Keycloak, Rancher, OpenBao and tenant enrollment are unselected. Start with storage acceptance, then select Rancher with its own TLS/bootstrap inputs; defer identity/SSO and tenant activation. Publication does not select a release or resume the paused seed. Local means the physical three-node cluster. Actual IL2 preparation is deferred.

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
