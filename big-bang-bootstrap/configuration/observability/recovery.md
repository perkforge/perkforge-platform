# Monitoring recovery and retained state

This is a human-reviewed recovery procedure and cleanup inventory, not an
activation entrypoint. It grants no access, runs no retry and contains no
cluster certificate, key, credential, UID or physical address. Use the exact
published source/cluster identities and fresh live evidence; a render is not
proof that a hook ran. Do not rerun a first-install playbook against existing
credentials or foundations.

## Operator webhook trust lifecycle

The pinned monitoring wrapper selects `IgnoreOnInstallOnly`: the actual Helm
install renders Ignore, while **upgrade renders Fail**, including the native
patch Job's `--patch-failure-policy=Fail`. This is not permission to relax a
running webhook. The certificate-create Job runs pre-install/pre-upgrade; the
trust-patch Job runs **post-install/post-upgrade**. If initial workload readiness
fails before the post hook, a subsequent upgrade can set Fail with empty trust
bundles before that hook can repair them. An install-only/offline render misses
this lifecycle failure.

Native `patch.enabled=true` deliberately omits webhook `caBundle`; its patch
Job owns injection. Merely putting a CA in values does not inject it on that
path. Do not disable the hook, change failurePolicy to Ignore, add installer
access or rotate certificates to bypass this failure. First inspect hook
execution, operator readiness and exact pinned render in BOTH Helm modes.

For this release/name selection the rendered identities are:

- Serving Secret: `monitoring/monitoring-monitoring-kube-admission`.
- Service: `monitoring/monitoring-monitoring-kube-operator`, port443.
- Both cluster webhook configurations: `monitoring-monitoring-kube-admission`.
- Mutating entry: `prometheusrulemutate.monitoring.coreos.com`.
- Validating entries: `prometheusrulevalidate.monitoring.coreos.com` and
  `alertmanagerconfigsvalidate.monitoring.coreos.com`.

Re-render names/paths for the selected release before approval; stop if they
change. The internal webhook CA is **not** the browser/ingress lab CA.

If the native hook cannot complete, the narrow one-time recovery is:

1. Read current identities, resourceVersions, complete public webhook arrays,
   service paths/ports, operator Secret mount and ready endpoints. Confirm the
   only problem is empty trust; all failure policies must already be Fail.
   Stop for other causes, changed identities or degraded existing apps/storage.
2. Obtain action-specific approval to retrieve only the existing **public** CA
   and serving certificate, conditionally update only the three trust fields,
   and separately request at most one normal retry if demonstrably necessary.
   Secret GET authority is not field-restricted by Kubernetes RBAC: do not add
   any new Secret getter grant or call this harmless namespaced access.
3. Use exact field projections, never whole Secret JSON or `.data` wildcards.
   The pinned certgen helper supports legacy public CA field `ca` and serving
   certificate `cert`; verify the pinned helper/source before choosing fields.
   Never request `key`, `tls.key`, credentials or registry/admin Secret data.
4. In protected local memory, verify CA constraints/self-signature/validity,
   serving certificate issuer/signature/server-auth purpose/validity and exact
   DNS SAN `monitoring-monitoring-kube-operator.monitoring.svc`. Verify the
   certificate source matches the operator's actual mount/endpoint. Record only
   public fingerprints; never commit environment certificates or evidence.
5. Recheck the serving Secret UID/resourceVersion. For EACH exact webhook
   configuration, prepare JSON Patch with tests for metadata UID,
   resourceVersion and the entire original `/webhooks` array. The only writes
   may be `add /webhooks/<verified-index>/clientConfig/caBundle` using the
   existing matching public CA. Verify every index/name/service/path first and
   all preconditions for BOTH objects before the first write. Keep every
   failurePolicy=Fail and every other field unchanged. Refuse a nonempty,
   different bundle; do not rotate/adopt unexpected trust.
6. Apply only the approved guarded patches, then read back and compare each
   complete webhook array against the original with only those CA fields
   changed. Recheck serving Secret identity/version. A partial failure or
   concurrent change stops for inspection; there is no automatic rollback,
   cleanup, further patch, rotation or permission expansion.
7. Inspect current release counters and handled request/reset annotations to
   avoid racing an owner action. Only with its separate approval, request ONE
   normal supported retry/reset if needed. Never use force/uninstall. Confirm
   actual admission succeeds, native post-upgrade patch retains Fail and trust,
   releases/targets/apps/claims remain healthy. Preserve local recovery evidence.

`test_metrics_webhook_lifecycle.py` exercises the actual pinned chart install
and upgrade paths, hook ordering/policy and caBundle ownership. It is offline
source proof, not live authorizer, cryptographic or admission acceptance.

## Source and permission ownership

The selected `clusters/local-metrics-limited-pilot-ui` root carries monitoring
and Grafana values through the existing Big Bang owner. Keep these distinct
owners when comparing live state with Git:

| Configuration | Authoritative source | Reconciliation owner |
|---|---|---|
| Chart pins, pull references, worker placement, retention, bootstrap-admin reference and disabled Grafana migration | `candidate-values.yaml`, `pilot/`, `limited-pilot/` | Flux root, Big Bang, then the child Helm releases |
| Installer identities, namespaced Helm storage, ConfigMap-only Grafana reader, named CRD/webhook permissions and kube-system metric Services | `metrics-prerequisites/foundation.yaml` | Separately gated owner-admin prerequisite delivery |
| Namespace ingress isolation and exact API-server webhook sources | `metrics-prerequisites/templates/network-policy.yaml.j2` | Separately gated prerequisites with protected target inputs |
| Six platform dashboard ConfigMaps | `metrics-prerequisites/dashboards.yaml` | Prerequisite delivery, then the namespaced Grafana sidecar |
| Grafana route and Traefik ingress policy | `grafana-ui/ingress.yaml`, `grafana-ui/network.yaml` | Flux root |
| Grafana route-writing permission for `flux-system:platform-reconciler` | `grafana-ui/access.yaml` | Separate owner-admin prerequisite, outside the root receiving its grant |
| Runtime operator, Prometheus and kube-state-metrics RBAC | The pinned monitoring chart rendered from these values | Monitoring child Helm release |

Common root/umbrella identities and ConfigMap/HelmRelease writing permissions
remain in `../packages/bigbang/prerequisites/`. Do not move owner-admin grants
into the root that receives those grants or grant broad namespace/cluster access
merely to remove an ownership boundary. The Grafana UI Role permits creation of
Ingress/NetworkPolicy objects in monitoring (Kubernetes cannot name-restrict
create), while get/update/patch are limited to the exact two owned objects. It
permits no Secret reads, Role writes, bindings or deletion.

A read-only comparison on 2026-11-07 against deployed v0.26.0 verified the foundations,
UI grants and runtime monitoring RBAC against their source. This does not prove
all effective authorizer/admission behavior or replace separately approved
negative tests. Root ConfigMaps and generated public monitoring/Grafana/CRD values
also matched Git. The redundant inline registry fields listed below remain live;
retirement has **not** run. The three native webhook entries retain matching
nonempty trust bundles and Fail; runtime CA injection remains hook-owned rather
than an environment certificate copied into Git.

Protected registry/admin/TLS material, service-account tokens, API-server
addresses, runtime UIDs and resourceVersions stay outside tracked configuration.
Keep source templates, secret references and supported delivery/recovery steps
in Git, not exported runtime credentials or generated Helm state. Both monitoring
claims remain retained; no cleanup here deletes, recreates or resizes them.

## Registry overrides: review before retirement

The published package-local `values.global.imagePullSecrets` references now
supply the existing immutable `monitoring/private-registry`; they create/copy no
credential. The following live recovery overrides may still be retained:

| Owner | Added path | Preserve |
|---|---|---|
| `bigbang/monitoring` HelmRelease | `.spec.values.global.imagePullSecrets` | Every other child value |
| `bigbang/grafana` HelmRelease | `.spec.values.global.imagePullSecrets` | `.spec.values.upstream.admin` and every other value |
| `bigbang/bigbang` HelmRelease | `.spec.values.monitoring.values.global.imagePullSecrets` and `.spec.values.grafana.values.global.imagePullSecrets` | Every other owner value |

This is an inventory, not authority to remove them. Before a separate guarded
retirement, verify the selected tag contains the fix, compare fully merged child
install/upgrade renders WITH/WITHOUT only these fields, and prove identical pull
references/resources/security. Capture originals outside Git. Guard current
UID/resourceVersion/full spec; remove only the reviewed added fields, never
whole `spec.values`, the admin reference, a credential or a concurrent edit.
After identical merged renders are proven, retire the owner additions first and
verify normal reconciliation still emits the same references, then retire only
the child additions one transaction at a time. This avoids an owner restoring
child recovery fields. Preserve the existing source-owned admin reference. Stop if current effective values differ or permission is absent.
Acceptance requires authenticated image pulls, all releases/Pods/claims and
existing app identities healthy. No automatic rollback or retry is implied.

## Active pilot paths are not disposable names

`clusters/local-metrics-limited-pilot-ui` currently composes the limited metrics
pilot and lab UI. Its inherited `limited-pilot` exclusions defer control-plane
host scrapes, application integrations, blackbox probes and logging. Grafana SSO,
tenant access and notification routing remain separate selections.

Do not rename/remove an active root, its bases, values references, namespace,
trust, grants or claims as cosmetic cleanup. First inventory source/root pins,
composition, enrollment references, retention and protected inputs. A future
non-pilot naming change needs equivalent rendered resources, an explicit new
reviewed root selection and health acceptance BEFORE old-path retirement.
`prune=false` is preserved; switching paths alone does not withdraw old objects.
Keep this scope review separate from Nextcloud SSO and from any future expansion
of monitoring authority, storage or scrape scope.
