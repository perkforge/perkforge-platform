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

The candidate uses Grafana's standard JSON POST webhook and ntfy's native named
formatter, without a bridge or custom Grafana body. The server must mount
`ntfy-templates/platform-grafana.yml` in its configured template directory; the
future contact point selects `?template=platform-grafana` on its approved topic.
The template forwards only static status and grouped count. Labels, annotations,
values, titles, message text and URLs are deliberately omitted; recipients open
Grafana with their approved accounts for details. This reduces notification data
exposure, not backend authorization or tenant isolation.

The official ntfy v2.37.2 Linux amd64 archive was checksum-verified against its
release manifest. `integration.test_ntfy_native_webhook` ran the exact binary
against an isolated synthetic TLS server and temporary SQLite/auth databases.
It verified firing/resolved formatting, subscriber cache retrieval, anonymous
rejection, write-only publisher/read-only subscriber and wrong-topic denial,
wrong password, CA/hostname denial, malformed-payload rejection, and omission of
synthetic sensitive fields. These are ntfy component tests using Grafana-compatible
synthetic payloads; a live Grafana v13.2.1 contact point was not exercised. The
optional test requires `NTFY_VALIDATE_BIN`, checks that version, downloads nothing,
and otherwise skips. Run it with loopback socket permission, not cluster access.

Exact authenticated TLS endpoint, topic and protected publisher/subscriber
credentials remain UNCONFIGURED. Require default-deny ACLs and separate exact-topic
write-only/read-only identities; neither is an ntfy admin. There is still no ntfy
server deployment, credential delivery or armed Grafana contact point in this PR.
Test actual firing/resolved delivery to only the intended client, grouping/repeat,
silence expiry, deduplication and visible bounded failures before activation.
Rule migration, resource/retention/restore and whole-cluster failure detection
remain unaccepted.

The default-off `observability-verify.yaml` captures bounded readiness evidence
only after explicit target approval; it does not prove ingestion, authorization,
notification delivery or recovery. No live operation was performed here.

Sources: [Grafana migration](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/alerting-migration/),
[Grafana webhook](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/webhook-notifier/),
[ntfy publishing/templates](https://docs.ntfy.sh/publish/),
[exact native formatter source](https://github.com/binwiederhier/ntfy/tree/v2.37.2/server/templates),
[ntfy v2.37.2 release and checksums](https://github.com/binwiederhier/ntfy/releases/tag/v2.37.2).

## Portal PaaS delivery extension

The [context-scoped dual-delivery building block](context-alerting/README.md)
adds native Grafana contact-point rendering for one approved audience with both
ntfy and channel-locked Mattermost destinations. It is unselected and introduces
no policy tree, rules or recipients. Viewer eligibility is Mattermost-only; the
same transport contact point does not imply identical subscriber membership.
