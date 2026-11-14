# Native Mattermost lab activation

Tracks [#395](https://github.com/perkforge/perkforge-platform/issues/395), following
source PRs385/387. This module preserves the current integrated Portal/Nextcloud
and platform alert roots. It uses the selected Big Bang3.35.1 package/image pins,
free Entry mode without a license or trial, and dedicated non-HA PostgreSQL8Gi +
files10Gi storage. It does not declare production/HA/restore acceptance.

## Ordered procedure

1. Review source and target inputs. `render.yaml` defaults off; check mode is inert.
   Set `mattermost_runtime_render=true`, HTTPS `origin` and `issuer`, verified
   `ca_file`/`ca_sha256`, existing `storage_class`, `node_selector`, exact `/32`
   `api_cidrs` and `ingress_cidrs`, and owner-only `output_dir`, all prefixed
   `mattermost_runtime_`. DNS/Traefik namespace/selectors are target inputs; the
   local RKE2 Traefik selector is `app.kubernetes.io/name: rke2-traefik`, not the
   generic default. Inspect live scheduling requests before choosing placement.
2. Prepare the exact approved DNS record using the released supported DNS
   maintenance procedure. Preserve unrelated records, use verified strict SSH
   trust and fix forward. Check DNS health and active backup work before restart.
3. Issue only the approved hostname TLS leaf with the existing verified CA
   procedure. Keep signer material in private temporary memory, clean up/lock
   afterward; never copy the signing key into this app. Verify hostname/chain and
   report actual certificate expiry. `prepare-record.yaml` takes the leaf/key,
   public CA and private directory as inputs, generates dedicated URL-safe machine
   credentials locally, and refuses a mismatched repeat. It never accesses a CA
   signer or API. Enable explicitly with `mattermost_runtime_prepare_record=true`.
4. Use existing `authorization/sso/mattermost/reconcile-client.yaml` to prepare
   the owned disabled confidential client with the generated `oidc-client` file.
   Preserve authorization-code only, exact `/signup/openid/complete`, basic/profile/
   email scopes and no group/role grants. Do not run its manual Secret delivery:
   ESO owns the same runtime Secret names. Native account linking and later client
   activation require actual readiness evidence, not guessed attestations.
5. After approved network/custody scope and reviewed source, run `activate.yaml`
   with `mattermost_runtime_activate=true`. Additional target inputs are
   `cluster_uid` (kube-system UID), `bao_server`, `bao_cluster_id`, `bao_token_file`,
   exact dedicated `record` path under platform KV, and private `record_file`.
   It checks cluster/vault identity, refuses secret/record/policy drift, uses CAS0,
   stages reviewed native installer/scoped operator authority, namespace-only ESO,
   exact Registry1 identity copies, target PVC and scoped policies. It waits for
   ESO and verifies every decoded payload before staging native values ConfigMap.
   Target record input is0600 and all secret operations are no_log. No root switch
   occurs here. It refuses implicitly changing an already-staged values ConfigMap.
6. Coordinate current root promotions, then select the reviewed immutable commit
   and `clusters/local-mattermost-pilot`, which extends `local-deployment-notifications`.
   Verify root/Big Bang/native operator/app/database readiness, volumes/UID2000
   fsGroup, RWO Recreate strategy, TLS/SiteURL, actual narrow traffic and preservation
   of Portal, Nextcloud, Grafana SSO/datasource/dashboards and alert rules.

The native wait hook remains enabled but its unrestricted policy is replaced
with exact API/DNS transport. Application traffic is limited to TLS ingress8065,
its own database5432, DNS and approved Keycloak HTTPS443/post-DNAT8443. No public
telemetry egress, shared backend credentials, MinIO operator or extra filestore
service. The application/DB use existing native images, not rebuilt variants.

## Human identity and alert acceptance

Signup remains closed. No automatic `/platform/admins`→Mattermost system-admin
mapping is introduced. Initial owner bootstrap/linking is limited to the verified
Corey identity; do not create unrelated members or enable realm-wide signup to
work around provisioning. If a native local-mode socket or durable break-glass
custody action is needed, describe its exact temporary surface/custody separately.
Then verify fresh Keycloak login and the intended platform/Portal team/channel.
Grafana remains the sole alert router; production firing/resolved/grouping and
broader tenant denial are distinct acceptance, not implied by app readiness.

Use focused offline renderer/custody tests plus the backend native rendered image
check. They do not establish live recovery, tenant isolation or phone/channel
receipt. Keep #395 open until its actual acceptance is verified.

## Preowned namespace ownership

Any target using these staged prerequisites must include the reusable
`runtime/namespace-ownership` Kustomize component in its root. It omits exactly
`mattermost` and `mattermost-operator` Namespace objects from the umbrella Helm
render, following the existing preowned namespace pattern. This does not delete
live namespaces, change their labels, or grant the umbrella cluster-wide namespace
authority. The local pilot composes this same portable component.
