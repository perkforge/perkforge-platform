# Platform resource alerts

Portable, native Grafana alert provisioning for **platform-alerts**, separate
from platform-deployments and tenant topics. No global notification policy is
replaced. No Prometheus Alertmanager duplicate receiver. This package renders
only; a successful render is not a deployment or notification test.

## First baseline

| Signal | Sustained condition | Resource dimensions |
|---|---|---|
| CPU | busy >85%, 15m | exporter instance |
| Memory | available <10%, 10m | exporter instance |
| Persistent volume | available <15%, 15m | namespace, PVC |
| Host filesystem | available <15%, 15m, writable only | instance, device, mountpoint |
| Required collector | failing 10m | instance, collector |
| Physical network | RX **or** TX >85% advertised speed, 10m | instance, interface |
| Physical disk | average completed I/O >50ms at >10IOPS, 15m | instance, device |

Network directions are not added on full-duplex links. Disk busy time alone is
not a saturation claim, particularly for parallel NVMe. Thresholds are initial
warning thresholds, not hardware guarantees; review against baseline workloads.
Disk device and physical interface regexes are deployment inputs; never select
container veth or logical Longhorn devices as physical links/disks by accident.
PVC observations are deduplicated by namespace/claim. This does not measure
Longhorn replica backing-store or thin-provisioned pool capacity.

## Input contract and activation

Run `ansible-playbook -i localhost, render.yaml -e @protected-inputs.yaml` with:

- `platform_alerts_render: true` (default false; check mode is inert)
- `platform_alerts_topic: platform-alerts`
- `platform_alerts_url`: HTTPS ntfy origin with trailing slash
- `platform_alerts_grafana_url`: HTTPS Grafana origin with trailing slash
- `platform_alerts_runbook_url`: deployment's HTTPS copy of this runbook
- `platform_alerts_token_file`: existing exact-topic write-only publisher, mode0600
- `platform_alerts_ca_file` and `platform_alerts_ca_sha256`: verified public CA
- `platform_alerts_output_dir`: protected absolute real path
- `platform_alerts_network_device_regex`, `platform_alerts_disk_device_regex`
- `platform_alerts_enable_host_filesystem`, `platform_alerts_enable_physical_network`:
  false until correct host-level series and expected node coverage are verified.

Keep the token and rendered alerting.yaml out of Git. Deliver through a distinct
exact-record OpenBao policy, namespace-scoped ESO consumer and native Grafana
Secret mount. Preserve every existing effective extraSecretMounts entry,
especially tenant-portal-alerts. Existing initial-audience ntfy-routing activation
refuses existing mounts intentionally; do not bypass that guard. New topic must
have explicit publisher write and Corey subscriber read ACLs. Do not reuse a
tenant token, wildcard topic permission or broaden existing reader grants.

Each rule uses native per-rule notification routing, groups by platform and
alert name, waits1m, groups updates10m and repeats6h; resolved messages enabled.
Missing data and evaluation errors are visible, never rewritten to healthy zero.
Contact point payload uses JSON serialization, a bounded set of resource labels,
summary, runbook and Grafana's generated rule URL. ntfy `click` opens the source
rule (last included rule if grouped); each alert has its own source link in the
message. Verify Grafana's external root URL before live test. No guessed Rancher
or Headlamp deep links. Native firing/resolved delivery and phone click behavior
must be verified separately before claiming end-to-end completion.

## Current local coverage finding (2026-11-14)

Read-only platform queries confirmed CPU/memory3 nodes, PVC22 series and physical
NVMe latency3 series. Filesystem collector fails on all nodes: SELinux denies
`/host/proc/1/mountinfo`; no host filesystem free-space series. netdev emits
exporter pod eth0/lo counters, whereas netclass reports host interface speeds;
these are not comparable. Host filesystem/network rules therefore default
paused, rather than pretend coverage. Collector failure remains actionable.
PSI is compiled but disabled by the RHEL boot default; enabling requires boot
configuration/reboot and is not assumed by this package. No PSI alert is armed.
Any host security change requires its separate exact approval; do not disable
SELinux or enable privileged mode to clear a monitoring warning.

## Investigate

Open the alert's native Grafana rule, inspect query labels and recent time range.
For CPU/memory, correlate node load and workload requests/limits; investigate
pressure before adjusting limits. For PVC space, inspect the named workload's
retention and expansion policy, plus Longhorn replica/pool headroom. Never
blindly delete data. For disk latency, inspect node disk service time, queueing,
errors and concurrent backup/replica rebuild activity. For network, validate the
selected physical link speed and traffic direction before assuming congestion.
For collector errors or missing data, restore metric coverage before treating
an absent resource alert as healthy. Link out to the deployment's documented
node/workload dashboards; account permissions still govern access.

Payloads include at most3 alerts with explicit truncation count and bounded label
text; open Grafana for the complete group. Provisioning escapes Go `$` variables
as `$$` because Grafana expands environment variables while loading YAML. Native
Grafana13.2.1 import was verified with network disabled and synthetic paused
rules; this is not a notification-delivery claim. `NoData` detects a wholly
empty query, not an individual missing node among others; fleet-level expected
node/collector inventory detection remains a separate improvement.

## Additive delivery workflow

`render-delivery.yaml` renders the dedicated `eso-platform-alerts` consumer and
mount values from `platform_delivery_expected_mounts`, copied from the effective
native Helm values. `activate.yaml` checks exact equality before reading the
operator credential, checks path/Secret collisions, creates or verifies the
exact OpenBao record/policy/role, then verifies ESO payload equality. It creates
`grafana-platform-alerts-values`; it never selects a Flux root. Coordinate the
`local-platform-alerts` root promotion with the active platform deployment.

`packages/ntfy/auth/runtime/platform-audience.yaml` adds only grafana-platform
(write) and corey-platform (read), both ordinary users, to platform-alerts. It
compares prior native users and every current auth list, preserves all non-auth
server settings, uses CAS, and accepts an already-written owner record only
when exactly equal to the preserved credential. Re-running preparation reuses
saved hashes/tokens rather than rotating them. A mismatch stops without overwrite.

If Grafana activation stops after ESO creates its Secret, the target collision
guard intentionally stops a blind retry. Read exact named Secret/payload and
consumer identities privately, compare against rendered artifact, and resume
only missing ConfigMap/root steps after equality verification. Never delete the
Secret, rotate tokens or weaken collision guards to make a retry pass. If ntfy
has already restarted with new users, its initial native-user guard also stops;
verify the four exact users/ACLs and existing desired config instead of repeating
account addition. No routine operation needs new cluster-wide grants.

### One phone credential, multiple exact reader topics

Keep the already-working Corey phone token rather than replace it per topic.
`subscriber-topics.yaml` adds read-only platform-alerts to the verified existing
corey-portal identity while preserving its tenant-portal-alerts permission,
password and token. Publishers remain separate exact-topic write identities.
The server account name is not its authorization boundary. No wildcard is used.
After successful CAS, the authoritative protected prior becomes
`unified-validation.json`; use that as `ntfy_phone_prior_validation` for a safe
idempotent retry. Do not rerun from the old pre-change validation snapshot.
The separately created corey-platform account is not deleted by this change.
