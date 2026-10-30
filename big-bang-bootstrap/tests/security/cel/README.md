# Native admission evidence

This retained Kubernetes CEL harness compiles and executes the Flux enrollment repository's real native policies against positive/negative mutations. It uses the existing pinned Go dependencies. The historical Fleet-only policy generation tests remain archived.

Set `FLUX_PORTAL_CASE_SCRIPT` to this bootstrap checkout's `tests/portal_admission_cases.py` and `FLUX_PORTAL_OPENAPI` to the reviewed Kubernetes OpenAPI fixture; run `go test -run TestFluxPortalAdmission -count=1 -v`. No cluster, credentials or policy installation is involved.
