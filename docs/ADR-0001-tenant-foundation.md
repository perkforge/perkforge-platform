# ADR-0001: Reconcile tenant foundations through the existing Fleet workflow

- Status: Accepted
- Date: 2026-10-23

## Context

The repository already deploys a `tenant-foundation` Fleet bundle containing
synthetic tenant namespaces, NetworkPolicies, ResourceQuotas, LimitRanges, and
Pod Security Admission labels. The implementation is being extended to
provision Rancher tenant Projects and bind Keycloak groups to Rancher project
roles. Existing namespace quota values are separate per namespace, not
aggregate tenant budgets. The current live cluster has Rancher 2.15.2 and RKE2
Kubernetes 1.36.5; Keycloak OIDC is not enabled and the two synthetic tenant
Projects are not present.

The platform needs a reproducible multi-tenant capability without replacing
the existing local-lab, Fleet, or Ansible workflows or introducing a second
tenant controller prematurely.

## Decision

Keep the implementation under the existing `local-lab` and
`local-lab/fleet/bundles/tenant-foundation` paths. Use Fleet as the reconciler
for cluster-resident desired state. Add tenant configuration and validation
in the existing local-lab workflow, and retain the current tenant namespaces
and identifiers during the first migration.

The first shared-cluster tier will combine Rancher Projects and project roles
with Kubernetes RBAC, namespace ownership, NetworkPolicies, Pod Security
Admission, and resource quotas. No single mechanism will be described as the
complete security boundary. Tenant-wide budgets will be represented as an
aggregate ceiling and explicitly allocated to namespaces; per-namespace
quotas alone do not enforce the aggregate ceiling.

Rancher 2.15 maintains both a Project Limit and a Namespace Default Limit.
Namespaces created through Kubernetes APIs must carry
`field.cattle.io/projectId`; when a namespace needs a specific allocation, it
must also carry `field.cattle.io/resourceQuota`. Fleet-rendered namespaces
therefore include a per-environment Rancher reservation matching the catalog
allocation, while the Project Limit remains the tenant-wide pool. The
namespace `ResourceQuota` remains an additional native Kubernetes admission
boundary. See the [Rancher 2.15 project quota guide](https://rancher.github.io/product-docs-playbook/rancher-manager/v2.15/en/cluster-admin/project-admin/project-resource-quotas/resource-quotas-in-projects.html).

Use Rancher's supported `Project` and `ProjectRoleTemplateBinding` resources.
The tenant foundation emits stable Project IDs, custom project RoleTemplates,
namespace ownership metadata, and quota/security resources. The separate
binding reconciler reads each Project's actual
`status.backingNamespace`; it does not guess Rancher-generated namespaces or
write Rancher-generated Kubernetes RBAC. It refuses projects without matching
tenant ownership labels and refuses conflicting bindings. Keycloak groups use
the full-path claim `/tenants/<tenant>/<role>` and Rancher OIDC group principal
names. The binding reconciler is plan-only by default and applies bindings only
after Keycloak OIDC is enabled.

Keycloak-side realm, client, mapper, and synthetic-account provisioning is
scripted in `configure-keycloak-tenants.py`, but has not been applied to the
live Keycloak instance. Rancher OIDC activation and its login/revocation tests
remain unfinished. Rancher's supported setup validates the provider through a
browser redirect; unattended activation must preserve local break-glass access
and prove login and revocation before it is treated as operational.

## Alternatives considered

### New Tenant CRD and controller

Deferred. A new controller would create another reconciliation system and
increase the software and security surface before the existing Fleet/Rancher
mechanisms have been evaluated. Reconsider only if declarative Fleet resources
cannot safely provide the required idempotent lifecycle.

### Ansible-only tenant provisioning

Not selected for cluster-resident tenant state. Ansible remains appropriate
for host and cluster bootstrap, but Fleet already owns the local cluster's
platform bundle reconciliation.

### Namespace-only tenancy

Rejected as the complete model. Namespaces are useful organization and policy
scopes but do not by themselves provide the Rancher dashboard boundary,
aggregate resource governance, network isolation, or a separate kernel.

## Consequences and limits

- Existing Fleet paths and deployment workflows remain in place.
- Reconciliation must be idempotent and ownership-aware.
- A one-shot role-binding reconciler complements Fleet because the correct
  Project backing namespace is runtime status; Fleet remains authoritative for
  the Project, RoleTemplates, namespaces, and tenant policy resources.
- The Keycloak group claim must be present in the token and use full paths;
  changing Keycloak group structure or Rancher provider type requires updating
  the principal mapping and verification tests.
- The local shared-cluster tier does not provide separate kernels or a DoD
  authorization boundary. Dedicated nodes/clusters and mission authorization
  requirements remain future design and assessment work.
