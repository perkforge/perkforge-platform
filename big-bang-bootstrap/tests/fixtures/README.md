# Retained offline fixtures

`kubernetes-1.36.5.json` merges the unchanged definitions from the previous checked-in Kubernetes schema fixtures (`kubernetes-1.36.5.json` and `workload-types-1.36.5.json`, now archived). It supplies Service/ConfigMap/Deployment types for native Flux admission-policy tests. Kubernetes Apache-2.0 license is retained alongside it; original extraction/provenance notes remain in the archived schema README. No live API or credentials are used.

`source-pins.yaml` and `full-selection-values.yaml` retain the reviewed chart download pins and complete offline selection. Full-selection values are test-only; they are not included by a deployment root. Historical platform release JSON fixtures retain old tag paths for release/refusal tests.
