# Approved local ntfy rollout

The owner approved dedicated `ntfy` namespace, HTTPS
`ntfy.perkforge.home.arpa`, 1Gi Longhorn RWO, 24h cache, existing platform CA,
Traefik-only ingress and no allowed egress. No tenant accounts or Grafana routes.
This optional root adds only the ntfy source to `local-velero`; it does not deploy
by merging. Preserve the current immutable-release GitOps source and select
`clusters/local-ntfy` only after preparation. Do not change another app's input.

`resources.yaml` composes the reusable templates, replacing their duplicate
Service with the annotated HTTPS version. Namespace-only `prerequisites.yaml`
is deliberately outside the Flux root: owner applies it once, not the receiving
reconciler. The role adds get/list/watch/create/patch/update for ConfigMap,
Service, ServiceAccount, PVC, StatefulSet, Ingress, NetworkPolicy and
ServersTransport **only in ntfy**; no direct Secret API, RBAC-write, delete or
cluster authority. Workload creation inherently permits mounting any Secret in
this dedicated namespace (including the approved ntfy TLS leaf), choosing its
service account and editing its network policy. Treat this reconciler as trusted
for ntfy namespace workload/secret use; do not place unrelated credentials or
privileged service accounts here. This is not a zero-secret-access boundary.
Kubernetes cannot restrict create to exact resource names.

Before selecting the root:
- Verify this root's `local-velero` baseline equals the currently selected release.
- Issue a dedicated ntfy server leaf using the existing CA and verified trust
  fingerprint, never a replacement CA. Deliver `ntfy-local-tls` (tls.crt/tls.key)
  and public `ntfy-backend-ca` (ca.crt) through the approved secret procedure.
  Both ingress and backend expect SAN `ntfy.perkforge.home.arpa`.
- Add only ntfy's record to the existing lab DNS procedure, target the same
  reviewed private ingress address. Preserve other records and service settings.
- Verify existing Traefik supports ServersTransport rootCAs; verify private-only
  reachability and effective additive policies, not just the policy in this file.
- Preserve prune=false and existing platform-reconciler. Verify no direct Secret API or RBAC-write
  authority is gained through the namespace binding; confirm the namespace has
  no unrelated Secrets or privileged service accounts.

Acceptance: one healthy ntfy pod and bound PVC; correct TLS chain/hostname through
Traefik; anonymous publish/read denied; no effective egress permission; existing
platform resources unchanged. No credentials, topics, subscribers, contact points
or real notifications are part of this activation. A listening probe is not that
acceptance. Stop on CA/custody, permission, external-exposure or baseline mismatch.
