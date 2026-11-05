# Alerting review — revised owner decision, inactive

Grafana-managed evaluation and Grafana's built-in Alertmanager own the single ntfy
notification path. Separate Prometheus Alertmanager and its Grafana datasource are
disabled; no live contact point is armed. Preserve the 35 upstream rule objects
plus the three custom source alerts. Recording rules remain useful to dashboards
and queries. Preserving source rules is not completion of Grafana alert migration.

Before activation, inventory each useful upstream/custom alert, its recording-rule
dependencies, labels and pending period; import/review it as a Grafana-managed rule
against datasource UID `prometheus`. Check no-data/error behavior and stable IDs.
Do not forward Prometheus notifications into Grafana's built-in manager or enable
a second notification route. Keep exactly one configuration owner per rule.

The native webhook/custom-payload or ntfy-template path needs pinned-version
compatibility tests before adding an adapter. Exact authenticated TLS endpoint,
topic and protected publisher/subscriber credentials remain external decisions.
Test firing/resolved, grouping/repeat, silence expiry, deduplication, TLS/auth
denial and visible bounded delivery failures. No endpoint or credential exists in
this candidate. Rule migration, actual delivery, resource/retention/restore and
whole-cluster failure detection remain unaccepted.

The default-off `observability-verify.yaml` captures bounded readiness evidence
only after explicit target approval; it does not prove ingestion, authorization,
notification delivery or recovery. No live operation was performed here.

Sources: [Grafana migration](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/alerting-migration/),
[Grafana webhook](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/webhook-notifier/),
[ntfy publishing](https://docs.ntfy.sh/publish/).
