# Offline security findings

Use `big-bang-bootstrap/evidence/manage-security-findings.py --help` for the retained offline register workflow. It imports sanitized candidate reports idempotently and records human-reviewed states, risk decisions, remediation and retest evidence. Defaults use protected local state; never commit credentials or raw sensitive reports.

The `docs/templates/security-finding.yaml` record is an illustrative schema. Set artifact paths to reviewed local evidence from the current target. Historical tenant-suite producers remain archived and require endpoint/catalog/identity adaptation before physical-cluster use; no live probe is authorized by this document.

A finding cannot be closed just because configuration changed: retain an applicable passing retest and evidence reference. Risk acceptance requires accountable human ownership and expiry. Tests of this register use synthetic local reports and do not change a cluster.
