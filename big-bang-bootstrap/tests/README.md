# Verification by responsibility and execution risk

| Directory | Checks | Execution |
|---|---|---|
| configuration/ | full pinned renders, inventory, precedence, target/profile/release contracts | local kubectl kustomize/Helm, no cluster |
| bootstrap/ | seed/source defaults, release refusal, private-input gates, realm/readiness operation defaults | local Ansible with disabled/mock targets |
| security/ | effective installer/user permissions, OIDC/API contracts, native Flux admission CEL | synthetic objects and pinned schemas, no cluster |
| integration/ | real Ansible/Helm behavior against disposable loopback HTTPS/API fixtures | offline integration; loopback sockets, never a real cluster |
| fixtures/ | genuinely shared chart pins, schemas, released metadata, rendering/API fixture helpers | test data/construction only |

Configuration/test_optional_enrollment checks a tenant-free root preserves platform objects; bootstrap/test_prerequisites checks package ownership, unique definitions and explicit common-first ordering.

The former Headlamp/identity mixed modules were split case-by-case. Shared rendered package setup has no test cases. Release/seed checks are separate from cross-repo configuration tests; generic findings tests live at repository-root evidence/tests, and infrastructure RKE2 tests stay with infrastructure/ansible/tests; Rancher API safety tests live in bootstrap/test_rancher_management.py with the platform operation. No test is labelled live integration when it only exercises a fixture.

## Offline commands

Grafana SSO claim evaluation requires `jmespath==1.0.1` in the test Python
environment (`python3 -m pip install jmespath==1.0.1`). It is imported when the
claim test executes, so discovery-only audits need no extra dependency; an actual
run without it fails rather than skipping the authorization checks.

Use the pinned source downloader `tests/fixtures/fetch_sources.py <temporary-directory>` only to obtain checksummed public fixtures. Full render tests require PREFLIGHT_SOURCES_DIR plus actual released ENROLLMENT_CHECKOUT/TENANT_APP_CHECKOUT; the portal boundary tests use corresponding PORTAL_ENROLLMENT_CHECKOUT/PORTAL_APP_CHECKOUT. CI resolves/verifies those refs before checkout.

```sh
KUBECONFIG=/dev/null python3 -m unittest discover -s big-bang-bootstrap/tests -v
python3 -m unittest discover -s infrastructure/ansible/tests -v
python3 -m unittest discover -s evidence/tests -v
```

The first command requires those fixture inputs. RUN_PLATFORM_CONFIG_TESTS=1 and RUN_PORTAL_IDENTITY_TESTS=1 explicitly enable real Ansible against synthetic loopback APIs; they do not enable production APIs. Exact commands/tool versions and CEL environment inputs are in .github/workflows/gitops-selection.yml. Never point fake-API tests at an actual kubeconfig.

## Live testing is separate

No default unittest command performs live cluster integration. Existing identity-verify.yaml requires explicit live approval and external signed test tokens; real browser/session, effective API denials, storage persistence, controller startup, capacity and recovery must be verified against the chosen target after code review. Archived catalog probes require adaptation before use. Do not add empty speculative suites or treat fixture passes as physical readiness/IL authorization.

Resource inventories cover the explicitly selected Big Bang/application charts, not the entire cluster. RKE2/CNI/ingress/storage systems and Rancher-installed management dependencies need separate measured capacity/readiness validation.

`bootstrap/test_platform_tls.py` executes TLS validation/delivery tasks against
synthetic local certificates and an isolated CLI state fixture. It checks exact
Secret/CA content, log redaction, existing-resource refusal and mismatched-key
rejection before any API call. This is offline evidence, not live Secret delivery.

The authoritative local-root regression renders only active Longhorn behind the separately tested paused seed and checks identity/tenant packages are absent. Identity and capacity tests explicitly compose their application fixtures; those inventory totals do not describe the initial Longhorn-only rollout. Fixture opt-in never changes operator selection.

bootstrap/test_flux_registry uses synthetic credentials and a mock CLI to verify default/check refusal, explicit creation, redaction, reuse without local files, unsafe-file and overwrite refusal, and credential ordering before controller apply. It makes no live registry or cluster calls.

`integration/test_longhorn_lookup.py` uses the existing loopback API fixture and
real pinned Helm server rendering to cover the unnamed ClusterRole list lookup.
It rejects the old/name-restricted policies and proves the exact list-only rule
allows rendering with PSP and ingress disabled. This authorization model uses
synthetic discovery/roles, not a live cluster or real credentials.

`security/test_longhorn_installer.py` renders the pinned Longhorn child and checks
all resource CRUD, role escalation and binding roleRefs against the bound installer
policy. Removing the named cluster-admin bind reproduces only the diagnostic
binding denial. This offline model does not replace Kubernetes admission or live
storage acceptance; the lab explicitly accepts upstream runtime RBAC trust.

`bootstrap/test_longhorn_storage_smoke.py` proves default/check mode makes no API
calls, renders the actual restricted pod/1Gi claim templates and checks positive
replica health plus co-location, degraded/RW-mode and failed-replica negatives.
The live Ansible smoke is separately approved, retains storage and is not invoked
by this unittest suite. See the Longhorn package procedure for its observed result.

`integration/test_metrics_worker_placement.py` compares default, CRD-only,
limited-metrics and limited-logging renders, preserving all objects except the
two PVC consumer selectors and derived values checksums. The separate mandatory
`metrics-placement` CI job additionally sets `REQUIRE_NATIVE_OPERATOR_PLACEMENT=1`
and `PROMETHEUS_OPERATOR_SOURCE` to the verified public operator source and runs:

```sh
KUBECONFIG=/dev/null PYTHONPATH=big-bang-bootstrap/tests \
  python3 -m unittest integration.test_metrics_worker_placement -v
```

Provide `PREFLIGHT_SOURCES_DIR`, the two native-test variables above and Go/Helm
on PATH to reproduce native coverage locally. It feeds the actual rendered
Prometheus CR to the pinned operator's StatefulSet generator, verifies Kubernetes
label matching excludes the observed unlabelled control-plane and accepts both
labelled workers, and compares the entire generated StatefulSet after removing
only its new selector. This is scheduling-constraint evidence; it does not prove
live CSI mounts, scheduler decisions, free capacity or storage persistence.

`integration/test_metrics_registry_pull_refs.py` reproduces the empty-reference
failure through the real umbrella and child charts across seven default/review/
CRD/full/limited roots. It checks every limited-pilot Pod/CR consumer and native
monitoring ServiceAccount, including admission hooks. Exact equality after removing
only those references preserves other app inputs, credentials, RBAC, images,
resources, security, placement and storage. The existing `metrics-placement` job
runs it with the native operator source; the generated StatefulSet must retain
`private-registry` for both Prometheus and its reloader. Broader roots' deferred
blackbox exporter is explicitly asserted unchanged, not claimed covered. No
registry authentication, actual pull, live recovery or Secret value is tested.

`bootstrap/test_bitwarden_bootstrap.py` exercises real Ansible against synthetic
Bitwarden CLI and trusted loopback HTTPS fixtures. Run with
`PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest bootstrap.test_bitwarden_bootstrap -v`.
Default/check modes never access a vault or server. No real credentials are used.
Native KV-v2/ACL checks use the existing pinned OpenBao 2.7.2 binary, without a
download, kubeconfig or operator token:

```sh
KUBECONFIG=/dev/null RUN_OPENBAO_POLICY_TESTS=1 \
  OPENBAO_POLICY_TEST_BINARY=/ABSOLUTE/existing/bao \
  PYTHONPATH=big-bang-bootstrap/tests \
  python3 -m unittest bootstrap.test_bitwarden_bootstrap.NativeOpenBaoBootstrap -v
```

## Native ESO candidate

The source remains unselected/suspended and CI's existing pause is unchanged.
`fetch_sources.py` includes the checksummed native ESO wrapper and its vendored
dependencies. Set `ESO_CHART_SOURCE=$PREFLIGHT_SOURCES_DIR/external-secrets` and
`ESO_CRD_BUNDLE=$ESO_CHART_SOURCE/chart/crds/bundle.yaml`; JSON-schema validation
requires `jsonschema==4.25.1` in the test environment. The paused selection job is
wired to these inputs for when its existing gates are restored separately.

```sh
KUBECONFIG=/dev/null PYTHONPATH=big-bang-bootstrap/tests \
  RUN_PLATFORM_CONFIG_TESTS=1 python3 -m unittest \
  bootstrap.test_external_secrets_native bootstrap.test_external_secrets_foundation \
  integration.test_openbao_eso \
  security.test_external_secrets_stores -v
```

Schema validation checks the actual pinned served v1 schema, not upstream CEL
admission. The real Ansible HTTPS test uses synthetic credentials and a copied
fixture release/checkout check; it proves API ordering, conflict refusal,
idempotence and redaction, not remote publication or physical readiness.
Optional native OpenBao ACL tests reuse the existing `RUN_OPENBAO_POLICY_TESTS=1`
and `OPENBAO_POLICY_TEST_BINARY` setup above. They validate exact read/deny paths
and role API compatibility, not Kubernetes JWT login or actual ESO synchronization.

`integration/test_tenant_query_gateway.py` runs the actual inactive Ansible
renderer, native Nginx TLS/auth and checksum-pinned prom-label-proxy against a
synthetic recording backend. Supply `PROM_LABEL_PROXY_BIN` as documented in
[the gateway slice](../configuration/observability/tenant-query/README.md).
It tests query rewriting and authentication, not real Prometheus data, Grafana
org boundaries, ingestion authenticity or deployed network isolation.

`integration/test_tenant_query_data_plane.py` extends that evidence with pinned
Grafana 13.2.1 and Prometheus 3.14.0: real synthetic series, upstream mTLS,
per-org roles, custom-datasource attacks and query-model API denials. See the same
gateway README for binary inputs and the remaining deployed/plugin/ingestion gaps.
