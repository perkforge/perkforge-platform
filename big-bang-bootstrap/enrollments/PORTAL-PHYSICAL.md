# Physical Portal enrollment release gates

Portal's first implementation targeted the retired VM lab. Restoring the small,
stateless, admin-only SSO baseline is separate from the later AI-driven UI work.
Do not use the historical `enrollments/local` specimen for the physical cluster:
its source/parent name collides with Nextcloud and its old release is incompatible.

## Independent, paused published chain

[`local-portal/`](local-portal/kustomization.yaml) contains only a GitRepository
and Flux Kustomization, both named `portal-enrollments` in `flux-system` and both
suspended. No existing platform cluster root selects this pair. Rendering it is
safe and offline; applying or resuming it requires separate authorization.

The source selects published enrollment
[v2.0.0](https://github.com/perkforge/perkforge-platform-tenants/releases/tag/v2.0.0)
at `59462926a05fcb7a0ee8015f2998b233b706c9e8`, recorded under
`physical-portal-enrollment` in [release evidence](../../release-evidence.json).
Its `./clusters/local` root selects published physical app configuration
[v2.0.0](https://github.com/perkforge/perkforge-tenant-portal/releases/tag/v2.0.0)
at `e8de0e3cf68d01860b0addaa3b38e24f928d5ff6`. The released app source, child
Kustomization and HelmRelease remain suspended; chart values remain disabled.
Neither ordinary enrollment nor this pair includes foundation grants, ESO stores,
ExternalSecrets, runtime credentials or routing.

The parent references its own `portal-enrollments` source and uses the existing
`tenant-enrollment-admin` service account with `prune: false` and `force: false`.
The enrollment release's separately applied Portal foundation defines the bounded
`portal-enrollment` RoleBinding for GitRepository/Kustomization reads, creates,
updates and patches in `tenant-portal-config` (not deletion). This source wiring
does not create that grant or broaden root authority. The independent pair is operator-staged, not added to a live root;
do not bypass source-defined gates with an ad hoc `kubectl apply`.

Nextcloud retains its independent `tenant-enrollments` source at `v1.5.4`, parent
path `./clusters/local-nextcloud`, app `v1.1.3` and existing identity/suspension/
prune settings. All existing platform roots, including `local-velero` and
`local-external-secrets`, remain unchanged. Recheck live selections before any
separately approved promotion; publication alone deploys neither Portal nor ESO.

## Before activation

Publish a reviewed platform release containing this wiring. Reverify both
published dependency refs and actual path/context/render checks before use.
Review the cross-repository physical host/issuer, admin-only role mapping,
namespace/network isolation, public CA trust, dedicated TLS leaf, private-image
pull and narrowly scoped OpenBao/ESO runtime-secret delivery contracts. The URL is
`https://portal.perkforge.home.arpa`; the issuer is
`https://keycloak.perkforge.home.arpa/auth/realms/perkforge`.

ESO controller/CRDs, OpenBao auth/policies, tenant Store and actual consumer
ExternalSecrets are separate stages. Credential creation/delivery, foundation
creation, DNS, source staging and resume need their action-specific approvals.
No live state or credentials are supplied here.

Use the default-off [Portal-only DNS maintenance scope](../../infrastructure/ansible/DNS-MAINTENANCE.md)
only in a separately approved shared-DNS safe window. Preserve the active
Toshiba-to-Nextcloud transfer. Recheck measured capacity before deployment; the
small 25m/64Mi app request does not prove schedulability. Real HTTPS, SSO/admin and
non-admin denial, trust and recovery checks remain required after activation.

## Offline verification

Use exact checkouts of the two published commits above. Set
`PHYSICAL_PORTAL_ENROLLMENT_CHECKOUT` and `PHYSICAL_PORTAL_APP_CHECKOUT` to those
checkouts, then run:

```sh
KUBECONFIG=/dev/null PYTHONPATH=big-bang-bootstrap/tests \
  python3 -m unittest configuration.test_physical_portal_enrollment -v
```

The source tests always run. Released-chain tests explicitly skip without both
fixture paths; a skipped test is not a verified dependency chain. These tests make
no cluster calls. Existing CI remains paused, not restored by this source change.

## Identity explorer update

The active `local-platform-alerts` composition selects published enrollment v2.3.0 (699e407b087ad7ec2672eebe11b2eacdecf2f15f), config v2.2.0 and the build-once Portal v0.4.0 image. Apply the matching enrollment-owned runtime-contract image allowlist before promoting this root. Preserve both existing Grafana notification mounts, the Nextcloud composite, explicit admin policy and unprivileged Portal runtime. No credentials or access expansion is introduced. After rollout verify `/#/explore/identityLifecycle`, current/planned status labels and unchanged sign-in; document content is not live security evidence. Publication alone does not switch the running source.

## Published inventory reader selection

The new candidate selects enrollment v2.5.0 (`4651e35bb7505af4b419f0fb2864e8054e94ca41`),
app config v2.3.0 (`df3dcd8d061308beaf64dfb0e81cc8b3a14d88ae`) and checked
Portal v0.5.0 image `sha256:eaa66ab13be20079f188f4b5d8c5d79e274612f0f5742a8d3c0d2f0f6a48560d`.
The Portal UI reads a hash-verified read-only GitOps ConfigMap containing the
immutable **published enrollment v2.4.0 baseline**, not current root/live
reconciliation or customer tenant/user inventory. No runtime API token or network
egress was added. Source YAML remains authoritative and configuration CI verifies
materialized artifact provenance and actual valuesFrom wiring.

The exact ConfigMap create/admission boundary was separately approved and verified.
Before this promotion apply the matching v2.5.0 runtime image contract, preserving
the current root path and all Mattermost placement/namespace-ownership components,
Nextcloud and notifications. Coordinate with the active root-window owner; do not
switch to an older Portal-only root. Publication is not deployment. Verify image,
mount digest, authenticated source response and unchanged denial boundaries after
rollout. Tenant/user creation and truthful live inventory remain unfinished.
