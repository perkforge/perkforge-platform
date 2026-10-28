# Local-only tiny trial proposal — not an activation approval

This profile retains Big Bang 3.35.1's exact Flux versions/images, all four
controllers, security contexts, RBAC, CRDs and NetworkPolicies. Only resources
and hostname placement change. Dev's values/build and its pinned Flux remain
identical to published platform v0.2.0. Neither cluster is enabled or deployed.

## Inputs and rationale

- `examples/ansible/inventory.yaml`: local selects `local-tiny`; default/dev stays
  `pinned`. Bootstrap rejects local tuning on another inventory/environment.
- `examples/ansible/flux-local/`: four small resource/placement patches plus a
  native Kustomize template. `prepare-flux.yaml` stages them temporarily over the
  verified release checkout; it never edits that checkout or installs a second owner.
- `examples/clusters/local/values.yaml`: local Keycloak uses the earlier live lab
  allocation (250m/768 MiB request, 1 CPU/1,536 MiB limit), with worker placement.
  Headlamp, its DB and OpenBao also select worker via supported chart values.
  Other app budgets, pins, secret references and safety settings stay unchanged.
- Portal's current chart has no placement input. Its one Pod may land on either
  node; the per-node table conservatively budgets it on each alternative, not twice
  in the actual cluster total. Do not infer placement from a folder name.

| Controller | CPU / MiB request | CPU / MiB limit | Node |
| --- | ---: | ---: | --- |
| source | 50m / 128 | 500m / 256 | control |
| helm | 100m / 192 | 1 / 512 | worker |
| kustomize | 100m / 128 | 500m / 384 | worker |
| notification | 100m / 64 | 200m / 128 | worker |

CPU requests follow the same pinned upstream generated manifest (350m total).
Memory requests are deliberately above its 64 MiB/controller baseline; caps are
trial ceilings for few sources, not measurements of cold Helm/Kustomize peaks.
The Helm controller gets the largest budget. Keep all four initially: source,
Kustomize and Helm are essential here; notification is optional only without
Alerts/Providers/Receivers, but removing it saves little and complicates bootstrap.
No unrelated Big Bang packages or automatic Helm/Cypress tests are enabled.
Keycloak's observed earlier steady working set was about 568 MiB, not a startup
benchmark for this package/image/database combination. Do not lower its request
or cap further based only on that one sample.

## Before/after rendered budget

The before column is the preserved v0.2.0 local candidate, not current live usage.
Pods remain nine steady plus one disabled/unsized manual test Pod; PVCs stay 14 GiB.

| New stack only | Before | Tiny local |
| --- | ---: | ---: |
| CPU requests | 3.075 | 1.075 |
| Memory requests | 3,936 MiB | 1,984 MiB |
| CPU limits | 6.950 | 4.950 |
| Memory limits | 7,968 MiB | 4,288 MiB |
| Flux requests alone | 1.600 CPU / 2,208 MiB | 0.350 CPU / 512 MiB |
| Deployment maximum simultaneous surge | 1.400 CPU / 1,952 MiB | 0.400 CPU / 512 MiB |

Adding only the historical kube-system requests (2.175 CPU/2,776 MiB), not
Rancher/Fleet/apps, gives **3.250 CPU / 4,760 MiB**. A separate assumed storage
provisioner allowance (50m/64 MiB on control, limit 100m/128 MiB) gives
**3.300 CPU / 4,824 MiB**. This allowance is explicitly **not installed or pinned**
by this PR; select/render/approve the real storage component before any live trial.
RKE2 alone supplies no approved dynamic storage profile here.

`local-budget.yaml` is consumed by offline accounting tests. It records the
16:29 UTC 2026-10-28 baseline and assumptions, not a live scheduler policy:

| Node | System req CPU / MiB | Tiny + storage + portal alternative | Request space left | Planned floor |
| --- | ---: | ---: | ---: | ---: |
| control | 1.575 / 2,520 | 0.125 / 256 | 0.300 CPU / 877 MiB | 0.250 CPU / 512 MiB |
| worker | 0.600 / 256 | 1.025 / 1,856 | 0.375 CPU / 1,541 MiB | 0.250 CPU / 512 MiB |

Each node has only about 3,653 MiB allocatable; OS is not magically outside that
RAM. The request-space floor is a test-plan assumption, not proven peak capacity.
Replace this historical baseline with fresh clean-cluster evidence before proceeding.
Do not sum the portal alternatives as two real Pods.

**Important limit case:** worker system requests plus every assigned Pod at its
memory limit can reach 4,288 MiB, above the worker's allocatable RAM even before
its 512 MiB reserve. Cluster-wide limits plus system requests and the storage
allowance leave only about 114 MiB before OS reserve. Thus request-fit is not
full-load safety. This profile permits only a staged low-load experiment whose
measurements decide whether all four apps can remain active. Use the physical
target if peaks cannot retain reserve; do not disguise the failure by lowering
requests or ignoring limits. Images, DB startup, TLS/auth and restore are not proven.

## Stage protocol for a later separately approved clean target

No rebuild, apply, scale, unpause, realm/client creation or credential work was
performed. Existing coexistence is still rejected: Fleet owns Keycloak/OpenBao,
Nextcloud PVCs remain, and the old cluster has inadequate request capacity.

Before stage 0, explicitly settle preservation/backups or discard for the two
VM disks and every PVC/service, OpenBao recovery custody and the stable portal.
The existing `rebuild-local-lab.sh` reinstalls Rancher/Fleet and the old profile;
**do not run it unchanged**. A reviewed minimal RHEL/RKE2 provisioning entrypoint,
new cluster UID, hostname verification and storage/ingress ownership are prerequisites.
Do not allocate more VM RAM: host RAM is about 14.96 GiB and was already heavily
swapping (about 10.95 GiB swap used, 3.29 GiB available at this profile's host
snapshot). Existing swap use is not new capacity. Keep host activity comparable.

Start with paused seeds and platform packages explicitly disabled. The ordinary
cluster roots still have Headlamp/OpenBao enabled behind the paused umbrella;
**do not unpause them as-is for stage 0**. Review stage values in Git first.
These are supported Helm inputs, validated offline, not executable deployment files:

| Stage | Reviewed values/change | Gate before advancing |
| --- | --- | --- |
| 0: bare RKE2 | No Rancher/Fleet/old apps; approved storage/DNS/CNI/ingress prerequisites | Fresh baseline, node/host floors and PVC plan pass |
| 1: Flux | Tiny resources, same pinned images; all three platform app flags false, portal false | Cold source fetch and empty/controlled reconciliation; 10 min stable |
| 2: DB only | `addons.keycloak.enabled=true`, `addons.keycloak.values.upstream.replicas=0`; others false | Fresh 4 GiB DB PVC, approved secret refs; DB Ready, connection and storage checks |
| 3: identity | Set Keycloak replicas to 1 | Startup peak/Ready and approved realm/client/API trust checks; 10 min stable |
| 4: secrets | Enable `packages.openbao.enabled`; identity retained | Reviewed TLS/backend/unseal/recovery policy; Ready and authenticated checks |
| 5: UI | Enable `addons.headlamp.enabled` | Approved plugin, ingress/TLS, user-token API OIDC and cross-tenant denial checks |
| 6: portal | Separately reviewed tenant app enablement | Foundation/scoped deployer, approved digest/secret/client refs, callback/denial checks |

Stages 2–5 do not enable the portal. Database-only renders a zero-replica Keycloak
StatefulSet and one PostgreSQL instance; no fake standalone DB release is introduced.
The existing TLS-disabled OpenBao specimen and unfinished tenant foundations must
be replaced/reviewed before those live stages. No old PostgreSQL PVC can be reused
for PG18, and this is not an in-place Keycloak downgrade/migration.

Keep one worker Deployment rollout at a time: 100m extra request leaves at least
275m worker CPU request-space; concurrent allowed surges can exceed that floor.
No image/resource upgrades or broad reconciles of changed controller profiles
during the drill. A later maintenance plan must serialize updates; the bootstrap
is not a rolling-upgrade orchestrator. Stateful services here have no HA reserve.

Before each stage, collect read-only node metrics/stats/events, per-node requests,
Pending reasons, restarts and host MemAvailable/swap-in/out. For Keycloak cold
start, require at least **2 GiB worker available** beforehand (its 1.5 GiB cap plus
512 MiB reserve). Maintain **512 MiB node available** and **2 GiB host available**
afterward; these are initial conservative stop thresholds, not benchmarked minima.
Stop on any new OOM/restart, memory/disk pressure, unschedulable Pod, API/ingress
instability, failed auth/storage readiness, host swap growth over 256 MiB from
stage baseline or sustained swap-in/out over 1 MiB/s for a minute. Treat a startup
that cannot become healthy within 10 minutes as a failed stage, not permission to
raise limits, bypass policy, restart the old stack or continue. Retain evidence,
hold later stages and obtain the scoped recovery/pause authorization if needed.

## Offline evidence and confidence

Tests use the actual Ansible include/copy/template and native Kustomize assembly.
They compare every Flux object with the pinned base after removing only allowed
resource/hostname fields; images, security and RBAC must remain identical. Dev
build and pinned Flux compare with the verified v0.2.0 baseline. Full local/dev
child renders, staged flags, disabled defaults, external Secret contracts and
request/limit accounting are checked. No generated workload YAML is committed.

This profile is only publishable after tests/CI; a published version still is not
live approval. Runtime viability, kernel/host behavior and the missing operational
prerequisites remain unvalidated. Follow the release workflow, then select the
actual new tag if a later live experiment is explicitly approved; no future self-tag
or live credentials are supplied here.
