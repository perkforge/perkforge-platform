# Configuration releases

This repository uses the portal image workflow's pinned Release Please action,
with its **simple** strategy: no application package or new runtime dependency.
Conventional Commits → reviewed release PR → human merge → main Action publishes
`vMAJOR.MINOR.PATCH` Git tag/GitHub release. No image or deployment is published.
`VERSION`, `.release-please-manifest.json` and `CHANGELOG.md` are release-PR outputs.
The initial `0.0.0` is an unreleased sentinel, not a historical tag; first eligible
changes propose `0.1.0`. One-time `bootstrap-sha` is release-history metadata,
not a deployment ref. The workflow setup PR must retain its `feat(release)` subject.

After 0.1.0: `fix`/`perf` → patch, `feat` → minor, either breaking-change form →
major. Docs/chore/tests alone create no release; highest eligible bump wins.
Both pre-1.0 downgrade options are false. Review the final merged commit subject
and breaking footers, not just the original PR title. Config repo version and
portal chart/image versions are independent; this does not bump either of those.

## First rollout: do not invent missing refs

1. Merge each repository's release-workflow PR after checks. No tags are created
   by these feature branches or by merging the workflow alone.
2. Let the main workflow propose its release PR; review VERSION/manifest/changelog.
   Approve any pending workflow runs, or run **configuration-release** manually
   on that release branch for read-only checks. Human merge publishes the tag.
3. Verify the **portal app config** release exists and resolves correctly. Only
   then open the small enrollment PR switching its Flux source from commit to
   exact `ref.tag` (for example `v0.1.0`, only if actually published). Validate and
   release enrollment after that change merges.
4. Verify the new **enrollment** release, then switch platform's enrollment ref to
   that exact tag in a small PR. Its tests must resolve tags, check out the resolved
   commits and validate the full platform → enrollment → app chain. Keep resolved
   SHAs in release evidence, not human-maintained deployment inputs.
5. Release **platform** after that change; in its next reviewed config change,
   switch Ansible `config_commit`/seed `ref.commit` to validated `config_tag`/
   `ref.tag` and use the published platform tag as the bootstrap selection.
   Resolve and verify the tag before any gated bootstrap apply. The resulting
   platform release includes the tag-aware bootstrap. No floating main/latest ref.

These are separate sequential PRs because **none of these repos has a release
at setup time**. Current verified commit refs intentionally remain until the
corresponding releases exist. No missing tag is accepted as a deployment input.
Big Bang's existing 3.35.1 tag/commit verification and third-party Action SHA pins
remain independent and unchanged. All deployment stays paused/disabled.

## Verify and preserve a published ref

```sh
scripts/verify-release-ref.sh perkforge/perkforge-tenant-portal v0.1.0
# On later verification, pass the previously recorded resolved commit as argument 3.
```

The read-only check requires a published non-draft/non-prerelease SemVer release,
resolves annotated or lightweight tags, and rejects a changed recorded commit.
Use its output as review/release evidence; fetch/check out that resolved commit
and run the actual path/context/render tests before accepting a dependency update.
Never repoint a published version: fix forward with a new release. A tag name
alone is not cryptographically immutable. Repository release/tag protection or
immutable-release settings are **not configured by this PR**; any required change
needs owner approval. Do not grant a broad PAT just to bypass workflow behavior.

## Events, rights and recovery

The release job requires successful configuration and release tests and only runs
on a main **push**, using `GITHUB_TOKEN` with contents/PR/issues write (release,
release-PR and label operations). All checks have contents read only. No job
approves/merges PRs. Existing Actions PR-creation settings were observed enabled;
no setting or credential is changed here.

Do not rely on tag/release events from `GITHUB_TOKEN` to trigger another workflow.
The main run publishes and records the resolved tag in that same workflow.
Bot-created PR checks can require explicit workflow approval; manual dispatch runs
checks only, never release creation. This follows the
[Release Please action](https://github.com/googleapis/release-please-action) and
[GitHub event rules](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).
Main release publication and PR creation still need the first approved live
GitHub workflow run; offline tests do not prove those API operations.

If a main run fails, inspect its evidence and rerun failed jobs on that original
run. An existing tag is never manually recreated or force-pushed. The tag/source
recording step fails if the published tag does not resolve to the triggering main
commit; investigate rather than move the tag. No `workflow_dispatch` publication
backdoor is supplied. Future automation after publication must remain in the
same gated workflow or use a separately reviewed event/token design.

Offline tests use the actual release-please 17.3.0 library bundled by the action,
plus simulated read-only tag lookups. No API writes occur in tests. Keep the
library test version and action pin synchronized on upgrades.
