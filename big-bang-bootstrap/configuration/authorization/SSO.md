# Coordinated platform application SSO

Local preparation for one coordinated Headlamp, Rancher and OpenBao change.
This document is not activation approval or evidence of deployed SSO. All existing
application enable flags remain false. No credentials, memberships, grants,
deployments, authentication providers or control-plane configuration are changed.

## Ownership and sequence

Ansible owns three separate Keycloak clients and native application configuration.
Flux/Big Bang owns workload deployment; RKE2 provisioning owns API-server trust.
Use the merged MATRIX.md and C4 as the permission contract. Deliver one reviewed
MR, modular application files, and independently approved activation/rollback.
Acceptance order: Headlamp, Rancher, OpenBao. A failed stage blocks later stages;
rollback never removes another application's client, sessions or recovery path.

Use reviewed external environment inputs for realm/issuer, application origins,
exact callbacks, cluster UID/context, public CA bundle and private credential-file
references. Never bake physical identifiers, private credentials or one environment's
hosts aliases into reusable templates. Verify certificate chain, SAN, discovery
issuer and DNS from browser, workloads and API server. Public CA material may be
packaged as trust; a public issuer still requires explicit trust validation.

## Local source preparation

`sso/prepare.yaml` renders four private, nonsecret YAML review payloads from
`sso/desired.yaml` and explicit external environment overrides: separate client
representations plus independent Headlamp, Rancher and OpenBao contracts. Default
and check mode do not render, contact APIs or read credentials. Every app apply
flag must remain false; the preparation entrypoint refuses activation. Fresh
output-directory ownership prevents overwriting earlier review evidence.

The initial payload stage grants no live permissions and proposes PA only. It
uses the built-in client-role mapper bound to one exact client, with explicit
own-client scope roles and group-to-client-role mappings, rather than publishing
all canonical memberships. Canonical role/client IDs and mapper ownership are verified by the shared client
adapter, and native adapters have independent default-off inspect/apply/rollback
entrypoints. See [the supported procedure](sso/README.md) for private input delivery,
per-app sequencing, recovery, rollback and live acceptance gates. Tenant/engineer
activation is not part of the initial PA-only stage. Real product token/UI behavior
remains live acceptance, distinct from synthetic API fixtures.

`tests/security/test_platform_sso.py` executes Ansible and checks noncontacting
default/check behavior, independent disabled flags, exact audience/claims, duplicate
client/invalid endpoint/master-realm refusal, preserved output permissions,
environment portability and each application's distinct authorization boundary.
This is configuration-payload evidence, not live SSO enforcement evidence.

## Client and claim contract

Separate audiences/clients: headlamp-local, rancher and openbao are existing pilot
identifiers, not universal environment names. Require distinct nonempty IDs per
environment. Authorization-code flow only; no implicit/password/service-account
flow. Exact redirect URIs, no wildcard origins, no broad fullScopeAllowed.
Use PKCE S256 where the pinned application/provider supports it. Private credentials
stay in owned mode-0600 external files/private Kubernetes Secret delivery, never
rendered review output, logs, argv, tracked files or CI artifacts.

A generic full-path membership mapper exposes every tenant group to every client.
Do not reuse that review specimen unchanged. Select and test a supported bounded
per-client claim mechanism (such as explicit client roles mapped from canonical
groups). Preserve canonical group ownership and explicit per-app native role
translation. Parent groups grant nothing. No engineer role until diagnostic scopes
are decided. Do not equate all viewers or tenant memberships across products.

## Headlamp module

Reuse packages/headlamp/oidc.yaml and identity/kubernetes/rke2-oidc.yaml only after
parameterization and inspection of the installed versions/API authentication path.
Headlamp forwards a user's bearer token; Kubernetes validates issuer, audience,
algorithm, azp, username/groups claims and CA, then Kubernetes RBAC authorizes it.
The configured claim/prefix must match exact RBAC subjects. PA cluster-admin is a
powerful boundary, including Kubernetes Secret access; never describe it as
metadata-only tenant privacy. PV/tenant views require explicit resource scopes;
Kubernetes Secret LIST returns values and cannot provide names-only access.

Preflight must establish that API OIDC settings already match. Missing or different
API-server trust is a hard stop requiring separate provisioning/restart review;
this coordinated application play must not write RKE2 config or restart anything.
Do not restore the revoked temporary admin token. Recovery is existing independent
cluster-admin access, verified before human SSO acceptance.

## Rancher module

Inspect pinned Rancher version, auth provider schemas and current provider metadata
before choosing Generic OIDC versus native Keycloak OIDC. The existing
configure-rancher-oidc.yaml is a candidate, not proof that native Keycloak provider
principal IDs or fields are interchangeable. No automatic provider migration.
Keep local recovery enabled. Require exact provider type, ownership and cluster
identity; refuse competing enabled external providers. Preserve existing user/global
bindings. PA is the only initial admin group; tenant/developer/engineer users get no
Rancher login/admin binding. Review how provider group identity survives name
changes, group search, removal and session expiry. Check issuer trust from Rancher.

## OpenBao module

Reuse the JWT/OIDC roles/policy concepts, not the old platform-config/configure.yaml
activation wrapper. It also reconciles Kubernetes auth, machine identities/mounts
and legacy broad tenant-value permissions. Those operations are outside this SSO
change. Preserve current machine auth, unseal/recovery custody, mounts, policies and
existing sessions until an explicit migration/revocation plan is approved.

Initial PA policy: platform value read/edit and tenant names LIST only; no standing
tenant data reads, sys/auth/policy administration, destroy/version purge or default
policy inheritance. Tenant-admin/developer/viewer policies remain own-tenant and
are activated only for explicit reviewed tenant inputs; empty tenant inventory
must create no tenant roles. Never apply legacy human-platform-tenant-access.hcl
(the file grants tenant values) as nominal PA authority. Do not change retention or
create engines as a side effect of SSO.

Require exact audience, issuer, subject, client-specific claim binding and redirects;
no default login role. Bound role grants only approved policies. Existing identity
entities/external aliases and inherited policies must be inspected before migration:
removing a role's policy alone does not prove previously issued tokens/aliases lose
access. Explicit revocation/expiry plan and independent operator recovery required.

## Tests and acceptance

Offline API fixtures must model actual pinned pre/post-write responses. For each
module test default/check no-contact behavior; wrong environment/UID/CA; unowned
or duplicate client/provider; existing-client adoption refusal; exact callback and
claim allowlists; wrong issuer/audience/azp/algorithm/expiry; foreign app-token
replay; unknown/parent/no-group membership; extra roles; secret redaction; partial
write/readback failure; interruption recovery; normal second run with zero writes;
and rollback preserving other apps and recovery. Test removals and old sessions,
not merely additive admission or visible menus.

Headlamp: authenticated PA positive, ungranted negative, API-level authorization,
claim-prefix mismatch and rejected cross-client token; no mutation of real tenant
resources to prove a UI control. Rancher: PA admin positive, tenant/no-group login
negative, local recovery preserved, exact provider principals and membership
removal/expiry. OpenBao: capability checks plus disposable isolated test values
under separately approved test paths; PA denied tenant values; tenant A denied B;
TD read allowed/write denied; TV names allowed/value denied; no auth/policy self-
grant, metadata deletion or destroy. Any disposable identities/data require separate
live approval; synthetic identities remain offline fixtures meanwhile.

Operator fresh-MFA browser acceptance is distinct from automated metadata checks.
Do not authenticate as the owner, reset credentials or broaden live grants to test.
Report version/schema assumptions and all remaining gates rather than claiming
rendered artifacts prove enforcement. Publish only after the combined local diff
and tests receive separate publication approval.

## Read-only preparation observations

2026-11-02: installed Rancher image is v2.15.2. Authconfig metadata has local
provider enabled and distinct genericoidc and keycloakoidc objects (neither external
provider reports enabled). Schema and principal compatibility still need fixture
validation; presence of an object is not proof of a complete working integration.
The API-server pod exposes 41 arguments but no --oidc-* or
--authentication-config flag and no identity/OIDC/authentication trust mount.
Existing API trust is therefore not established. Headlamp's live stage cannot
proceed under the current no-restart/no-provisioning scope.

These observations did not read credentials or change providers/control-plane.
Legacy policy findings above are source evidence, not a claim of current live
OpenBao policy assignment. Actual live alias/token/policy inventory remains a
separate GET-only preflight using an existing approved operator credential.

## Upstream references

- https://headlamp.dev/docs/latest/installation/in-cluster/oidc/
- https://ranchermanager.docs.rancher.com/how-to-guides/new-user-guides/authentication-permissions-and-global-configuration/authentication-config/configure-keycloak-oidc
- https://openbao.org/docs/auth/jwt/
- https://openbao.org/docs/api/auth/jwt/

- Keycloak pinned mapper: https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/protocol/oidc/mappers/UserClientRoleMappingMapper.java
