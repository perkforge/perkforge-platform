# Maintain the platform

Run commands from the repository root. Work on a feature branch; review and release before a separately approved activation.

- [Add or configure a Big Bang application](applications.md): package selection, values, prerequisites and validation.
- [Add a cluster or environment](targets.md): physical inputs, optional tenant enrollment and bootstrap boundaries.
- [Add an impact-level profile](profiles.md): reuse, precedence and security validation.
- [Bootstrap operation order](../../big-bang-bootstrap/configuration/ansible/README.md) and [test commands](../../big-bang-bootstrap/tests/README.md).

Infrastructure Ansible owns RKE2/Rancher; platform Ansible seeds/configures Big Bang/Flux; enrollment Git owns tenant foundations and registration; application Git owns tenant deployments. Rancher manages clusters, Flux manages application reconciliation. These guides describe current code, including its gaps, not physical readiness or IL authorization.
