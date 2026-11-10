# Native External Secrets Operator

**Implemented source, inactive candidate.** The initial baseline uses one trusted
platform controller from Big Bang's native `addons.externalSecrets`. Big Bang
3.35.1 selects wrapper **2.12.0-bb.0**, upstream/image **2.12.0**. Version and image
values are inherited, not independently overridden. There is no custom ESO
package, chart fork, second controller or alternate deployment owner.

[Issue #31](https://github.com/perkforge/perkforge-platform/issues/31) owns shared
secret distribution. Only approved consumers receive values; OpenBao remains the
runtime source of truth and Bitwarden remains separately approved recovery custody.
No root/unseal material, signing keys or personal tokens belong in app records.

## What this change prepares

- `clusters/local-external-secrets` extends `local-velero`, retaining the existing
  Nextcloud and platform composition. No existing root selects it. Native ESO is
  additionally suspended, and provider egress is deliberately unconfigured.
- [Native values](runtime/native-values.yaml) disable unused cluster-external,
  push and generator features. Existing Big Bang package/image defaults and
  monitoring integration remain native.
- [Foundation](prerequisites/foundation.yaml) separates namespaced Helm installation
  from controller authority. The default-off
  [prerequisite playbook](../ansible/external-secrets-prerequisites.yaml) verifies
  release/target and exact public CRD bytes before any approved application.
  It never fetches code, handles credentials, selects a root or resumes a release.
- [Platform store](stores/platform/store.yaml): cluster-scoped `openbao-platform`,
  initially usable only in `external-secrets`. The machine policy is lookup-only:
  no platform data reads are implicitly approved. Each first consumer needs its
  exact namespace/record/field/destination added in reviewed source.
- [Machine authentication](openbao/README.md): separate `kubernetes-eso` mount,
  exact ServiceAccount/namespace/audience roles, 5-minute tokens with a 15-minute
  explicit maximum, no default policy. TokenReview delegation is a separate
  narrowly defined security prerequisite.
- The platform-owned enrollment repository owns each tenant's namespaced
  `openbao-tenant` Store and auth identity. [Tenant follow-up PR #51](https://github.com/perkforge/perkforge-platform-tenants/pull/51)
  is a separate inactive stage, dependent on Portal enrollment #50. The first proposed physical Portal
  scope is `tenant-portal`; see [ownership and exact record contract](stores/README.md).
  It is not a migration from the former VM namespace or credential paths.

No ExternalSecret consumer, secret record, CA placeholder, private value, live
grant, release promotion or workload restart is included. The candidate is
reviewable preparation, not an assertion that ESO is running or synchronizing.

## Explicit controller trust boundary

**This controller can read Kubernetes Secrets in every namespace.** Exact ESO
2.12.0 source unconditionally registers a Secret metadata informer. Kubernetes
`list`/`watch` RBAC can retrieve full Secret contents; it cannot enforce
metadata-only access. Disabling caches or omitting global `get` does not remove
that exposure. The foundation explicitly grants only global Secret `list/watch`,
plus required nonsecret informer reads, and limits writes and TokenRequest calls
to reviewed namespace Roles and exact auth ServiceAccounts.

Scoped Stores and OpenBao ACLs protect against tenant users and unauthorized
consumer declarations. They do **not** make secrets confidential from a compromised
ESO controller, platform cluster administrator, or another privileged recovery
operator. Compromise of ESO may expose all existing Kubernetes Secrets, including
those it does not manage, as well as every path its approved machine roles can
read. Treat controller upgrades, image/pull credentials, RBAC, auth mounts and
Store authorship as privileged platform changes.

Controller class `perkforge` is routing, not authorization. The pinned controller
also accepts Stores with an empty class. Tenant app deployers must have no Store,
ExternalSecret, ServiceAccount, RBAC or TokenRequest mutation authority. Workload
admission must prevent selecting auth/controller SAs or mounting projected tokens;
`automountServiceAccountToken: false` by itself is insufficient. Platform Store
conditions explicitly exclude tenant namespaces; do not substitute a broad label
selector. Use [scoped controllers](strong-isolation.md) when this baseline's
operator trust exceeds the consumer's requirements.

## Ordered activation gates

A merge or release does not authorize these operations. Use clean immutable source
and exact target identities; inspect current state and stop on ownership drift.

1. Review exact native umbrella and child renders, controller authority, available
   resources, existing CRDs and recovery. Obtain explicit installation/security
   approval. Prepare the checksum-verified native CRD bundle locally, then run
   `external-secrets-prerequisites.yaml` only with its explicit scope/apply inputs.
   It creates only missing CRDs with a dedicated field manager, refuses unowned
   or differing existing state, never force-conflicts, and waits for establishment.
   Existing exact owned objects are read and left unchanged; a concurrent create
   fails rather than adopting the new object. The Helm installer receives no persistent CRD/RBAC
   administration. Future native pin changes need a newly reviewed CRD stage.
2. Review the native default-deny/DNS/API/metrics policies and add the exact
   OpenBao HTTPS route in runtime values. The generic native `0.0.0.0/0:443`
   provider rule is disabled. Physical addresses belong in protected target inputs,
   not tracked values. Verify actual service routing, TLS hostname/SAN and CA;
   DNS presence does not prove reachability or certificate validity.
3. Separately approve the existing Registry1 pull-secret delivery to the ESO
   namespace, exact auth TokenReview grant, and machine-auth adapter operation.
   Verify OpenBao recovery and existing initialized/unsealed cluster identity.
   Never initialize it again, reuse the human/legacy mixed API playbook, copy a
   static reviewer JWT, or move root/unseal material into runtime records.
4. Deliver the separately verified public OpenBao CA to
   `external-secrets/openbao-ca` (`ca.crt`). Tenant CA trust is its own
   `eso-openbao-ca` ConfigMap, not an assumption about Keycloak trust.
5. After review, publish the completed network/activation values and separately
   select that release/root and resume the native release through GitOps. Preserve
   all existing selected apps and sources. Verify controller startup and readiness.
6. Only after CRDs/controller/auth/trust are ready, separately apply the tracked
   platform Store/auth identity and enrollment's tenant Store stage. No active
   root includes these early, so absent CRDs cannot break normal reconciliation.
7. Review exact record population and ExternalSecret consumer mappings before
   first delivery. Check existing/immutable target Secret ownership and preserve
   current values. Approve a bounded synthetic acceptance batch before testing
   auth, data or rotation. Do not automatically delete values or restart apps.

The source does not implement automatic root selection, provider-network discovery,
registry/CA delivery, consumer population or cleanup. Those remain explicit
operator stages rather than hidden side effects of controller installation.

## Validation and limits

Run from the repository root with `KUBECONFIG=/dev/null`. Native chart tests use
`ESO_CHART_SOURCE` pointing to the verified extracted wrapper source (containing
`chart/`), `PREFLIGHT_SOURCES_DIR` containing Big Bang 3.35.1, and Helm on PATH.
See [pins](source-pin.yaml) and [test setup](../../tests/README.md).

```sh
PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest \
  bootstrap.test_external_secrets_native bootstrap.test_external_secrets_foundation \
  security.test_external_secrets_stores -v
RUN_OPENBAO_POLICY_TESTS=1 OPENBAO_POLICY_TEST_BINARY=/ABSOLUTE/existing/bao \
  PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest \
  security.test_external_secrets_stores -v
```

The native OpenBao test uses the existing pinned 2.7.2 binary, synthetic values,
root-minted test tokens and a loopback memory-only server. It validates actual ACL
allow/deny and auth-role API compatibility, not Kubernetes login or inherited
identity enforcement. HTTPS adapter fixtures exercise real Ansible against a
synthetic server, not production authentication. Required live acceptance includes
wrong SA/namespace/audience denial, exact Store namespace restrictions, unrelated
namespace write/token denial, correct public TLS, no unexpected secret exposure
in logs, exact consumer mapping/rotation and preservation of existing resources.
