# Repository guidance

Read README.md and HANDOFF.md first. Big Bang/Flux is the active platform; `archive/fleet/` is historical reference, never an active deployment path. Read `big-bang-bootstrap/README.md` for platform work and `infrastructure/README.md` for host/RKE2 provisioning.

Local refers to a physical cluster. VM/AWS lab workflows are removed; do not reintroduce them or confuse historical trial state with operator-selected targets. Rancher is for platform-admin cluster lifecycle management; Flux owns GitOps.

Never print, commit or copy credentials from `.secrets/` into tracked files. Preserve ignored evidence, backups and user files. Do not run provisioning, teardown, live integration, credential/security changes or cloud operations without action-specific authorization. Read-only/ offline checks do not authorize live mutations. Do not commit/push unless requested; never push main or merge on the user's behalf.

Preserve evidence-producing tests when moving code; distinguish historical fixtures from current live validation. Configuration management belongs in Ansible/YAML; Python is for verification, not a new configuration generator.
