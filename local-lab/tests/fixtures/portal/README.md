# Portal admission workload fixture

`workload.json` is the output of tenant portal commit
`ecafe09a497e971a4a4af04a331d837e4e1a146a`, rendered with Helm3.19, the platform
non-secret values and **test-only** enabled=true/image digest of 64 `a` characters.
That digest is synthetic and is never written into the platform contract.

CI checks out the exact tenant revision from the contract, renders its chart and
compares the complete output to this fixture. It then renders malicious identity/
origin/Secret overrides and evaluates generated policies using Kubernetes1.36.5
admission CEL. Additional cases exercise pod/controller and injection boundaries.

Offline fixture-only execution is available without Helm or a tenant checkout.
Set PORTAL_CHART_DIR to an exact reviewed chart checkout to enable real rendering
comparisons and negative chart-value cases; HELM can override the executable path.
