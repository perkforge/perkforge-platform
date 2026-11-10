# Repository guidance

Read README.md and HANDOFF.md first. Big Bang/Flux is the active platform; no Fleet application deployment path is supported. Read `big-bang-bootstrap/README.md` for platform work and `infrastructure/README.md` for host/RKE2 provisioning.

Local refers to a physical cluster. VM/AWS lab workflows are removed; do not reintroduce them or confuse historical trial state with operator-selected targets. Rancher is for platform-admin cluster lifecycle management; Flux owns GitOps.

Never print, commit or copy credentials from `.secrets/` into tracked files. Preserve ignored evidence, backups and user files. Do not run provisioning, teardown, live integration, credential/security changes or cloud operations without action-specific authorization. Read-only/ offline checks do not authorize live mutations. Do not commit/push unless requested; never push main or merge on the user's behalf.

Preserve evidence-producing tests when moving code; distinguish historical fixtures from current live validation. Configuration management belongs in Ansible/YAML; Python is for verification, not a new configuration generator.

Maintain only the supported human-operated procedure and required implementation/tests. Do not recreate historical archives, session journals, planning folders or duplicate docs. Physical IP/MAC metadata belongs only in ignored infrastructure/ansible/inventory/.topology.yml. Public topology views show relationships without physical identifiers; credentials and private keys must remain outside tracked files.

## Credential custody and runtime secrets

- Use Bitwarden Password Manager for explicitly approved bootstrap/recovery inputs and durable human break-glass credentials that must remain available independently of the cluster and Keycloak. Follow the [credential storage procedure](big-bang-bootstrap/configuration/ansible/bitwarden-credentials.md).
- Use OpenBao for ongoing platform-owned and tenant-specific runtime secrets, with separate scopes and ESO delivery only to approved consumers. Do not substitute personal tokens or a Bitwarden runtime integration for that path. See [shared-secret scope](https://github.com/perkforge/perkforge-platform/issues/31).
- Never make OpenBao the sole custodian of the material needed to recover it. Root tokens, unseal shares, CA signing keys and SSH private keys require their separately reviewed custody; do not place them in downstream application records or generic Login items.
- The [Bitwarden recovery bootstrap](big-bang-bootstrap/configuration/ansible/bitwarden-bootstrap.md) reads existing approved Login fields and seeds only missing approved OpenBao records. It does not create Bitwarden items, rotate credentials or activate ESO consumers.
- Obtain action-specific authorization for credential creation/access, storage destination and sharing, rotation, delivery and cleanup. These instructions and a documentation change authorize none of those operations. Never expose values, sessions, encoded payloads or secret-bearing receipts in Git, chat or logs.

## Working rules

- Use the GitHub CLI (`gh`) for PerkForge GitHub operations unless Corey directs otherwise. Do not switch tools or credentials to bypass an access denial.
- Use the [Current Board](https://github.com/orgs/perkforge/projects/1/views/1) as authoritative for work scope, priority and status. Check the relevant issue before starting or proposing the next task.
- Keep tickets and PR/MR descriptions concise: outcome, blocker or next action, and relevant evidence links. Avoid repeated narration.
- Work on feature branches and submit draft PRs/MRs for Corey to review and merge. Never commit or push directly to main, merge, or enable auto-merge on his behalf.
- Prefer one cohesive PR/MR and coordinated deployment per app when practical. Preserve required repository boundaries and safety/approval stages; link dependent PRs/MRs.
- For authorized changes, run relevant local/offline tests and checks before handoff, even while CI is disabled or paused. Report passed, failed and unrun checks. Offline validation never authorizes live changes.
