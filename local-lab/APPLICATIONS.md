# PerkForge Platform application plan

This catalog covers the disposable development harness under `local-lab/` and
the eventual three-node physical homelab. PerkForge Platform is a functional,
secure, multi-tenant Kubernetes PaaS reference implementation and engineering
portfolio. The initial real operator is one person; synthetic tenants are used
to exercise genuine tenant lifecycle and security boundaries. The VM harness
currently has two 2-vCPU, 4-GiB RHEL VMs, so heavier applications should be
enabled in stages while preserving the intended platform capabilities.

## Local foundation

| Capability | Local implementation | State |
| --- | --- | --- |
| Kubernetes | RKE2 on the disposable RHEL VMs | Deployed |
| Cluster management | Rancher | Deployed |
| GitOps | Fleet, managed by Rancher | Deployed |
| Local persistent volumes | Rancher local-path provisioner | Deployed; node-local only |
| Collaboration | Mattermost with CloudNativePG | Bundle available; excluded from the conservative profile |
| Tenant namespace controls | Two demo namespaces with scoped RBAC, restricted Pod Security, quotas, and default-deny network policies | Deployed by Fleet |

The Fleet source is split into two `GitRepo` resources: `local-lab` for the
cluster foundation and `platform-apps` for enabled application bundles. Each
resource has its own tracked path list, keeping infrastructure dependencies
separate from the apps being exercised.

The tenant demo uses placeholder Kubernetes groups `tenant-alpha-users` and
`tenant-bravo-users`. An identity provider and Rancher/Kubernetes group mapping
must be configured before real people can use those bindings. Network policies
also depend on enforcement by the cluster CNI. These namespace controls are a
teaching baseline, not a hard isolation boundary between hostile tenants.

## Application catalog

| Capability | Candidate implementation | Local harness approach |
| --- | --- | --- |
| Identity and SSO | Keycloak | Active in the conservative Fleet profile; OIDC integration with Rancher and GitLab is a follow-up |
| Source control and CI | GitLab | PostgreSQL and Valkey dependencies are active; the GitLab application bundle is disabled until memory headroom is reviewed |
| Collaboration | Mattermost | Bundle available as an opt-in integration; disabled in the conservative profile |
| Metrics and dashboards | Prometheus and Grafana | Add as a staged observability bundle |
| Pod log collection | Grafana Alloy with Loki | Pair Alloy with a log backend; Alloy alone does not retain/query logs |
| Traces | Grafana Tempo | Optional observability extension after metrics and logs |
| Code quality | SonarQube | Optional; evaluate its memory and persistent-storage needs before enabling |
| Vulnerability and configuration scanning | Trivy, optionally Trivy Operator | Start with CI or on-demand scans; cluster-wide scanning can increase resource use |
| Container and artifact registry | Harbor **or** Sonatype Nexus Repository | Harbor is installed outside the active Fleet profile; a prior upgrade OOM-killed its database. Nexus remains an alternative profile |
| Secrets management | HashiCorp Vault **or** OpenBao | Select one per deployment; keep the app-facing secret integration documented separately from the provider choice |
| Policy enforcement | Kyverno | Add policies alongside tenant tests; keep policy report/enforce behavior explicit |
| Certificates | cert-manager | Already installed as a Rancher prerequisite; revisit as a shared platform service |
| Storage and recovery | local-path for learning; evaluate Longhorn or another supported backend later | Current data is tied to a VM disk and is not highly available or backed up |

The intended pattern is one tested default for each capability, with explicit
alternatives where licensing or operator choice matters. Harbor and Nexus, and
Vault and OpenBao, are alternatives rather than services that need to run
simultaneously. The current conservative local profile enables Keycloak and the
GitLab database/Valkey dependencies. The GitLab application, Harbor Fleet
bundle, and Mattermost remain available as opt-in paths until the VM resource
profile is increased or measured headroom supports them. The `paths` list in
[`fleet/gitrepos/platform-apps.yaml`](fleet/gitrepos/platform-apps.yaml) is the
active local app profile: adding a bundle path enables it, and removing a path
tells Fleet to stop managing that bundle. Keep the profile and bundle versions
in Git so each test run is reproducible. For alternatives, include exactly one
provider's bundle path at a time. The separate
[`fleet/gitrepos/local-lab.yaml`](fleet/gitrepos/local-lab.yaml) GitRepo owns
local infrastructure and tenant foundation bundles.

## Staged build order

1. Publish and verify the tenant-foundation Fleet bundle, including policy
   enforcement and the placeholder group bindings.
2. Bring up Keycloak, GitLab, and Harbor as the local platform baseline. Then
   integrate Keycloak OIDC, enable a suitably small GitLab Runner, and test
   tenant groups, RBAC, and image pushes to Harbor.
3. Add metrics, logs, scanning, and code-quality bundles as separately
   switchable capabilities; test useful combinations rather than requiring the
   whole catalog to run at once.
4. Add Nexus and Vault/OpenBao alternatives as separate selectable bundles,
   and verify each supported choice through the same integration contracts.
5. Profile GitLab and other resource-heavy apps on the current VM footprint.
   The small harness is a constraint to account for in test profiles, not a
   reason to make those capabilities permanently unavailable.

## Scope boundary

The immediate target is the local VM harness, followed by the three-node
ThinkCentre RKE2 cluster. EKS, AKS, and multiple production environments are
not active implementation targets. Preserve portable, reproducible patterns
where practical and avoid unnecessary dependencies on a particular machine.
Commercial billing, subscriptions, and public customer onboarding are outside
the reference implementation's scope.

Keep the complete PaaS capability set in scope, including identity, CI/CD,
registry, GitOps, observability, secrets, storage, lifecycle operations, and
tenant provisioning/offboarding. Implement services in stages to fit current
resources; stage order is not a reduction in the target architecture. Connect
working controls to repeatable verification, evidence, findings, and risk
remediation. Design for the three physical nodes and measure their resources
before deciding whether memory or storage needs an upgrade.
