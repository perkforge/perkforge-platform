# Native Grafana → exact-topic ntfy

One portable, explicitly selected audience. `render.yaml` defaults off and renders
protected native provisioning, ESO declarations and nonsecret Big Bang child values.
The two Grafana-managed rules query only the reviewed namespace: unavailable
replicas of the expected Deployment and CrashLoopBackOff containers for five minutes.
The availability rule also fires if that exact Deployment or its required metrics
disappear; it does not interpret missing series as healthy. They bind
directly to their receiver with 30s grouping wait, 5m group interval and 4h repeats;
the existing global notification policy tree is not replaced. Both firing and
resolved events carry only a static context, state and grouped count, never raw
annotations, labels, links, values or credentials. The crash-loop count alone defaults to zero when no waiting containers exist;
query errors keep last state rather than pretending recovery.

Supply the exact approved namespace/expected Deployment/context/topic, HTTPS ntfy origin ending `/`,
existing write-only publisher token file (0600), public CA file and SHA256,
OpenBao endpoint/cluster identity, dedicated record path, monitoring namespace,
and owner-only output directory. Targets are inputs, not image rebuilds or
hardcoded physical addresses. No subscriber or Mattermost identity is created.

`activate.yaml` is independently default-off and needs action-specific approval.
It writes one CAS-zero OpenBao record with protected alerting YAML and creates one
exact-record policy and short-lived namespace/SA-bound auth role. Exact partial
retries are verified, not rotated; conflicting records stop. It uses existing
monitoring ESO Secret/status permissions and public CA, adding only TokenRequest
for its dedicated auth SA. It does not add a network policy or broad Secret read
grant. Existing ntfy server configuration/owner ACLs remain untouched. Verify the
controller's existing monitoring permissions and CA before activation. Apply only
reviewed rendered files; none of these paths are tenant-writable.

After ExternalSecret sync, the native `extraSecretMounts` mounts only `alerting.yaml`
read-only at `/etc/grafana/provisioning/alerting/ntfy.yaml`. `local-portal-alerts`
extends the integrated Portal root, retaining its exact enrollment selection,
Nextcloud, Grafana SSO/query datasource and dashboards. Activation reads effective stored Helm values (including Secret valuesFrom) under
no_log, using the target `grafana_ntfy_helm_release` (default monitoring-grafana).
Set `grafana_ntfy_helm_binary` to the existing verified executable path when Helm
is not on PATH; this procedure never installs a binary.
It refuses a nonempty existing extraSecretMounts list instead of replacing
it; this initial target had none. Exact synchronized Secret payload equality is
checked after ESO Ready and before exposing the values to a selected root. Never select
an older ntfy-only root to add notifications. A coordinated Grafana restart imports
the file; subPath mounts require a restart after later approved credential updates.
No credential is placed in ConfigMaps, Git, Helm values or chat.

Before activation, inventory live rules/receivers for UID collisions, preserve
existing global policy, datasource UID `prometheus`, SSO, dashboards and CA. Check
HTTPS from Grafana with existing CA and egress rather than adding network grants.
Afterward verify ESO Ready, Grafana Ready, exact receiver/rule provenance and
notification settings via native APIs, live query success and no provisioning errors.
Real failures may notify once armed. Do not fabricate a failure or call the test
notification endpoint without the owner's separately coordinated test request.
Phone receipt, real firing/resolved, repeats and silence behavior are distinct
acceptance, not inferred from successful import. This slice does not migrate all
upstream rules or invent absent pipeline/security metrics.

## Optional matching Portal Mattermost delivery

The opt-in `grafana_mattermost_enabled=true` adds a second native webhook receiver
`ctx-portal-mattermost` to the **same** `context-portal-ntfy` contact point. Existing
ntfy UID/configuration, alert rules, grouping, resolution and repeat settings are
unchanged. It sends only static context, firing/resolved/unknown and alert count;
no raw labels, error text, user-supplied links or dynamic channel override.

Render inputs additionally require `grafana_mattermost_locked_approved: true`,
exact verified `grafana_mattermost_channel_id`, trusted HTTPS
`grafana_mattermost_origin`, owner-only `grafana_mattermost_hook_url_file`, and
`grafana_mattermost_ca_file` with `grafana_mattermost_ca_sha256`. Verify the native
hook's owner/channel lock through the separately approved Mattermost helper before
rendering. The URL file must be0600 under0700, contain only the exact origin's
`/hooks/<native-id>` URL, and remain out of Git/logs. TLS peer/hostname validation
stays enabled with the approved public CA. No network rule changes are implied.

Use `update-mattermost.yaml`, **not initial `activate.yaml`**, for an existing
Portal record/ESO consumer. It is default/check inert and requires
`grafana_mattermost_update=true`, `grafana_mattermost_update_approved=true`,
`grafana_ntfy_cluster_uid`, and exact `grafana_ntfy_previous_sha256` of the current
protected alerting.yaml, in addition to existing approved custody/render inputs.
It checks the selected cluster/OpenBao identity and existing ESO remote record,
requires the decoded configuration to differ only by the appended receiver,
updates the **same** record using its current KV version CAS, verifies readback,
refreshes only the existing ESO object and waits for exact decoded Secret equality.
No policies, roles, SAs, Secrets, mounts, root selection or restart are created.
A repeat with the exact desired payload makes no KV write. Stale/foreign source
or mixed-field changes stop rather than overwrite another worker.

After exact ESO equality, the rollout coordinator performs the separately
approved bounded Grafana rollout because the mounted file uses subPath. Preserve
all dashboards, datasources, both existing provisioning mounts, ntfy server/auth
and platform-resource rules. Verify native receivers/health and delivery through
one separately coordinated labeled test, not an induced incident. These helpers
never send a test or publish a message. A generated URL/Ready Secret is not proof
of actual Grafana→Mattermost delivery; keep #395/#39 acceptance open until verified.
