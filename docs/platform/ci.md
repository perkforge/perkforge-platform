# Change-aware offline CI

`configuration-release` is the canonical automatic entrypoint: one call of the
shared selection workflow per PR or main push. The reusable workflow no longer
also starts itself for the same push/PR. It retains a manual full run. Release
writes remain restricted to main pushes after configuration and release checks;
read-only checks receive no service credentials and use no live kubeconfig.
No branch protection settings, release pins or deployment gates are changed.

## Selection and security boundaries

The small [selector](../../scripts/ci_impact.py) uses a NUL-delimited, no-rename
base/head Git diff. Deleted/renamed shared files cannot hide behind a new docs path.
The [selection tests](../../scripts/test_ci_impact.py) and documentation/C4 tests
run for every change. Known docs changes skip unrelated state machines. Isolated
SSO code/tests and the role matrix keep SSO **and** host-boundary suites; targeted
SSO also runs the shared authorization-model tests otherwise covered by the full
suite. Exact API OIDC host/routing fixture changes keep the host-boundary suite.

Every main push/manual run is full. Shared fixtures/configuration, release evidence,
workflow/selector changes, other security code, unknown paths, malformed paths,
unavailable commits and empty/missing diffs all fall back to full. A selector/test
failure blocks dependent jobs rather than emitting a successful empty plan.
The chosen flags/reason appear in the job summary. This is conservative routing,
not a claim that arbitrary dependencies can be inferred from filename extensions.

The full job retains the existing pinned dependency/reference verification,
all platform/infrastructure/PXE/evidence regressions, historical tag-aware bootstrap
and native Flux CEL admission tests. Existing negative permission, role-graph,
recovery and app-SSO tests remain in their owner suites. Main validation still runs
all of them before release automation; narrower PR checks do not waive review or
live acceptance. Workflow-policy edits themselves always select full validation.

## Measured baseline and limits

Before this change, a source branch with an open PR started a push selection run,
a pull-request selection run and the release workflow's reusable selection run.
MR145's exact head demonstrates all three. This change reduces that to one
canonical automatic suite per PR event, plus the separate required main-push run.

For the earlier TLS-only MR138, refreshed hosted configuration selection took
**20m38s** (run 41493756539, 17:42:58–18:03:36 UTC on 2026-11-02).
The important baseline is about twenty minutes for unrelated full regression work
on docs.
Local replay of MR138's eight changed paths selects docs only; replay of MR145's
twelve changed paths selects SSO/host/docs without full review-chain work.
These are tested routing decisions, **not measured hosted after-times**.

The optimization MR changes workflow policy, so its own CI intentionally runs all
suites and cannot demonstrate docs-only hosted turnaround. Record the first
eligible post-merge docs and isolated-SSO PR durations, queue time and npm cold/cache
cost before claiming a percentage improvement. Main/full/unknown-impact changes
still incur full validation. No tests are removed to manufacture a faster result.
