# Portal offline fixtures

`workload.json` is the output of tenant portal commit
`ecafe09a497e971a4a4af04a331d837e4e1a146a`, rendered with Helm3.19 and a test-only
digest of 64 `a` characters. No synthetic image or allocation is committed as desired state.

CI renders actual native Fleet templates in temporary active/paused fixtures. Their
ConfigMap supplies values for the exact tenant chart; complete workload output must
match this fixture. Hostile chart overrides and Pod mutations are evaluated using
Kubernetes1.36.5 native admission CEL, not a Python substitute.

`native-controls-baseline.json` fingerprints the 19 previously reviewed active/paused
identity/security resources from `f8648170fc08130a4e20101bb038b1adee049136`.
Normalization sorts documents, parses embedded values YAML, and removes only Fleet's
injected `objectset.rio.cattle.io` metadata. All original CEL strings remain exact.
The new namespace/quota/limits receive separate ownership/schema tests. Default disabled
rendering now produces no preview resources. Do not refresh fingerprints to hide an
unexplained security difference.

`FLEET` selects the pinned v0.16 executable. `PORTAL_CHART_DIR` enables real tenant
chart comparison; `HELM` selects its Helm executable. These are test-only tools;
Fleet consumes production YAML directly without Python or these fixture helpers.
