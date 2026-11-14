# Native Grafana → exact-topic ntfy

One portable, explicitly selected audience. `render.yaml` defaults off and renders
protected native provisioning, ESO declarations and nonsecret Big Bang child values.
The two Grafana-managed rules query only the reviewed namespace: unavailable
Deployment replicas and CrashLoopBackOff containers for five minutes. They bind
directly to their receiver with 30s grouping wait, 5m group interval and 4h repeats;
the existing global notification policy tree is not replaced. Both firing and
resolved events carry only a static context, state and grouped count, never raw
annotations, labels, links, values or credentials. Missing workloads produce zero;
query errors keep last state rather than pretending recovery.

Supply the exact approved namespace/context/topic, HTTPS ntfy origin ending `/`,
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
Nextcloud, Grafana SSO/query datasource and dashboards. Existing extraSecretMounts
must be merged explicitly if present; this initial target had none. Never select
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
