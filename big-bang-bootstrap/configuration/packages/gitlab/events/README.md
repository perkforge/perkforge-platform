# Scoped GitLab events (#334)

Inactive source slice for the Portal pilot. `policy.yaml` records Corey's selected
failed/recovered pipelines, failed security-scan execution, and failed deployments.
No webhook, credential, receiver, app membership or delivery is installed here.
The receiver remains unselected. The hook template is **not** a complete integration.

## Native ingress, not direct notifications

`project-hook.json.j2` is the native project webhook request body. Ansible owns
future rendering/apply. Review inputs with `verify_inputs.verify(hook, context)`
and enforce identical checks in the future apply workflow. Use the reviewed
context map's **real** native group/project IDs, checked with `inspect-context.yaml`.
Empty IDs deliberately fail. Render protected output only; the token is a secret.
Do not put it in Git, a ConfigMap, logs, URLs or notification messages.

The receiver path is fixed per context; the operator-approved HTTPS origin and
credential are explicit runtime inputs. It must authenticate each hook and bind
that credential to the configured project/context before accepting payload IDs.
A matching payload ID alone is not authorization. The local validator cannot prove
receiver ownership, native project membership or token scope. No URL is selected
from webhook data. Project hooks are used rather than instance-wide hooks.

Pipeline/job/deployment event switches are needed for this selected event set.
**GitLab sends broader events than the desired notifications**: the receiver must
filter running/success/canceled/skipped events and unrelated jobs. A plain webhook
forwarder is not acceptable. Security scan execution jobs need an explicit reviewed
job-name allowlist. Job failure is not equivalent to vulnerability findings;
findings threshold/report handling is still unselected and must not be implied.

## Required stateful integration

Keep Grafana's built-in Alertmanager as the only grouping/repeat/silence owner.
A supported event ingestion/normalization path is not chosen yet; do not send these
GitLab bodies straight into Grafana contact points or ntfy. That missing integration
must establish all of the following before any hook is enabled:

- Durable per-context/project incident state, authenticated project binding, retry
  deduplication and stale/out-of-order event handling. A healthy pipeline is a
  recovery only for its matching prior failure, never a different project/ref.
- Agree exact incident correlation (ref/environment/job), repeat interval and how
  deployment/scan incidents resolve; no invented threshold or time-based recovery.
- Firing/resolved grouping, repeat only while unresolved, and no healthy-event spam.
- Fixed private Mattermost channel and exact ntfy topic from the entitlement map,
  never a payload-provided destination. Viewers see Mattermost channel alerts only;
  no viewer ntfy subscriptions or direct messages. Platform engineers see all tenant
  contexts without creating cross-tenant tenant channels.
- Bounded reviewed event messages, no raw payloads/logs/commit text or secret-bearing
  URLs. Native GitLab links must still require project authorization.
- Receiver failure visible to operators; independent per-destination delivery retry,
  offboarding and wrong-tenant denial, no duplicate native chat integrations.

This is a desired contract, not proof those controls already exist. #334 stays open.
Source tests validate input rejection and the rendered native hook fields only.
No hosted API or installed GitLab 19.4.2 compatibility test is claimed.

References: [project hooks API](https://docs.gitlab.com/api/project_webhooks/),
[webhook event types](https://docs.gitlab.com/user/project/integrations/webhook_events/).
Run `PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest configuration.test_gitlab_events -v`.

A [native polling candidate](metrics/README.md) avoids a bespoke event service, with explicit latest-state/polling limits. It remains inactive pending selection and acceptance.
