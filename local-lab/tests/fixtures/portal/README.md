# Portal offline fixtures

`workload.json` is the output of tenant portal commit
`e82eb8daef435580c2edd54562f681c8ecf0a3d8`, rendered with Helm3.19 and a test-only
digest of 64 `a` characters. No synthetic image or allocation is committed as desired state.

CI renders actual native Fleet templates in temporary active/paused fixtures and renders
the exact tenant chart with its own ordinary application values. Complete workload output
must match this fixture. Hostile chart overrides and Pod mutations are evaluated using
Kubernetes1.36.5 native admission CEL, not a Python substitute.

`admission-baseline.json` fingerprints the eight previously reviewed admission policies
and bindings from `f8648170fc08130a4e20101bb038b1adee049136`. It removes only Fleet's
injected `objectset.rio.cattle.io` metadata. Original CEL strings remain exact. Shared
foundation objects have separate ownership, opt-out and synthetic second-tenant tests;
they no longer include a platform-values ConfigMap or its read grant. Do not refresh
fingerprints to hide an unexplained admission difference.

`FLEET` selects the pinned v0.16 executable. `PORTAL_CHART_DIR` enables real tenant
chart comparison; `HELM` selects its Helm executable. These are test-only tools;
Fleet consumes production YAML directly without Python or these fixture helpers.
