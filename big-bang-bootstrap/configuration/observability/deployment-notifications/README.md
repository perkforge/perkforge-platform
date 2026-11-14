# Platform deployment outcomes (inactive)

Native flow: **Flux notification-controller 1.9.4 generic Provider → existing
ntfy 2.37.2 named template → `platform-deployments`**. No bridge, new image or
polling controller. Related notification acceptance: #39. All resources remain
unselected; Provider and Alert are suspended, endpoint/environment unconfigured.

The namespace-bounded source selects all platform HelmReleases in `bigbang`,
including the umbrella and future Big Bang subcharts/dependencies. The umbrella
is labeled platform orchestration; other releases are platform components. This
is intentionally one event per relevant Helm action, not a claim the umbrella
represents all children reaching application readiness. Source fetches and tenant
control namespaces are excluded. Namespace ownership is the boundary: tenant
HelmReleases must not be placed in `bigbang`. Its current writers are platform
reconcilers/admins and trusted cluster controllers, not tenant roles; no admission
rule guarantees future placement. Keep that boundary in onboarding reviews.
Tenant deployment topics/routes require a separate audience and source review.
Platform engineers need explicit native topic subscription
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

## Scoped delivery and local opt-in

`packages/ntfy/auth/runtime/deployment-audience.yaml` is default-off. It verifies
the authoritative four-account snapshot against current OpenBao auth lists, adds
only `flux-deployments` write-only and the existing `corey-portal` reader topic,
preserves every previous hash/token/ACL, and uses CAS for the shared runtime.
It stores generated publisher material only in the protected local output directory.
A retry after CAS deliberately fails the prior-state guard: verify the five-account
desired state and continue missing steps, never rerun from stale four-user input or
rotate the token. Its only non-auth config addition is the dedicated template-dir.

`deliver.yaml` first renders and then, only when separately enabled, creates or
verifies the exact OpenBao publisher record/policy/short-lived SA-bound role. The
foundation creates the empty `flux-deployment-publisher` target. ESO uses Merge and
the protected `headers` includes a fixed `Click` header from the verified trusted
`deployment_click_url` base URL (local Headlamp `/`, never a guessed deep path).
The source link remains text; neither destination comes from event content.
ESO
can get/update/patch **only that named Secret**, not create/delete any Secret.
The accompanying namespace Role additionally permits only its named TokenRequest,
public CA get, own status updates and events. There is no network rule change.
A partial retry with an existing target stops: inspect exact desired objects
privately and resume only missing steps without overwrite or credential rotation.

The local opt-in root `clusters/local-deployment-notifications` extends the latest
platform-alerts root and adds only the template mount and native notification
objects. It is **not** selected by this change. The template-dir is separate from
the existing protected `/etc/ntfy` configuration mount; current public/private
mounts remain untouched. Verify existing template-dir is absent/compatible before
setting it, coordinate the single ntfy replacement, and preserve root enrollment
reference and both Grafana alert mounts when selecting this root. A later source
update to this root must not inadvertently drop a newer app rollout stage.
