# Bounded deployment-event delivery to Mattermost

Native Flux's Slack provider forwards full Helm event messages and all metadata.
That is unsuitable for tenant channel projection. This tiny adapter uses the
already pinned Nginx runtime's bundled njs module, not a new framework/image or
second event controller. Flux still owns source selection and retries.

The exact-source, per-route authenticated adapter accepts only native Helm
install/upgrade success/failure events. It emits a fixed title, derived
success/failure action, exact allowlisted release identity and configured safe
link. It never emits the input message, annotations, metadata, arbitrary URLs,
chart values, or caller-controlled channel. Each destination hook is native
channel-locked. Unknown sources, methods, paths, mismatched severity and wrong
credentials are denied. Platform and Portal use separate credentials.

Deployment inputs remain target-owned: source lists, recipient hooks, tokens,
public CA, cluster DNS, signed TLS certificate and network selectors. Protected
routes.json is delivered from OpenBao/ESO. Never commit it or log hooks/tokens.
No namespace wildcard is accepted by the adapter: enumerate approved platform
release identities and the exact Portal app release. Unknown future releases
remain off until the trusted source allowlist changes. The Portal route is not
a route for its foundation/configuration control-plane events.

Source-only until deployment acceptance. A 200 requires Mattermost's native
200/ok response, but independent channel readback is still required. Retry can
produce duplicates after an uncertain downstream response; this adapter does
not claim durable exactly-once delivery. There is no replay store or lifecycle
scheduler. Alerting metric messages remain owned by Grafana and not this adapter.

## Guarded activation

`render.yaml` outputs an inert/suspended runtime from exact selected-target inputs.
`custody.yaml`, `seed.yaml` and `activate-custody.yaml` reuse the existing guarded
record/ESO patterns for four exact records under `notifications/mm-projection/`:
`routes-v1`, `tls-v1`, `platform-v1`, `portal-v1`. Each consumer gets its own SA-bound
short-lived OpenBao role and one-record read policy. ESO can patch only its named
precreated Secret, not create arbitrary Secrets. Existing objects/records must
match; no implicit adoption or rotation. Verify current API defaults on retries.

The relay lives in existing `ntfy` namespace with no Kubernetes API token, all
capabilities dropped, read-only root and fixed resource limits. Network ingress
is only notification-controller in flux-system. Egress is cluster DNS and exact
verified Mattermost ingress /32 endpoints on TCP443 plus the selected ingress
pods after DNAT (exact namespace and both name/instance labels, selected port).
The lab target selects RKE2 Traefik in kube-system on TCP8443; other deployments
must supply their own exact approved ingress identity. No broad namespace/CIDR
or internet egress.

Precreate reviewed suspended native runtime objects with the intended GitOps field
manager, then apply the separately approved named-object root management grants.
Publish/select the additive integrated root without dropping newer logging/Portal
work. Verify native TLS, unauthorized request/source denial and test messages in
exact locked channels before unsuspending the two Flux routes. Observe real allowed
Helm outcomes and receipt contents; do not fabricate a production failure.

The platform metric-alert receiver is a separate additive native Grafana change
in `platform-alerts/update-mattermost.yaml`. It CAS-preserves all existing rules
and the ntfy receiver, adding only the locked platform Mattermost receiver.
Coordinate refresh with the existing Grafana rollout owner. This is not a second
metric evaluator or global notification-policy rewrite.
