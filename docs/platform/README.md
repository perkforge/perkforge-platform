# Maintain the platform

Run commands from the repository root. Work on a feature branch; review and release before a separately approved activation.

- [Add or configure a Big Bang application](applications.md): package selection, values, prerequisites and validation.
- [Add a cluster or environment](targets.md): physical inputs, optional tenant enrollment and bootstrap boundaries.
- [Add an impact-level profile](profiles.md): reuse, precedence and security validation.
- [Bootstrap operation order](../../big-bang-bootstrap/configuration/ansible/README.md) and [test commands](../../big-bang-bootstrap/tests/README.md).

Infrastructure Ansible owns hosts/RKE2; platform Ansible seeds/configures Big Bang/Flux and gated Rancher OIDC; enrollment Git owns tenant foundations and registration; application Git owns tenant deployments. Rancher manages clusters, Flux manages application reconciliation. These guides describe current code, including its gaps, not physical readiness or IL authorization.

## Core principle: keep authorization evidence with the change

For every application addition or authorization change, the **same MR** must:

- Update the [role/app matrix](../../big-bang-bootstrap/configuration/authorization/MATRIX.md): native permissions, tenant/resource scope, edition/protocol limits and machine-identity or not-applicable cases.
- Update [C4 ownership/trust-boundary views](../architecture/README.md) and relevant code links: who grants, who uses, and where the app/API enforces scope.
- Update relevant positive/negative [permission tests](../../big-bang-bootstrap/tests/README.md), including cross-tenant and privilege/elevation denial where applicable.
- Label **proposed / implemented / tested** status, actual evidence and explicit exceptions or gaps. An unsupported mapping needs a documented decision, not a pretend implementation.

Review these together before merge. Offline models and successful login are not
live authorization proof; deployment/grant approvals and acceptance remain separate.
This checklist uses existing docs/tests, not a generic policy framework.
