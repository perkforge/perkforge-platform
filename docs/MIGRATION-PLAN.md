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

- Historical source checkout `/home/corey/src/homelab` has been removed
  locally. Its GitHub repository remains available as `source`.
- Source remote: `https://github.com/coreyperkins/homelab.git`; its `main`
  remains at `04030d6`. No tags or additional branches were present at the
  time of migration.
- Current checkout: `/home/corey/src/perkforge-platform`, with `origin` at
  `https://github.com/perkforge/perkforge-platform.git` and `source` retaining
  the former remote. `main` tracks `origin/main`; the target repository is
  public.
- History-preserving migration commits include `ead1fb2`, `5f7f30e`,
  `c5cff46`, `c4698d5`, and subsequent Fleet/profile fixes. No force-push or
  history rewrite was used.
- The user changed repository visibility to public. Anonymous `git ls-remote`
  confirmed destination `main` was readable before Fleet reconciliation.

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
   permission on `perkforge-platform` before any push. This was verified
   immediately before the initial push.
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

### 1. Preserve and reconcile the source — complete

The source history and local state were reviewed. The old checkout was removed
only after required files and local VM assets were moved and verified. The old
GitHub repository remains available.

### 2. Verify the destination — complete

The user created `perkforge/perkforge-platform`, verified its description, and
changed its visibility to public. Anonymous access to `main` was confirmed.

### 3. Transfer history without rewriting it — complete

`main` was pushed without force from the preserved source history. The target
is canonical `origin`; `coreyperkins/homelab` remains the `source` remote.

### 4. Update repository identity and documentation — complete

Documentation describes PerkForge Platform as a functional multi-tenant PaaS
reference implementation and engineering portfolio, preserving the local VM
harness, physical homelab target, security controls, and RMF/GRC evidence goal.

### 5. Repoint operational references — complete for local Fleet

The `local-lab` and `platform-apps` GitRepo sources now use the public PerkForge
repository. Fleet fetched the same `main` revision for both GitRepos and
reconciled all seven bundles in the conservative local profile. The GitLab
PostgreSQL Cluster manifest and Valkey chart are separate bundles. Existing
CNPG resources were adopted in place; no VM teardown or database deletion was
performed.

### 6. Close out

The canonical URL and verified Fleet state are recorded in `HANDOFF.md`. Keep
the old GitHub repository until the user separately approves archival or
deletion. Other integrations and technical identifiers remain unchanged.

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

### Readiness and migration progress

- Preserve source history and review local state before migration writes.
- Verify destination access and intended visibility before pushing.
- Keep secrets and VM artifacts outside tracked files.
- Verify Fleet source access and bundle reconciliation after repointing.

The destination is public, `main` is canonical at `origin`, and anonymous
fetch was confirmed. Both local Fleet GitRepos now reference PerkForge and
reconciled the conservative profile. The old repository is still retained as
`source`; it has not been archived or deleted.

### Actions requiring separate explicit approval

1. Repository visibility was changed to public by the user. Further changes to
   ownership, repository name, or organization metadata require approval.
2. Fleet sources were repointed and verified. Other operational integrations
   should be reviewed separately before changing.
3. Archiving or deleting the old GitHub repository requires separate explicit
   approval. Keep it available until that decision is made.

Readiness checks do not authorize unrelated repository or infrastructure
changes. Preserve technical identifiers unless a separately reviewed change
is approved.
