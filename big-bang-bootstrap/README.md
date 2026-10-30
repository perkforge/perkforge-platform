# Big Bang bootstrap

One named cluster root composes authored values. Ansible bootstraps/configures; Flux reconciles Big Bang. Infrastructure Ansible owns RKE2/Rancher, enrollment Git owns tenant foundations and registration, and app Git owns tenant deployments.

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

Local selects Headlamp and Keycloak. OpenBao is defined but unselected. The seed, outer release and enrollment remain paused. Local means an engineer-owned physical cluster; existing trial VMs and historical release paths are not changed by this source layout. Actual IL2 preparation is deferred.

Start with [platform maintenance](../docs/platform/README.md): [applications and values](../docs/platform/applications.md), [targets/environments](../docs/platform/targets.md), and [impact profiles](../docs/platform/profiles.md). Use [operation order](configuration/ansible/README.md), [verification commands](tests/README.md), [infrastructure prerequisites](../infrastructure/README.md), and the [restructuring inventory](../docs/RESTRUCTURE-INVENTORY.md).

Entrypoint: inventory gitops_path → paused Flux seed → clusters/<name>/kustomization.yaml → umbrella ordered valuesFrom → pinned child releases. Kustomize composition is not readiness. No merge, directory copy or successful offline render authorizes live activation.
