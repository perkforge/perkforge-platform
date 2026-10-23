# Repository migration plan: PerkForge Platform

## Purpose and product scope

This plan moves the existing `coreyperkins/homelab` project to
`perkforge/perkforge-platform` while preserving its engineering work and Git
history. The new identity is Perkins Forge / PerkForge Platform.

PerkForge Platform is a functional, secure, multi-tenant Kubernetes PaaS
reference implementation and professional engineering portfolio. It
demonstrates platform engineering, DevSecOps, security architecture, and
RMF/GRC through working platform capabilities, implemented controls,
repeatable assessment, evidence, findings, and risk remediation. The current
operator uses synthetic tenants to exercise genuine tenant lifecycle and
isolation functionality. Commercial billing, subscriptions, and public
customer onboarding are outside the project's scope.

The immediate target is the local VM harness, followed by the three-node
ThinkCentre RKE2 cluster. Keep local VM work under `local-lab/` and
physical-host work under `ansible/`. Prefer reproducible, portable deployment
patterns and avoid unnecessary hardware-specific assumptions. EKS, AKS, and
multiple production environments are not active implementation targets.

The portfolio may document security engineering and simulated RMF evidence.
It must not imply a government ATO, FedRAMP authorization, CMMC certification,
or government endorsement. Use synthetic data and clearly label simulated
assessment artifacts.

## Current repository facts

- Source checkout: `/home/corey/src/homelab`.
- Source remote: `https://github.com/coreyperkins/homelab.git`.
- Source branch: `main`, at `04030d6` during this assessment; `origin/main`
  matched it. No tags or additional branches were present.
- The source working tree is dirty. `HANDOFF.md`, `README.md`,
  `local-lab/README.md`, `local-lab/fleet/gitrepos/local-lab.yaml`,
  `local-lab/scripts/deploy-mattermost.sh`, and
  `local-lab/scripts/rebuild-local-lab.sh` are modified. `docs/`,
  `local-lab/APPLICATIONS.md`, six Fleet bundle directories,
  `local-lab/fleet/gitrepos/platform-apps.yaml`, and two deployment scripts
  are untracked. Preserve and review all of them before selecting migration
  content; none were staged or committed during readiness checks.
- Target checkout: `/home/corey/src/perkforge-platform`, with the requested
  `https://github.com/perkforge/perkforge-platform.git` remote. It had no
  commits or files and no remote refs during the assessment.
- On 2026-10-23, authenticated GitHub CLI access was verified for
  `coreyperkins` using the keyring. The private target repository exists and
  reports `ADMIN` permission. Its default branch is unset because it is empty.
  The token had `gist`, `read:org`, `repo`, and `workflow` scopes. Read-only
  `git ls-remote` returned no refs.

These observations are a snapshot. Recheck source and target refs, working
trees, and GitHub permissions immediately before each migration write.

## Migration rules

1. Preserve source Git history. Do not recreate the project by copying files
   into a new initial commit, rewrite history, delete branches, or force-push.
2. Preserve uncommitted work as a separately reviewed set of changes. Never
   include `.secrets/`, kubeconfigs, private keys, VM credentials, generated
   passwords, or local VM images.
3. Do not change the source remote, add a migration remote, push, transfer
   ownership, rename a GitHub repository, or alter the default branch until
   the user explicitly approves that operation.
4. Verify authenticated access to the `perkforge` organization and write
   permission on `perkforge-platform` before any push. The target currently
   appears empty, but that must be rechecked at execution time.
5. Keep infrastructure identifiers stable during the branding move. Change
   them only in a separate, justified migration with compatibility checks.
6. Do not run a destructive local-lab rebuild as part of the repository
   migration.

## Public-facing changes to plan

- Set the repository's public title and README to **PerkForge Platform**.
- Describe Perkins Forge as a professional engineering portfolio for
  platform engineering, DevSecOps, cybersecurity, and RMF/GRC.
- Describe PerkForge Platform as a multi-tenant Kubernetes PaaS reference
  implementation that demonstrates engineering and verifiable
  synthetic-tenant security controls. State clearly that one person currently
  operates it and exercises tenant behavior with synthetic tenants.
- Apply the repository description supplied by the user after the target
  repository is verified.
- Propose an organization profile README in the `perkforge/.github` repository
  only after organization access is confirmed and that separate repository is
  approved.
- Update public documentation links and old product names selectively. Do not
  perform a global text replacement.

## Identifiers to preserve initially

These names participate in local workflows or cluster metadata and should not
be renamed as a side effect of public branding:

- `local-lab/`, its VM names (`cks-control`, `cks-worker`), IP addresses,
  `.test` hostnames, and local secret filenames.
- Fleet GitRepo names, bundle paths, release names, namespaces, and labels such
  as `local-lab.homelab/component` and `platform.homelab/tenant`.
- Existing app resource names, Helm release names, storage classes, database
  resources, and RKE2 cluster settings.

The `app.kubernetes.io/part-of: opengovlocalpaas` label is an old product
string in the uncommitted tenant manifest. Leave it untouched until a
dedicated identifier change is approved; first check selectors, scripts, and
existing live resources, then use a compatibility transition if needed.

Fleet GitRepo `spec.repo` URLs are different: they must eventually point to
the new repository for Fleet to fetch migrated bundles. Update those URLs only
after the target contains the intended history and bundle paths, then verify
that Fleet can fetch the new source before removing the old reference.

## Migration stages

### 1. Preserve and reconcile the source

- Record the source commit, branch/tag list, remote URL, and complete status.
- Review the existing dirty working tree file by file. Decide which local
  changes are intended migration content; retain unrelated local state.
- Keep a recoverable source checkout and do not delete the old GitHub repo.
- Confirm that `.gitignore` still excludes `.secrets/`, `images/`, local
  kubeconfigs, credentials, and generated artifacts.

### 2. Verify the destination

- Reauthenticate `gh` and confirm the active account and organization. This
  was verified on 2026-10-23 for `coreyperkins`.
- Confirm `perkforge/perkforge-platform` exists, is the intended repository,
  and grants the user sufficient write/admin access. It currently exists as a
  private, empty repository and the account reports `ADMIN` permission.
- Inspect its refs and contents. If it is no longer empty, stop and reconcile
  histories rather than overwriting it.
- Confirm the desired visibility, default branch, repository description, and
  organization profile location.

### 3. Transfer history without rewriting it

- Add/use a separate destination remote only after explicit approval.
- Push the preserved source branch and any tags without force. At the time of
  this plan there were no tags and only `main`, but recheck first.
- Verify commit ancestry, branch tips, tags, and the cloned destination before
  changing the canonical `origin` remote or updating users' checkouts.
- Keep the old repository available until the new checkout and Fleet source
  have been verified.

### 4. Update repository metadata and documentation

- Update README, descriptions, documentation links, and portfolio language.
- Preserve the full PaaS capability set, synthetic multi-tenancy, the local
  VM harness, the three-node homelab target, and security/RMF evidence work.
- Describe portable deployment patterns as a design preference without
  treating EKS, AKS, or multiple production environments as active targets.
- Remove claims about mass-market commercialization, billing, and public
  customer onboarding while retaining the PaaS reference implementation
  identity.

### 5. Repoint operational references

- Search for the old GitHub URL and update Fleet GitRepo sources and scripts
  that validate or fetch `origin/main`.
- Review CI references, repository badges, documentation links, and any future
  GitLab integration separately from app/cluster identifiers.
- Do not change namespaces, labels, URLs, Helm releases, or cluster naming
  merely to match the new brand.
- Confirm Fleet fetches the target repository and that the configured bundle
  paths exist before asking Fleet to reconcile them.

### 6. Close out

- Verify the new clone contains the preserved history and expected files.
- Verify no secrets or local artifacts were committed.
- Confirm README and repository metadata match the approved PerkForge PaaS
  reference implementation identity and RMF/GRC purpose.
- Record the new canonical URL and migration result in `HANDOFF.md`.
- Retain the old repository until the user explicitly approves archival or
  deletion.

## Acceptance criteria

- Existing commit history is reachable from the new repository; no history was
  rewritten or discarded.
- The source checkout and all pre-migration dirty changes are accounted for.
- Destination access was verified before the first write.
- No secret, kubeconfig, VM image, or generated credential was published.
- Fleet and automation references resolve to the intended source repository.
- Technical identifiers remain stable unless a separate change was approved.
- Public docs describe a functional, multi-tenant PaaS reference implementation
  and engineering portfolio, not a commercial customer-facing service or
  formally authorized system.

## Migration execution checklist and approval gates

### Readiness work completed without changing repository state

- Recheck source branch, commit, remotes, refs, and full working-tree status.
- Preserve all dirty and untracked work; review and classify it before staging.
- Reauthenticate GitHub and verify organization membership and destination
  write permission.
- Inspect the destination repository's refs, contents, visibility, and default
  branch.
- Review secret exclusions and identify any operational source references.

As of 2026-10-23, authentication and destination permissions are verified.
The source is `main` at `04030d6`, matching `origin/main`, with one branch and
no tags. The destination is private, empty, and grants `ADMIN` permission.
The source worktree remains dirty and all listed changes must be reviewed and
preserved before migration writes. The repository is ready for that review
stage; it is not yet ready to push because the dirty changes have not been
classified and selected for migration.

### Actions requiring separate explicit approval

1. **Stage and commit selected working-tree changes.** Review the complete
   diff and secret scan first. Do not include unrelated local changes.
2. **Add a destination remote and push preserved history.** Confirm the exact
   source commit/branch/tag set and destination state immediately beforehand;
   never force-push or rewrite history.
3. **Change canonical remotes or GitHub repository settings.** This includes
   renaming/transferring repositories, changing visibility/default branch, or
   editing organization/repository metadata.
4. **Change operational references.** Update Fleet GitRepo URLs and any scripts
   or integrations only after the destination contains the verified history
   and bundle paths; then verify Fleet fetches the new source.
5. **Archive or delete the old repository.** Keep it available until migration
   and operational verification are complete; archival or deletion requires
   its own approval.

Readiness checks do not grant approval for these actions. Preserve technical
identifiers throughout unless a separately reviewed compatibility change is
approved.
