# Tenant architecture

A tenant owns its application configuration and data. The platform owns enrollment,
shared infrastructure and the policies between tenants. This is a **source-reviewed
model, not certification of a running tenant**. Reviewed 2026-11-09 against
platform commit `ae3b74b94c83f0bf909a798ea797e049c269fe8c`.

## Join the platform

1. Agree the tenant identifier, app owner, data needs and intended users with the
   platform operator. Do not send credentials in a request or commit them to Git.
2. The platform reviews enrollment: namespace, reconciliation identity, permitted
   repositories, network/data boundaries and independent recovery requirements.
3. The tenant proposes app configuration in its app repository. The platform-owned
   enrollment repository controls which reviewed source the tenant reconciler uses.
4. After release and separate activation approval, verify sign-in, intended access,
   denied cross-tenant access and recovery. A merged configuration is not acceptance.

The full enrollment journey is **planned**; repository ownership and scoped Flux
wiring are **implemented in source**. Existing app pilots do not prove all tenants
are onboarded or isolated. Generic enrollment defaults are suspended; an explicitly
selected stage can override them.

## What separates tenants

| Boundary | Contract | Evidence and limits |
|---|---|---|
| Configuration | Tenant app Git cannot own shared enrollment or platform policy. | [Enrollment source and scoped reconciliation](../../big-bang-bootstrap/enrollments/local/reconcile.yaml) exist. Exact enrollment/app release and effective permissions must be checked for each tenant. |
| Identity and permissions | A shared identity may belong to several tenants. Each app/API must enforce the explicitly granted tenant scope. | [Role matrix](../../big-bang-bootstrap/configuration/authorization/MATRIX.md) is partly design intent. Login alone does not prove resource access or isolation. |
| Workloads and traffic | Namespaces organize resources; scoped identities, admission and allowed traffic must enforce separation. | End-to-end denial acceptance and complete ingress/egress policy are **unverified/planned** under [#21](https://github.com/perkforge/perkforge-platform/issues/21), [#43](https://github.com/perkforge/perkforge-platform/issues/43) and [#44](https://github.com/perkforge/perkforge-platform/issues/44). A namespace is not a complete security boundary. |
| Data and recovery | Applications use their own approved data/secret scope; backup and restore must preserve that scope. | Per-app implementation varies. Independent restore and administrator access require explicit review; storage replication is not backup. |

Ordinary tenant users should have no access to another tenant. **Trusted platform,
identity, host, storage and backup administrators can bypass nominal app boundaries.**
Do not assume confidentiality from those administrators. Tenant-approved elevation,
complete revocation and adversarial isolation evidence are not established here.

## Shared responsibilities

- **Platform:** approve enrollment and privileged policy, maintain shared services,
  review releases, protect recovery custody and demonstrate allowed/denied boundaries.
- **Tenant:** review its app changes and users, classify its data, protect app secrets,
  and agree recovery needs. Do not treat an app release as permission to change the platform.
- **Together:** accept the specific deployed revision, permissions, retention,
  offboarding and restore results before relying on them.

## Models and reuse

`tenant_context`, `tenant_boundaries` and `tenant_onboarding` are intentionally
small. **Implemented (source)** means reviewed code exists; **planned** means the
workflow/control is not complete; **unverified** means the claimed runtime outcome
has not been established by this review. No live checks ran.

Use the [local viewer commands and publication rules](../architecture/README.md#audience-builds).
This source root contains generic tenant concepts only, with no tenant inventory,
private endpoints or reviewer/operator model payload. A tenant download must never
include those other bundles, even if navigation hides them.
