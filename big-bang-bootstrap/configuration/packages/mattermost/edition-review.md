# Mattermost Entry: source evidence, runtime acceptance pending

The current Big Bang package `11.11.0-bb.0` selects Iron Bank Mattermost `11.11.0`.
The [immutable build manifest](https://repo1.dso.mil/dsop/opensource/mattermost/mattermost/-/blob/58877c06636a6fd0e3e3e8ae18ba90bb4761826b/hardening_manifest.yaml)
is retained as `ironbank-11.11.0-source.yaml`. Its vendor archive is the Enterprise
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
  supported upgrade path. Vendor security patches postdate 11.11.0. This MR deliberately inherits the
  selected Big Bang release rather than overriding its app versions. Review
  that security exposure before activation; release alignment does not prove
  vulnerability-free software. Any exception needs an explicit decision.
- Verify actual Entry/OIDC availability without a trial; retain independent local
  recovery. Review message-history and user limits rather than assuming paid HA,
  compliance, delegated administration or v12.1 ABAC capabilities.
- Review operator trust, TLS, external PostgreSQL/filestore, capacity and restore.
  Separately approve protected client delivery and one linked person with signup
  closed; test MFA, native membership, tenant denial and offboarding.

Source preparation is not a license decision, live SSO acceptance or permission
to deploy. No additional credentials or licensing acceptance were requested.
