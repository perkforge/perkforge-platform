# Phase A: platform-only real pod logs

This optional root is source preparation until a reviewed exact commit is selected.
It inherits the current integrated logging root, preserving existing apps, ingress,
SSO, query/notification mounts, Prometheus and the old `loki-pilot` datasource.
The new org-1 `loki-platform` datasource has a distinct read-only identity; the
native dashboard and reviewed PE-only OAuth fields are additive map keys.
No tenant org, user membership or tenant query map is enabled here.

## Ordered activation

1. Complete reviewed four-record custody delivery and verify exact synchronized
   payload, not only a Ready condition. Keep original pilot credentials/Secrets.
2. The authorized foundation operator applies only `collector-rbac.yaml` and
   verifies pod metadata/log reads, with Secrets/exec/writes still denied.
   These two cluster-scoped objects are deliberately NOT in the tenant-limited
   root: `platform-reconciler` cannot create ClusterRoles/Bindings. Do not expand
   its authority or reinstall bootstrap to apply these prerequisites.
3. Verify no active old opt-in pilot producer before the gateway/collector switch;
   otherwise review buffer/loss impact. Preserve `platform-pilot` hash with exact
   legacy read scope. New writes use only `pf-log-collector-write` and registered
   scopes. Gateway access metadata goes to stdout without request arguments or log
   content, avoiding an unbounded private filesystem log.
4. Select the reviewed current-root composition only in the serialized window.
   Wait for Loki/gateway/Alloy/Grafana readiness; verify actual pipeline labels,
   spoofed namespace annotation handling, read/write separation, arbitrary header
   denial, legacy query preservation and TLS. Test actual datasource proxy and
   dashboard queries before enabling the separately reviewed PE entitlement.
5. Verify existing dashboard inventory/Prometheus/notifications and app readiness.
   Tenant access remains gated by lifecycle admission and actual cross-scope tests.

Initial collection is explicitly `tenant-portal`, `mattermost`, `flux-system`.
This provides real workload logs and a platform read federation while measuring
bytes/retries/drops/PVC growth/CPU/memory against existing 10Gi/72h storage and
unchanged requests/limits. It is NOT yet all-cluster coverage. Expand the source
namespace list or explicit all-namespace flag only after the measured budget is
reviewed. Per-tenant ingestion limits are not a global storage cap; no arbitrary
silent debug dropping or claim of general secret redaction is made.

`profile.yaml` plus the reusable boundary renderer must reproduce checked-in
`boundary-values.yaml` and `collector-rbac.yaml`. The dashboard values derive from
the reviewed `pod-log-dashboard/platform-profile.yaml` and renderer, wrapped by
`dashboard-values.yaml.j2`; no alternate dashboard or datasource fallback.
