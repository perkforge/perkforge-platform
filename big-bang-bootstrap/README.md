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

Local selects Headlamp and Keycloak. Tenant enrollment is omitted from the local root until core platform readiness; its retained source/reconciler remain suspended and require explicit later selection. OpenBao, Longhorn and Rancher are defined but unselected. Longhorn/Rancher child releases are additionally suspended. The seed, outer release and enrollment remain paused. Local means an engineer-owned physical cluster; existing trial VMs and historical release paths are not changed by this source layout. Actual IL2 preparation is deferred.

Start with [platform maintenance](../docs/platform/README.md): [applications and values](../docs/platform/applications.md), [targets/environments](../docs/platform/targets.md), and [impact profiles](../docs/platform/profiles.md). Use [operation order](configuration/ansible/README.md), [verification commands](tests/README.md), [infrastructure prerequisites](../infrastructure/README.md).

Entrypoint: inventory gitops_path → paused Flux seed → clusters/<name>/kustomization.yaml → umbrella ordered valuesFrom → pinned child releases. Kustomize composition is not readiness. No merge, directory copy or successful offline render authorizes live activation.

Prepared storage/management inputs and activation boundaries are documented in
[Longhorn](configuration/packages/longhorn/README.md) and
[Rancher](configuration/packages/rancher/README.md). Nothing is bootstrapped by
adding or rendering these files.
