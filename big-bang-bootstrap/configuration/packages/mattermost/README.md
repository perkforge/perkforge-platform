# Mattermost: inactive Big Bang candidate

Reviewed 2026-11-08 for MR #116. Both packages remain disabled and suspended,
absent from all cluster roots. Rendering this candidate does not authorize rollout.

## Current package and native values

The repository's Big Bang 3.35.1 umbrella composes Mattermost **12.0.1-bb.2**
(app 12.0.1) and operator **1.25.9-bb.4** (app 1.25.9), the latest package tags
returned by the official repository at review time. Checksummed archives are in
`tests/fixtures/source-pins.yaml`. Big Bang 4.0.0 exists; upgrading the platform
umbrella is a separate change, not bundled into this app MR.

The candidate uses Big Bang's `addons.mattermost` and `addons.mattermostOperator`
interfaces, the packages' `bb-common` integration keys and Mattermost `global`
values. Native image/resource defaults are retained. The explicit registry Secret
reference is only a reference; no registry credential is created or read.

`objectStorage: null` suppresses the old umbrella's bundled MinIO defaults.
The current Mattermost chart rejects any top-level `minio` key and requires
external storage. `fileStore` and `database` retain external Secret references;
no placeholder password, bundled PostgreSQL, Elasticsearch or object store runs.
Endpoints remain UNCONFIGURED. Network policies, monitoring, ingress and mesh
remain off until the actual target's transport/integrations are reviewed.

The exact renders contain eight Mattermost objects and ten operator objects,
including three CRDs. The updated operator adds a namespaced leader-election event
Role/RoleBinding; installer rights name those objects, with no cluster-admin bind.
Both installers are in `bigbang`, separate from the runtime operator identity.

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

The optional `sso-values.yaml` uses native `MM_OPENIDSETTINGS` environment values
and an existing client Secret. Big Bang's `sso.enabled` stays false because that
helper configures GitLab auth rather than Other OIDC. Signup stays closed.
Provisioning/linking, native team/channel membership and offboarding are not
implemented. Team Admin is not System Admin; assigned viewers may chat. No v12.1
ABAC or paid feature assumption is made. See `sso-review.yaml` for acceptance gates.

## Offline validation

Run the two Mattermost security modules using the checksummed fixture sources,
Helm and kubectl, with KUBECONFIG=/dev/null and PYTHONPATH=big-bang-bootstrap/tests.
These verify the real umbrella/child renders, installer permissions, native values,
Secret references, no license and closed-signup OIDC. They do not execute the
operator or prove live storage, network enforcement, login or restore acceptance.
