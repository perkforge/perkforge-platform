# Retained offline fixtures

`harbor-image-startup/` retains the unchanged Iron Bank Harbor 2.15.2
`install_cert.sh` (identical for core/jobservice) and two entrypoints. Immutable
source URLs and SHA-256 values are in `sources.json`; the exact Dockerfiles are
[core](https://repo1.dso.mil/dsop/opensource/goharbor/harbor-core/-/blob/163854c78e1f0c206cd096caeab1516bc1a5dbc7/Dockerfile)
and [jobservice](https://repo1.dso.mil/dsop/opensource/goharbor/harbor-jobservice/-/blob/6bd752347f1355bf9c9bbc5c1195443fd955dcfc/Dockerfile).
These are source fixtures, not assertions about a registry tag's image contents.
The upstream Apache-2.0 license is retained in that directory.
The test uses the actual copy command from application values, Bash as UBI's
`/bin/sh`, UID 10000/GID 1000, synthetic public roots, read-only mounts and no
network. Only application binaries are replaced with sentinels; no Harbor image
is pulled/run and no credentials or real certificate inputs are used. Render
tests separately require matching immutable init/runtime image digests.

`kubernetes-1.36.5.json` merges the unchanged definitions from the previous checked-in Kubernetes schema fixtures (`kubernetes-1.36.5.json` and `workload-types-1.36.5.json`, now archived). It supplies Service/ConfigMap/Deployment types for native Flux admission-policy tests. Kubernetes Apache-2.0 license is retained alongside it; original extraction/provenance notes remain in the archived schema README. No live API or credentials are used.

`source-pins.yaml` and `full-selection-values.yaml` retain the reviewed chart download pins and complete offline selection. Full-selection values are test-only; they are not included by a deployment root. Historical platform release JSON fixtures retain old tag paths for release/refusal tests.

`operator_placement_test.go` runs inside the public Prometheus Operator v0.94.0
source (commit `2e4af1d7d8f0ae634fcf0ac967a76fb381a65542`). The dedicated
`metrics-placement` CI job verifies its archive SHA-256 before extraction and
uses the existing pinned Go toolchain. The chart's operator image version is
asserted alongside the native generator test so a chart upgrade cannot silently
reuse the old generator. No operator/controller is started.
