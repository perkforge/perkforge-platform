# Native polling candidate for GitLab events

Proposed smallest reusable path, not selected/deployed:

`GitLab API → gitlab-ci-pipelines-exporter → existing Prometheus → Grafana-managed rules → built-in Alertmanager → scoped Mattermost + ntfy`

This avoids writing/operating a bespoke webhook/state service. GitLab itself remains
the latest-state source; Grafana owns alert instance state, repeat, grouping,
silences and resolved delivery. The prior webhook template remains inactive and is
not needed for this polling candidate. No exporter, scrape, rule or hook is enabled.

## Inputs and trust

The pinned upstream is v0.6.0, commit and Linux amd64 SHA512 in `sources.yaml`.
Checksum came from the upstream HTTPS release, **not independently authenticated
signatures**. No exporter binary has been installed/executed or compatibility with
our GitLab 19.4.2 proven. Verify artifact checksum and provenance before executing;
use reviewed artifact acquisition, never an unpinned `latest` install.

Future Ansible rendering must validate inputs with `verify_inputs.verify` and
repeat those checks in the apply workflow. Test Python is verification, not an
installer. `approved: true` is a review marker, not an authorization grant. Bind
numeric project IDs and full paths to the shared context and native inspector;
the exporter itself selects by path, so identity drift must be checked before use.
Actual refs, environments, scanner job/stage names, source types and Grafana org
and data-source IDs remain unselected. Do not assume fixture `main`, `test`, `push`
or `scanner` is a real Portal setup. There is no production input file here.

Use one context-scoped reader and explicit projects, no wildcard discovery or child
pipeline traversal. Token comes from protected runtime `GCPE_GITLAB_TOKEN`, not the
rendered YAML; no credential is created here. Upstream documents broad token scopes;
validate the least-privilege read-only API scope against the selected endpoints
before any token grant rather than copying those scopes blindly. TLS verification
stays on, with the existing private CA trust delivered separately. Listener remains
loopback-only. Deployment and scrape/network design remain to be integrated.

Pipeline variable/test-report/runner-description capture is disabled. Exported
metrics still include project/ref/job metadata; keep exporter and metrics backend
platform-only until independent tenant query isolation is proven. A metric label
is not authorization. Rules use static operator-owned context/project labels and
exact selectors; raw metadata is not forwarded in messages.

## Recovery semantics and limits

Each rule has one fixed incident identity and aggregates to one unlabeled value:
failed status → 1; success → 0; running/pending/canceled/skipped or absent → no data.
Grafana `KeepLast` for no-data/error preserves an already firing alert until the
matching scope actually succeeds. A new run starting is **not recovery**. Rules are
paused, including the native import fixture. The candidate does not define whether
canceled deployments/scans should be acknowledged or manually resolved; choose that
before activation. Scan rules mean execution failure only, never findings severity.

This is **latest-state monitoring, not an event ledger**. A failure followed by
success between API polls/scrapes can be missed. Poll cadence is a candidate 30s,
not a delivery SLA. Grafana restart/state persistence and no-data behavior require
lifecycle acceptance. Add independent exporter/API freshness and scrape health
alerts before activation: missing/error data must not silently masquerade as
success, and a reachable exporter can still hold stale cached API data.

Do not use the pipeline's creation/update timestamp as proof of a recent API poll.
A successful API response may legitimately describe a long-idle pipeline. Do not
unpause these rules until current-data health, rejected/removed identities and
native evaluation have been tested. Repeat policy remains unresolved-only via the
single notification owner, not repeated one-off webhook sends.

## Evidence and remaining acceptance

Five offline candidate tests check routing selectors, status expressions, explicit
projects, disabled secrets/variables and paused state. A disposable **network-none**
Grafana 13.2.1 test imports the paused rule and reads back its expression, static
labels, `KeepLast` settings and file provenance. That is native import evidence,
**not PromQL evaluation, exporter compatibility, lifecycle or delivery proof**.
No synthetic test grants real access or contacts GitLab.

Run `PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest configuration.test_gitlab_metrics -v`.
For existing pinned official Grafana image only:
`RUN_GRAFANA_GITLAB_RULE_IMPORT=1 PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest integration.test_grafana_gitlab_rule_import -v`.

Before activation test failed→running→success and canceled/no-data across restarts,
concurrent refs/sources, deleted jobs, stale API cache, transient poll gaps and
cross-tenant denial. Confirm acceptable polling semantics with Corey. Keep #334
open until actual integration and scoped receipt tests pass.

References: [upstream pinned configuration](https://github.com/mvisonneau/gitlab-ci-pipelines-exporter/blob/c50ef849a541cd2a826167b9494fa7d0d7d134b4/docs/configuration_syntax.md),
[pinned metrics](https://github.com/mvisonneau/gitlab-ci-pipelines-exporter/blob/c50ef849a541cd2a826167b9494fa7d0d7d134b4/docs/metrics.md),
[GitLab pipeline efficiency](https://docs.gitlab.com/ci/pipelines/pipeline_efficiency/).
