# Platform deployment outcomes (inactive)

Native flow: **Flux notification-controller 1.9.4 generic Provider → existing
ntfy 2.37.2 named template → `platform-deployments`**. No bridge, new image or
polling controller. Related notification acceptance: #39. All resources remain
unselected; Provider and Alert are suspended, endpoint/environment unconfigured.

The explicit source list contains user-facing platform HelmReleases in `bigbang`.
It excludes `bigbang` umbrella duplicates, database/operator dependencies, Source
fetches, tenant namespaces and wildcards. Mattermost is an approved future source,
not evidence it is already deployed. Add/remove sources deliberately for each
platform installation; tenant deployment topics/routes require a separate audience
and source review. Platform engineers need explicit native topic subscription
rights; Keycloak membership alone is not an ntfy ACL.

## Event contract

Helm-controller **1.6.4** emits `Helm install/upgrade succeeded/failed for release …`.
Flux's `inclusionList` matches the **message**, not the event reason. The anchored
filter excludes periodic reconciliations and no-op drift messages. Both info and
error outcomes are included. No started notification is fabricated: a bounded,
verified native started-event contract can be added later. Repeated genuine failed
actions may notify again after native notification-controller duplicate-rate limits;
this is not durable once-per-version delivery and must not be described as such.

The template publishes app name, environment, chart revision and app version from
chart metadata when available, plus a fixed platform source link. Helm chart app
version is not proof of the running image version. Unknown versions are explicitly
unavailable. Success reports **Helm action completion**, not independent application
acceptance. Wait settings, hook/Helm tests and custom-resource readiness differ by
release; a successful Mattermost CR chart install alone cannot prove Mattermost
pods or login are healthy. Runtime incident routing remains in `platform-alerts`.

Flux 1.9.4 strips the resource API group prefix from event metadata, so the generic
JSON Event exposes `metadata.revision` and `metadata.app-version`. A static Alert
`eventMetadata.environment` supplies the selected target name. The template never
includes the raw `message`, annotations, arbitrary links, tokens or reporting IDs.
Output fields are length bounded; the source link in the message is fixed, not
payload-controlled. Native named templates support title/message/priority, not
a templated `click` field.

**Wire boundary:** the generic Provider sends the complete original Event to ntfy,
including its original message/Helm logs. Formatting happens inside trusted ntfy
before persistence/publication. Thus phone/cache output is minimized, but the wire
payload is not pre-redacted. Use authenticated TLS and normal non-debug logs. If
policy forbids even the trusted ntfy service receiving raw events, do not activate
this native route: it cannot satisfy pre-transport redaction without a different
architecture. Do not claim that the formatter retroactively removes source logs.
If inspection finds credentials in an actual event, stop that route before
transport and report the exposure; do not knowingly send them to this endpoint.

## Additive activation contract

1. Coordinate with the current ntfy runtime owner. Preserve every existing user,
   token, topic ACL, template and server setting. Create a **different** publisher
   with write-only access to exact topic `platform-deployments`; never reuse
   platform-alerts or tenant-portal-alerts credentials. Extend the verified existing engineer
   subscriber identity with exact-topic read-only rights; do not create a second per-server human token.
2. Store runtime publisher input in its dedicated approved OpenBao record and
   deliver via scoped ESO to Secret `flux-system/flux-deployment-publisher`.
   Required fields: `headers` containing YAML `Authorization: Bearer <token>`, and
   `ca.crt` containing the trusted public issuer chain. Do not put credentials in
   Git, ConfigMaps, Provider.address, logs or chat. **The generic Provider ignores
   `token` for authentication**; its `secretRef` must supply `headers`.
3. Mount ConfigMap `ntfy/ntfy-flux-deployment-template` key `flux-deployment.yml`
   read-only as `<existing template-dir>/flux-deployment.yml`, preserving existing
   files. The named endpoint is `?template=flux-deployment`; `.json.tmpl` is not
   the contract. Coordinate any restart/subPath refresh with the runtime owner.
   This directory creates the additive ConfigMap, not a patch to the shared live
   StatefulSet or protected server.yml. No shared configuration is silently replaced.
4. Set the approved HTTPS endpoint and environment through the selected target's
   overlay, verify TLS hostname/CA, exact-topic ACLs and existing controller egress.
   Obtain concrete approval for any new security/network grant; this source adds
   none. Provider/Alert/Secret live in the notification-controller's control namespace;
   confirm its existing Secret-read and cross-namespace source settings first.
5. Select the manifests through the existing integrated root only, then unsuspend
   Provider/Alert after prerequisites are verified. Do not regress to an older root.
   Before enabling each success source, inspect its effective install/upgrade
   settings: wait and wait-for-jobs must not be disabled. Remove an unchecked
   source rather than labeling an unverified action as completed. This filter
   does not itself inspect HelmRelease settings; the activation check is required.
   Check Provider Ready, native notification failures and actual intended deployment
   outcome receipt. No artificial production test without coordinated authorization.

## Verification and closure

Offline tests exercise the actual pinned ntfy template with synthetic payloads,
check exact source/filter/default-off settings and verify hidden fields never enter
cached/published notifications. They do not grant credentials or prove live Flux
transport. Before closure, verify one real permitted deployment outcome, failure
formatting/delivery, wrong-role/topic denial, no tenant/umbrella/no-op forwarding,
and app/environment/version/link on the approved subscriber. Report ticket closure
only after these live criteria, not when this source merges.

Primary source contracts:
- https://github.com/fluxcd/notification-controller/blob/v1.9.4/internal/notifier/forwarder.go
- https://github.com/fluxcd/notification-controller/blob/v1.9.4/internal/notifier/factory.go
- https://github.com/fluxcd/notification-controller/blob/v1.9.4/internal/server/event_handlers.go
- https://github.com/fluxcd/helm-controller/blob/v1.6.4/internal/reconcile/install.go
- https://github.com/fluxcd/helm-controller/blob/v1.6.4/internal/reconcile/upgrade.go
