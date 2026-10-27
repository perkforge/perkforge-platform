# Portal admission workload fixture

`workload.json` is the output of tenant portal commit
`ecafe09a497e971a4a4af04a331d837e4e1a146a`, rendered with Helm3.19, the platform
non-secret values and **test-only** enabled=true/image digest of 64 `a` characters.
That digest is synthetic and is never written into the platform contract.

CI checks out the exact tenant revision from the contract, renders its chart and
compares the complete output to this fixture. It then renders malicious identity/
origin/Secret overrides and evaluates generated policies using Kubernetes1.36.5
admission CEL. Additional cases exercise pod/controller and injection boundaries.

Offline fixture-only execution needs Helm for platform templates, but no tenant checkout.
Set PORTAL_CHART_DIR to an exact reviewed chart checkout to enable real rendering
comparisons and negative chart-value cases; HELM can override the executable path.


`template-baseline.json` freezes semantic SHA-256 fingerprints captured from commit
`f8648170fc08130a4e20101bb038b1adee049136` before replacing Python object/CEL
construction with Helm templates. It covers disabled, active and paused catalog
fixtures from `test_portal_catalog_lifecycle.py`: current catalog for disabled;
explicit synthetic image/allocation/budget for active/paused. Each includes the
full foundation plus all four application preview artifacts. Document order and
embedded ConfigMap values-YAML formatting are normalized, but every field and CEL
string is retained. This is a refactor regression guard alongside the readable
behavioral/admission tests, not evidence of live enforcement. An intentional
contract change needs reviewed fixture updates; do not refresh hashes just to
make an unexplained difference pass.
