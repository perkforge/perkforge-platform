# Shared evidence tooling

`manage-security-findings.py` is the cluster-independent offline findings register: sanitized report import, reviewed status/risk decisions and evidence-backed retests. Its tests live in `tests/`; it is shared infrastructure/platform/application tooling, not a Big Bang package.

Generated evidence belongs in ignored `runs/` or existing protected operational state. Never commit tokens, passwords, kubeconfigs, Secret bodies or raw sensitive logs. Existing ignored evidence and backups are preserved.

Big Bang-specific render, bootstrap, identity/authorization and isolated API tests live under `big-bang-bootstrap/tests/`. Historical catalog/Rancher tenant probes remain archived with their assumptions; adapt them to current enrollment-owned expectations before live reuse. A passing old fixture is not proof of the physical target. No document or default test command authorizes live probes.

```sh
python3 -m unittest discover -s evidence/tests -v
```
