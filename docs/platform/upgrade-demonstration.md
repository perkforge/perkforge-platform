# Upgrade demonstration runbook

Target: PerkForge platform *adoption* (January 2027). We need to show reviewers
and potential adopters that PerkForge upgrades safely and repeatably — in
**documentation** and **in practice**. This is that documentation. It records a
single, reproducible upgrade path an operator can follow without AI, and it
defines the evidence each step must capture so a real upgrade can be
demonstrated live later.

Status: queued/draft. **Do not execute.** This is the "plan before beginning"
artifact for the queued Big Bang parent upgrade
([perkforge-platform#199](https://github.com/perkforge/perkforge-platform/issues/199)
operating model; queue draft
[#536](https://github.com/perkforge/perkforge-platform/pull/536)). None of the
stages below is authorized by this document; each needs its own approval.

## 1. The upgrade chain

PerkForge upgrades bottom-up, one layer at a time, each with its own window,
evidence and recovery:

| Layer | Owner | Demonstrated by |
|---|---|---|
| Host OS / RKE2 | Infrastructure Ansible | Nodes Ready + same version after node-by-node drain (separate infra window, no reboot inside app window) |
| Flux foundation | platform Ansible `bootstrap.yaml` | Pinned controller images pulled from the private registry; artifacts reconcile |
| Big Bang parent umbrella | platform source promotion | Parent chart at an exact immutable tag/commit |
| Big Bang managed components | parent chart values | Each child version = the parent chart's pinned value, not "latest" |
| Non-parent / add-on apps | enrollment/application Git | Independent app upgrade tracked separately, never folded into the parent PR |

Big Bang's parent chart owns GitLab, Mattermost, Keycloak, etc. Their versions
come **from that exact parent chart's values**, never from the latest standalone
package tag. Take every managed pin for the target (e.g. `4.2.0` for the queued
upgrade) from that release's rendered values.

## 2. How we demonstrate it works

1. **Documentation-first (this runbook):** the operator does not need AI or a
   human on chat to run it. The steps, gates and evidence are written down.
2. **One real, recorded upgrade:** prove the path on a real cluster through the
   full gate chain — a before/after version matrix, a backup + isolated restore
   check, go/no-go approvals, readiness verification and a rollback drill. An
   upgrade that ran and recorded evidence is the demo; a write-up is not.
3. **Start small, then flagship.** Prove the *procedure* on one low-risk
   managed component first (exercises every gate end-to-end), then run the
   flagship parent upgrade (Big Bang `latest 4.x`) using the identical
   procedure, with the small one as its rehearsal.

## 3. Preconditions before any upgrade

Every layer's precondition checklist (unsatisfied anything = stop):

- [ ] Clean checkout of the exact published immutable source/tag; verify
      `bigbang_tag` and `bigbang_expected_commit` match the upstream render.
- [ ] Correct `target_kubeconfig`, `target_context` and `expected_cluster_uid`
      (explicit protected external inputs; never main/feature-branch/future tag).
- [ ] Application-consistent backup for every affected stateful service:
      database + matching repositories/filestores/object storage + persistent
      volumes. Record off-cluster backup IDs, timestamps, and the **result of an
      isolated restore/read test**. An etcd snapshot is not an application backup.
- [ ] Write-quiesce point agreed with the operator.
- [ ] Health/capacity baseline recorded (see the delivery stage).
- [ ] Go/no-go and rollback owner named, window agreed.

## 4. The delivery stage (the core of the demo)

Driven from `big-bang-bootstrap/configuration/ansible/` against the pinned
source at `configuration/packages/bigbang/{source,release}.yaml`. Repeat the
same five sub-steps for each layer being upgraded:

1. **Baseline.** Record the current ready Flux Source/root revision, ready
   HelmReleases, and each component's declared vs observed version. This is the
   "before" matrix; a noisy/late sample is not a baseline.
2. **Backup + restore check.** Confirm the off-cluster backups from §3 exist and
   that an isolated restore was already exercised. Record the IDs and the check
   result (not the secret contents).
3. **Approve and promote.** For a parent upgrade, conditionally advance the root
   / pinned tag only after verifying the expected **old path, resourceVersion,
   active Source and exact fresh artifact**. Move one layer at a time.
   Child suspension comes from reviewed Git values — never a manual resume of an
   individual child against contradictory values.
4. **Verify readiness.** Flux curses ready; completed migrations; a health and
   capacity snapshot (`kubectl top nodes`, `kubectl top pods -A`, Longhorn
   node/volume/replica status) showing the delta from the baseline. Save the
   run evidence; missing/stale metrics mean unavailable, not zero.
5. **Application smoke.** For each affected app in scope: login, database
   connectivity, and a representative read/write (e.g. Nextcloud upload/download,
   a notification, a pipeline). Stop and escalate on drift/failure/timeout.

Record the final rendered `chart/app/image` versions as the "after" matrix. The
pair of matrices plus the readiness/health deltas and the approved go/no-go are
the demonstration evidence.

## 5. Non-parent add-ons

Add-ons outside the parent chart (Nextcloud, PerkForge Portal, ntfy, the tenant
acceptance runner, GitLab Valkey and Harbor Valkey as separate releases) are
inventoried from the selected Flux root and their owning manifests. Each is
assessed separately: declared vs observed version, can it stay, and a blocker or
evidence. Do not take an add-on's version from Big Bang values; do not fold a
warranted add-on upgrade into the parent PR.

## 6. Rollback / recovery

- **Never disable a package to roll back** — that can uninstall it. Disabling an
  app to make capacity look acceptable is not a rollback.
- **Pause the affected root first, then the affected child** Source/reconciler/
  HelmRelease before stopping new workloads. Root suspension halts manifest
  updates; it does not stop running services and does not delete retained data.
- **A git revert does not undo schema or data changes.** A failed migration/data
  check stops reconciliation; get an explicit recovery decision before any
  destructive restore.
- **Resume only from a reviewed canonical configuration**, never from an active
  parent that could undo containment.
- Separate host/RKE2 rollback (node re-provisioning/drain) from application
  rollback; they are different windows.

## 7. Evidence artifact for January

One demonstrable bundle per completed upgrade:

1. The before/after version matrix (this runbook's §4 baseline → after).
2. The backup IDs + timestamps + isolated restore result (no credentials).
3. The health/capacity deltas (annotated timestamps and versions).
4. The go/no-go record at each approval checkpoint.
5. A one-line result: which layer, which tag, migrated/verified, by whom.

Keep credentials, private IDs, DM text and rollback journals out of Git.

## References

- Operating model: `#199` (human-governed, rehearsed, evidence-captured).
- Queue draft: `#536` (Big Bang `4.2.0`, parent-defined pins, no files changed).
- Bootstrap/registry: `big-bang-bootstrap/configuration/ansible/bootstrap.yaml`.
- Big Bang package source/release: `configuration/packages/bigbang/`.
- Readiness/health: `big-bang-bootstrap/configuration/ansible/readiness.yaml`.
- Container recovery: `big-bang-bootstrap/configuration/ansible/README.md`.
