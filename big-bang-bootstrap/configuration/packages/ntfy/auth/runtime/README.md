# Publisher-only runtime delivery

This bounded slice adds one write-only service publisher for one approved exact
ntfy topic. It adds no human subscriber, Grafana contact point, route or message.
Use the same pinned native image everywhere; namespace, topic, publisher, HTTPS
OpenBao origin, verified cluster ID, trust file and exact record are operator inputs.

Before rendering, inspect `ntfy user list` on the intended live instance. This
first-activation path accepts no existing users or prior managed users. Export
its public server config as `ntfy_base_config_file`; review it for drift. Set
`ntfy_existing_users: []`, `ntfy_previous_managed: []`, `ntfy_publisher_render: true`
and a private `ntfy_runtime_dir`, then run render.yaml. Native offline hashing and
the existing ownership/entitlement validator protect full-config assembly.
Credentials and output stay mode0600 inside a0700 directory, never Git.

After concrete destination/credential approval, deliver.yaml verifies OpenBao
identity/TLS before loading its bearer (`ntfy_bao_token_file`). It refuses an
existing target Secret, record, policy or role. It creates only the exact record,
read-only machine policy and namespace-bound role, public CA and ESO declarations.
Set `ntfy_publisher_deliver: true`. Partial success is retained: inspect and fix
forward rather than rerunning blindly. No existing query roles/records are changed.

Confirm ESO Ready and configuration ownership before selecting the optional
`local-ntfy-publisher` root at an immutable reviewed commit. It preserves the query
stack, ntfy PVC, image and security settings, changing only the full config mount
to a Secret. ntfy reconciles native accounts on restart. Read-only tests and native
ACL inspection are safe acceptance here; do not publish an alert or grant humans
without the approved destination/identity scope. Pair actual Grafana alert delivery
with the ready locked Mattermost destination later. Rotation/removal is not covered
by this create-only path and requires separate coordinated native lifecycle work.

Fail-closed promotion gate (run before changing any Flux source/path):

```sh
set -eu
kubectl -n ntfy wait secretstore/ntfy-runtime --for=condition=Ready --timeout=90s
kubectl -n ntfy wait externalsecret/ntfy-runtime-config --for=condition=Ready --timeout=90s
# Only after both commands return success: select the reviewed immutable root.
```

Never separate these waits from promotion with an unconditional semicolon. A
cancelled/failed wait must terminate the promotion script, not proceed to restart.

## Verified owner subscriber

`subscriber.yaml` is a separate opt-in extension. Supply the verified Keycloak
subject/role, native username and exact approved topic; it does not change Keycloak
or infer entitlements from user input. It verifies the live native user set and
existing publisher configuration before preparing one read-only subscriber. Native
password hashing stays local. `ntfy_subscriber_apply` defaults false; true creates
an owner-readable record containing only subscriber username/token/topic and updates
the full runtime record using its read version as CAS. Publisher credentials and
all non-auth settings are preserved. No deletion, contact point or message is sent.

After writes, wait for a NEW ESO refresh and verify the delivered Secret matches
`subscriber-server.yml` without printing it. Only then select the reviewed immutable
`local-ntfy-owner` root to restart ntfy. Verify native exact-topic read-only access
and denied cross-topic/publish rights before providing secure owner retrieval.
The separate owner record must be readable through the owner's existing approved
OpenBao identity; this play grants no human OpenBao rights. Partial writes require
inspection and fix-forward, not blind rerun (owner record creation is CAS zero).
