# Retained OpenBao API and evidence assets

The JSON/HCL configuration, roles, policies, validation fixtures are preserved from the prior effort. Big Bang/Flux owns package installation through the parent app values. `configuration/ansible/platform-config` owns explicitly gated mutable API settings; its defaults and identities are unchanged by this move.

OpenBao is not running in the current trial. These assets are not a current activation runbook: endpoints, identity, storage, initialization/unseal, TLS and permissions must be reviewed before use. No root/unseal material belongs in Git. This restructuring does not adopt historical custom enrollment or duplicate native platform controls.
