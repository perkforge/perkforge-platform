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

## Parallel full validation

The first post-merge run of #146 ([41640409008](https://github.com/perkforge/perkforge-platform/actions/runs/41640409008))
passed on `79e6967dd08288e49fee045fd2b29f54ff0feb3f`. It took **21m27s**
from creation to completion: selection 20m46s, SSO 8m34s, documentation 13s,
and the final release job 24s. There was one automatic main workflow, rather
than duplicate selection triggers. This full main run does not measure the new
docs-only/targeted PR path. Runner variance matters: the preceding release's
full selection job took 15m02s, so a single timing is not a speed guarantee.

Within that run, platform discovery executed 176 tests in 942s, followed by
40 infrastructure tests in 155s, 27 PXE tests in 105s and eight evidence tests.
Those sequential suites dominate the release wait, not release publication.

The [verification runner](../../scripts/ci_suite.py) partitions the **same**
platform discovery into realm foundation, human enrollment, realm-admin and
residual suites. Every new or unclassified platform test stays in residual.
Infrastructure and PXE keep their complete original discovery commands on
separate runners. Selection retains residual/evidence, immutable dependency
checks, historical bootstrap and native Flux CEL admission validation.
The regression matrix allows at most three concurrent runners; all rows finish
even when another fails, and failures still block the reusable configuration
workflow and release. No result is allowed to fail silently.

SSO discovery is independently compared with its original three commands.
Client lifecycle runs separately from the remaining app/security fixtures.
New app tests stay in the app shard. Existing intentional overlap with full
discovery/host checks and the original environment-controlled skips is retained;
partitioning never changes those enablement flags. These are isolated synthetic
HTTP/TLS state machines, not tests against the physical cluster.

The assignment audit rejects duplicate IDs, missing test assignments, failed
imports and unexpectedly empty required shards. It emits counts and sorted-ID
SHA-256 digests; [regressions](../../scripts/test_ci_suite.py) compare the union
against original discovery and verify required jobs and release dependencies.
The audit runs before any suite. Review intentional module renames/removals with
the assignment changes; do not suppress its failure to obtain a green empty job.

Run the nonexecuting audits from the repository root:

```bash
python3 scripts/test_ci_suite.py
python3 scripts/ci_suite.py --family platform --audit
python3 scripts/ci_suite.py --family sso --audit
```

This raises the number of configuration jobs from five to eleven (including
matrix rows), with repeated checkout/dependency setup and potentially more queue
contention/runner minutes. No cross-run acceptance cache or privileged artifact
reuse is introduced. Measure hosted critical path, queue/setup time and counts
before claiming improvement. Release creation still requires complete validation
of the actual main/release commit; metadata-only release commits do not bypass it.
