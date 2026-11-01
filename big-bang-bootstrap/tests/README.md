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
