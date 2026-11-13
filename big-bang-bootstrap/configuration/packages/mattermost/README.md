# Mattermost: inactive Big Bang candidate

Reviewed 2026-11-08 for MR #116. Both packages remain disabled and suspended,
absent from all cluster roots. Rendering this candidate does not authorize rollout.

## Current package and native values

The selected Big Bang **3.35.1** release is the version authority. The candidate
contains no package Git/tag or image-version override. Its defaults select
Mattermost **11.11.0-bb.0** (app 11.11.0) and operator **1.25.9-bb.1**.
Checksummed test fixtures match those release values; a regression checks equality.
Newer independent package releases are not selected by this MR.

The candidate uses native `addons.mattermost` and `addons.mattermostOperator`
values and inherited chart defaults. Bundled PostgreSQL/MinIO/Elasticsearch are
disabled. External `mattermost-database` and `mattermost-filestore` Secret
references remain; endpoints are unconfigured until operator preparation.
Native registry references are wired for the app CR, operator and readiness Job;
namespace-specific `private-registry` delivery remains a prerequisite. No registry
credential is created or read.

The exact renders contain eight Mattermost objects and eight operator objects,
including three CRDs. Both installer identities live in `bigbang`, separate from
the runtime operator. No cluster-admin binding is added.

## Remaining deployment gates

- The upstream operator still has cluster-wide wildcard authority, including
  Secrets and workloads. This trust decision is unapproved; there is no silent
  RBAC fork or namespace-isolation claim.
- The native wait hook still emits unrestricted any-port egress even with general
  network policies disabled. Keep readiness; review API-only transport before use.
- Review exact image digest/security status, [edition and license](edition-review.md),
  Kubernetes compatibility and cumulative app/operator/data-service capacity.
- Prepare separately approved external PostgreSQL and S3 storage, trusted TLS,
  restricted routing, protected Secret delivery and independent restore evidence.
- Establish independent local administration with restricted signup before SSO.
  No human credentials, account grants, activation or deployment occurs here.

## Entry and Keycloak OIDC

Entry remains the planned free mode of the Enterprise binary, not a paid trial.
`enterprise.enabled: false` disables license wiring; it does not establish rights
or runtime features. Source evidence and runtime acceptance are distinct.

The `sso-values.yaml` contract uses native `MM_OPENIDSETTINGS` environment values
and an existing client Secret, plus a read-only public CA mount through
`SSL_CERT_FILE`. The [SSO preparation](../../authorization/sso/mattermost/README.md)
prepares the disabled Keycloak client and public app values together. Big Bang's `sso.enabled` stays false because that
helper configures GitLab auth rather than Other OIDC. Signup stays closed.
Initial person provisioning/linking, native team/channel membership and
offboarding remain separate acceptance requirements. Team Admin is not System Admin; assigned viewers may chat. No v12.1
ABAC or paid feature assumption is made. See `sso-review.yaml` for acceptance gates.

## Offline validation

Run the Mattermost security modules using the checksummed fixture sources,
Helm and kubectl, with KUBECONFIG=/dev/null and PYTHONPATH=big-bang-bootstrap/tests.
These verify the real umbrella/child renders, installer permissions, native values,
Secret references, no license and closed-signup OIDC. The SSO modules also execute
Ansible against disposable HTTPS and kubectl fixtures for client/input lifecycle.
They do not execute the
operator or prove live storage, network enforcement, login or restore acceptance.

## Integrated Portal pilot

The [native context acceptance check](../../authorization/sso/mattermost/context/README.md)
verifies the configured private team/channel, exact reviewed membership and
channel-locked incoming webhook without changing access. Portal shares its tenant
context with GitLab, Grafana and ntfy; tenant viewers may participate in channels
and see their alerts but are not direct notification subscribers. Native
provisioning, identity linkage and cross-tenant denial remain live acceptance,
not capabilities implied by Keycloak login or source-only fixture checks.
