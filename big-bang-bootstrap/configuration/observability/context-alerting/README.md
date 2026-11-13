# Context-scoped dual alert delivery (#39)

Inactive native Grafana provisioning building block, not an installer or proof of
live delivery. No root selects it and no receiver or policy is armed. The same
named contact point contains two webhook integrations: an exact ntfy topic and a
Mattermost channel-locked webhook. Both send resolved events. Grafana's built-in
Alertmanager remains the sole owner of grouping, silence and repeat behavior.

## Input and ownership contract

Ansible owns eventual rendering of `contact-points.yaml.j2`. First call
`verify_inputs.verify(alert_audiences)` in offline review/tests and enforce the
same constraints in the future delivery play. Empty `alert_audiences` means no
recipients. Never render operator-unapproved input or auto-populate recipients
from tenant labels. Each approved input has:

- `id`: stable lower-case audience slug, max 24 characters; `org_id`: approved
  Grafana organization; `approved: true`: operator review marker, not evidence of
  native permissions.
- `ntfy`: HTTPS server-root `url`, exact `topic`, protected `token`,
  and `publisher_permission: exact-topic-write-only`.
- `mattermost`: protected HTTPS `webhook_url`, actual 26-character `channel_id`,
  and `channel_locked: true`.

The URL/permission assertions must be checked against the actual apps during
activation. A YAML boolean cannot prove a webhook is locked or an ACL exists.
The verifier rejects duplicate destinations, unapproved input, insecure URLs,
redirect/config query parameters, broad topics and unexpected override fields.
Do not give tenants edit rights to these contact points, rules, or provisioning
inputs. Protect Grafana provisioning read APIs: webhook URLs are **not masked**
by Grafana and contain Mattermost bearer capability. Store rendered output and
source secrets in protected runtime Secret/file storage, never a ConfigMap,
tracked values file or logs. Do not print validation input on failure.

Use the reviewed #16/#43 context map for intended audience identity. Corey approved
the Portal topic `tenant-portal-alerts` and private Portal alerts channel. Exact
native channel ID, subscriber identities and escalation are still activation
inputs, not invented by this template. Viewers receive channel
alerts through Mattermost only; they receive no ntfy subscriptions. Platform
engineers can see all tenant contexts, with OpenBao out of scope. This transport
template neither grants subscriptions nor adds channel members. Roles
map to Keycloak groups; native app membership and removal remain explicit work.

## Content and routing safety

Payloads contain only a validated static audience slug, firing/resolved/unknown
status and grouped count. They do not serialize labels, annotations, values,
links, channel overrides or arbitrary alert text. This is deliberately a first
transport slice: useful severity/app/symptom text requires an approved bounded
rule-to-message catalogue, not forwarding arbitrary annotations. The template
uses ntfy's JSON publish format at the server root with a static exact topic; no server formatter is
needed for this path. Existing platform formatter remains unchanged.

No notification policy tree is replaced by this file. Assign the contact point
only from platform-owned reviewed rules scoped to the permitted namespace/app;
never treat a route matcher or tenant-controlled `context` label as authorization.
An unmapped event has no tenant destination. Configure fallback to an explicitly
approved platform operations audience during integration, not an arbitrary tenant.
Cross-tenant aggregation must not happen before the audience decision. Tenant
Grafana drilldown links remain withheld until #218 proves query isolation.

Before enabling: inspect exact-topic ntfy ACLs and locked private-channel webhook;
verify Grafana 13.2.1 imports this file; test firing/resolved to both destinations,
unknown tenant/context denial, one integration failing while the other works,
grouping/repeat/silences, credential/TLS denial and offboarding. Never call a
render-only test evidence of those live outcomes. Do not create a second
Prometheus Alertmanager route.

## Verification

Run `PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest
configuration.test_context_alerting -v`. These are offline source/negative input
checks only. No real credential is used and no HTTP request is sent.

Native `payload.template` verified in Grafana 13.2.1's alerting dependency
[`e1a167a201a8`](https://github.com/grafana/alerting/blob/e1a167a201a8/receivers/webhook/v1/config.go).
See [file provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/),
[custom webhook payload](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/webhook-notifier/),
[ntfy JSON publishing](https://docs.ntfy.sh/publish/#publish-as-json), and
[Mattermost channel locking](https://docs.mattermost.com/integrations-guide/incoming-webhooks).

### Isolated native import regression

`tests/integration/test_grafana_context_import.py` boots official Grafana 13.2.1
(pinned manifest digest) in a disposable Podman container with `--network=none`.
It imports only synthetic contact points and checks the native provisioning API
for both receiver IDs, file provenance, resolved-event enablement and unchanged
custom payloads. It creates no policy/rule and cannot contact either destination.
No ports are published, no real credential or cluster context is read, and the
container is removed even on assertion failure. Pull the image explicitly first:

```sh
podman pull docker.io/grafana/grafana@sha256:1dec240d14e232597dce9bfa56dae55f4397b138cdc91e3ee92ac6b157e2fc49
RUN_GRAFANA_CONTEXT_IMPORT=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest \
  integration.test_grafana_context_import -v
```

The opt-in test passed against that image. This establishes native import, **not**
notification delivery, template execution against real events, recipient access,
silence/repeat behavior or tenant isolation. Those acceptance gates remain.
