# Evidence

Raw operational evidence stays local and ignored; do not commit tokens, passwords, Secret bodies or kubeconfigs. `manage-security-findings.py` is the retained offline findings-register tool, using protected local state and sanitized imported reports. Its tests run against synthetic data.

Active Big Bang rendering, identity and portal boundary tests are under `../tests`. The full historical evidence producers and tests are preserved under `archive/fleet/local-lab`: RBAC, admission, network, quotas, observability, security-suite aggregation and OpenBao isolation. Their catalogs, Rancher RoleTemplates, endpoints and fixture permissions describe the old deployment. They require explicit enrollment/Big Bang adaptation before any live reuse; archiving them preserves assurance work, it does not prove current controls. See `docs/RESTRUCTURE-INVENTORY.md` for exact paths.

Do not run historical apply-mode probes against the current cluster. A future evidence run needs reviewed target identities, namespaces and expected boundaries from the enrollment repository, plus action-specific approval. No new custom platform enforcement is introduced here.
