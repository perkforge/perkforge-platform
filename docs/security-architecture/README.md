# Security architecture review

**Review baseline:** 2026-11-09, platform commit
`ae3b74b94c83f0bf909a798ea797e049c269fe8c`. This is a source review, not a live
assessment, an ATO package or a compliance/authorization claim. It does not assert
that every configured package is selected, running or accepted. The
[control evidence map](controls.md) identifies code, evidence limits and open work.

## Review in this order

1. `security_context`: human, code, control-plane, workload and evidence boundaries.
2. `security_identity`: authentication is separate from authorization and privileged recovery.
3. `security_image_intake` and `security_chart_intake`: **planned**, gated before Harbor.
4. `security_maintenance` and `security_promotion`: current GitOps ownership versus
   the planned Rust CLI and GitLab-to-GitHub promotion.
5. [Control evidence map](controls.md), then the linked owner runbooks/tests.

**Implemented (source)** means configuration/code exists at the reviewed revision,
not an assertion of deployment. **Planned** means not implemented or not complete.
**Unverified** means the relevant runtime/negative test or operational evidence is
missing from this review. These statuses can apply to different parts of one path.
Historical operator acceptance is bounded to its recorded target, revision and time;
use current read-only verification before treating it as a present-tense fact.

## Zero trust and least privilege

The design does not grant trust merely because a request comes from the LAN,
cluster, an authenticated person or a signed-in application. Each receiving API
must validate identity and authorize the requested tenant/resource/action. Keycloak
SSO is authentication infrastructure, not a substitute for native app permissions,
Kubernetes RBAC, admission or NetworkPolicy.

Separate human roles, app clients, installer service accounts, runtime identities
and recovery credentials limit routine authority. The implementation includes
scoped installer delegation and independently gated API configuration. It also
retains powerful cluster, identity and operator authorities. Workload-edit rights
can permit secret mounts or service-account use even without Secret API write.
These bypass paths need admission, identity and negative-test evidence, not a
claim that namespaces or group names alone enforce isolation.

No mesh is selected by the shared defaults. Server TLS is not mutual TLS or
workload authorization. Some apps have verified-TLS source contracts, while
end-to-end hop coverage, identity lifecycle and migration remain a separate
[#45](https://github.com/perkforge/perkforge-platform/issues/45) design review.
[#44](https://github.com/perkforge/perkforge-platform/issues/44) owns complete
allowed-flow/default-deny design. This review selects neither Istio nor Gateway API.

## Why these components

| Choice | Intended benefit | Cost, trust and remaining decision |
|---|---|---|
| Keycloak | Self-hosted shared identity, per-app clients and consistent human authentication lifecycle reduce independent app passwords and duplicated identity administration. | Central identity is a high-value dependency. Realm administrators can change memberships/authentication. Native app authorization, client-specific claims, revocation, recovery and per-app protocol/edition support must still be tested. A shared realm is not tenant isolation. |
| Mattermost | Candidate for self-hosted collaboration with platform-controlled data location, retention and integration, and planned Keycloak sign-in. | **Inactive candidate.** Exact selected binary/edition/license, supported security release, team/channel denials, restore and operator authority are unresolved acceptance gates. Its operator has cluster-wide wildcard authority; no tenant-private collaboration or paid compliance feature is promised. See [edition review](../../big-bang-bootstrap/configuration/packages/mattermost/edition-review.md). |
| Self-hosting | Makes software selection, custody, configuration and evidence collection controllable within an approved boundary; can reduce reliance on an external runtime service. | Transfers patching, availability, monitoring, capacity, backups, recovery and incident response to the operator. A small cluster is not inherently safer or more available than SaaS. SaaS can offer independently assessed operations and resiliency, but introduces provider, residency, contractual and external identity dependencies. Compare requirements and evidence, not labels. |
| GitLab plus a public-safe GitHub release surface | Proposed internal development home and separately reviewed public release/GitOps source can reduce the bootstrap dependency on in-cluster GitLab. | **Planned #80**, not a migration already performed. One authority per repository, one-way promotion, public-content checks and independent image/chart/credential backups are required; GitHub alone cannot recover the platform. |
| Harbor | Controlled artifact storage and project authority provide a destination for reviewed image/chart identities. | Storage is not approval. The current Harbor candidate disables Trivy. Robots, enforced intake, tenant project sync and post-import rescanning remain separate work. Upstream Iron Bank provenance does not prove freshness or zero vulnerabilities. |

## ESO baseline trust update

The [inactive native ESO candidate](../../big-bang-bootstrap/configuration/external-secrets/README.md)
chooses one trusted platform controller for operational simplicity. Its Kubernetes
Secret list/watch authority is cluster-wide and exposes full values, including
unmanaged tenant Secrets. Namespace Stores, class labels and exact OpenBao roles
constrain consumers but are not confidentiality from a compromised controller.
No live grant, credential handling or delivery is claimed by this source update.
Consumers requiring tighter controls should review the documented
[scoped-controller alternative](../../big-bang-bootstrap/configuration/external-secrets/strong-isolation.md),
including per-namespace RBAC, protected controller identities, shared-store
limitations and additional release/resource/acceptance costs.

## Artifact approval before publication

[#79](https://github.com/perkforge/perkforge-platform/issues/79) is the source of
truth for this **planned** pipeline. No intake/publish implementation or policy
threshold is introduced by these diagrams. Current hosted validation gates remain
paused by owner direction; this documentation changes no workflow or gate.

- **Images:** allowlist source/destination; resolve the immutable index/manifest;
  scan every copied runnable platform digest in isolated staging without running
  the image or exposing a Docker socket. Record Trivy JSON, SBOM, tool/database
  versions, timestamps, policy/exception decisions and digest inventory. Findings
  must fail through explicit policy/exit handling; Trivy defaults alone do not gate.
- **Charts:** record exact package SHA256 and OCI identity separately, verify required
  provenance, inventory dependencies and use reviewed `Chart.lock` before fetching.
  Lint/schema-check and render the approved values/Kubernetes-capability matrix
  including CRDs; scan rendered manifests for misconfiguration. Inventory normal,
  init, sidecar, hook, Job and subchart images and apply the image gate. Do not run
  hooks/tests/downloaded scripts. Controller-created, conditional and lookup-derived
  images require explicit coverage or a blocked status.
- **Publish:** a separately authorized publisher verifies trusted producer/ref/job,
  evidence hashes, freshness, policy and destination; caller-supplied “passed” is
  insufficient. Intake has no Harbor write credential; untrusted MRs/forks cannot
  publish. Copy approved image digests, then the exact chart, and verify readback.
  Preserve upstream chart bytes with a reviewed digest-pinned values overlay where
  possible; a repacked chart is a derivative, not upstream-signed content.
- **Stop:** findings outside approved exception, stale/missing databases, scanner
  error/timeout, evidence tampering, missing platform/image coverage or digest drift
  block publication. Maintainers must decide severities, unfixed/EOL treatment,
  database age, signatures, exception owner/expiry and retention before implementation.
  Later Harbor rescans are defense in depth, not a replacement for intake.

## Auditability and assessment

Trace the reviewed change to source commit/release, selected target and actual
reconciliation, then to redacted acceptance evidence. Preserve failures as well as
passes. App authentication logs, Kubernetes API audit, workload logs, artifact
reports and privileged-operation records have different completeness/retention
requirements; a Grafana dashboard or Loki deployment is not proof of an audit trail.
The current logging candidate is platform-admin-only and does not implement a
tenant-safe datasource. Tamper resistance, time synchronization, access control,
retention, review cadence and independent restore require evidence.

The map uses NIST SP 800-53 Rev. 5 control identifiers as **review prompts**, not
implemented controls or a selected DoD baseline. The system owner/assessor must
establish the authorization boundary, applicable baseline/overlays, implementation
statements, inherited controls, test results and accepted residual risks. Policy,
personnel, physical and organizational controls are outside these code diagrams.

## Disclosure and ownership

These checked-in security models are sanitized review material, not a store of
restricted evidence. Platform maintainers own accuracy; identity/network/package
owners review their boundaries; the security owner reviews assessment claims;
the system/data owner approves disclosure. These are **proposed responsibilities**,
not recorded sign-off. Owner assignment/disclosure approval remain open in
[#81](https://github.com/perkforge/perkforge-platform/issues/81).

Build tenant and security roots separately. Restricted models/evidence, if needed,
require separate authorized storage and server-enforced delivery; neither exists
in this change. Do not bundle private content and rely on client-side role hiding.
The [publication contract](../architecture/README.md#audience-builds) also applies
to the portal Explorer, whose [draft integration](https://github.com/perkforge/perkforge-portal/pull/11)
requires its own content/disclosure review. Nothing is deployed or published here.
