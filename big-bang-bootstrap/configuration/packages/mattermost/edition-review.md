# Mattermost Entry and SSO — source verified, runtime acceptance pending

The pinned chart `11.11.0-bb.0` selects
`registry1.dso.mil/ironbank/opensource/mattermost/mattermost:11.11.0`.
The [immutable Iron Bank build manifest](https://repo1.dso.mil/dsop/opensource/mattermost/mattermost/-/blob/58877c06636a6fd0e3e3e8ae18ba90bb4761826b/hardening_manifest.yaml)
uses the vendor `mattermost-11.11.0-linux-amd64.tar.gz` distribution, SHA256
`03dfa47063849fe9e799c9523c56c74ec19852948e6fc42d9fc3e10cc5d95bc9`.
The source manifest is retained alongside this review. This is the Enterprise
binary distribution; Team Edition archives use the `mattermost-team-` prefix.
The chart's `enterprise.enabled: false` controls license wiring, not which binary
is installed. No image digest inspection or runtime feature test occurred here.

[Vendor editions documentation](https://docs.mattermost.com/product-overview/editions-and-offerings)
says Enterprise runs without an activated subscription as Entry. The
[OIDC guide](https://docs.mattermost.com/administration-guide/onboard/sso-openidconnect)
explicitly lists Entry and Keycloak via Other OIDC. Therefore Entry is a supported
**SSO testing candidate**, rather than assuming a paid subscription is required.
The optional native OIDC environment overlay remains unselected, signup closed,
with client-secret references only. No trial, paid license or account was created.

**Decisions before tomorrow's activation:**

- Keep the reviewed pin or separately review a patched Big Bang package/image.
  The [v11 changelog](https://docs.mattermost.com/product-overview/mattermost-v11-changelog)
  lists 11.11.2/11.11.3 security updates after 11.11.0. No silent upgrade is made.
- The [current free Enterprise license](https://mattermost.com/enterprise-edition-license/)
  limits use to evaluation/testing/non-production. Entry being free is not a
  production entitlement; terms/applicability need owner review before use.
- Verify the actual immutable image/binary edition and OIDC feature availability
  without a trial/license. Source selection does not prove a running entitlement.
- Review the cluster-wide operator trust, PostgreSQL/filestore/TLS/capacity,
  independent local admin recovery and protected client delivery before rollout.
- Explicitly provision/link one approved person with signup closed, test fresh
  Keycloak MFA and native membership/denial/offboarding. Team Admin must stay
  distinct from System Admin; ordinary assigned viewers may chat. OIDC itself
  does not synchronize team/channel memberships. Do not add v12.1 ABAC assumptions.

The native overlay and rendered CR are preparation, not a complete client/native
membership executor or successful live SSO acceptance.
