# Mattermost Entry: source evidence, runtime acceptance pending

The current Big Bang package `12.0.1-bb.2` selects Iron Bank Mattermost `12.0.1`.
The [immutable build manifest](https://repo1.dso.mil/dsop/opensource/mattermost/mattermost/-/blob/a119147cd04982c52d2625d1396cce5f163d2b32/hardening_manifest.yaml)
is retained as `ironbank-12.0.1-source.yaml`. Its vendor archive is the Enterprise
binary distribution (`mattermost-`, not `mattermost-team-`). The SHA256 is tested
against that source record; no image pull, digest inspection or runtime test ran.

[Vendor editions](https://docs.mattermost.com/product-overview/editions-and-offerings)
and [Other OIDC guidance](https://docs.mattermost.com/administration-guide/onboard/sso-openidconnect)
previously identified Entry and Keycloak support. That is a planning basis, not
proof of the exact binary's entitlement or enabled features. `enterprise.enabled:
false` controls license Secret wiring only. No trial or license was activated.

Before activation:

- Review the [Enterprise license](https://mattermost.com/enterprise-edition-license/)
  and intended use. Free availability is not a production/PaaS entitlement.
- Verify image digest, current security advisories and the selected release's
  supported upgrade path. The Iron Bank source already has a 12.0.2 manifest at
  review time, while the newest Big Bang package still selects 12.0.1. Latest
  package is not a claim of latest vendor patch or vulnerability-free software.
- Verify actual Entry/OIDC availability without a trial; retain independent local
  recovery. Review message-history and user limits rather than assuming paid HA,
  compliance, delegated administration or v12.1 ABAC capabilities.
- Review operator trust, TLS, external PostgreSQL/filestore, capacity and restore.
  Separately approve protected client delivery and one linked person with signup
  closed; test MFA, native membership, tenant denial and offboarding.

Source preparation is not a license decision, live SSO acceptance or permission
to deploy. No additional credentials or licensing acceptance were requested.
