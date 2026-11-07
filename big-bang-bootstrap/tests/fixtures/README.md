# Retained offline fixtures

`kubernetes-1.36.5.json` merges the unchanged definitions from the previous checked-in Kubernetes schema fixtures (`kubernetes-1.36.5.json` and `workload-types-1.36.5.json`, now archived). It supplies Service/ConfigMap/Deployment types for native Flux admission-policy tests. Kubernetes Apache-2.0 license is retained alongside it; original extraction/provenance notes remain in the archived schema README. No live API or credentials are used.

`source-pins.yaml` and `full-selection-values.yaml` retain the reviewed chart download pins and complete offline selection. Full-selection values are test-only; they are not included by a deployment root. Historical platform release JSON fixtures retain old tag paths for release/refusal tests.

`operator_placement_test.go` runs inside the public Prometheus Operator v0.94.0
source (commit `2e4af1d7d8f0ae634fcf0ac967a76fb381a65542`). The dedicated
`metrics-placement` CI job verifies its archive SHA-256 before extraction and
uses the existing pinned Go toolchain. The chart's operator image version is
asserted alongside the native generator test so a chart upgrade cannot silently
reuse the old generator. No operator/controller is started.
