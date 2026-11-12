# GitLab, Keycloak and protected-project runner — inactive preparation

This current-main feature reconciles GitLab-only work from stacked #114. It does
not import observability predecessors or change their PR bases. GitLab, SSO and a
working runner are one acceptance outcome. The ordinary roots and
`clusters/local-gitlab-review` remain disabled; none of this work is deployed.

Read [the coordinated procedure](coordinated-outcome.md) and
[the shared operator contract](../cloudnative-pg/README.md) before activation.

| Area | Prepared source | Remaining live evidence |
|---|---|---|
| GitLab | Big Bang 3.35.1 / package 10.4.2-bb.0 / 19.4.2-ee Free, exact tested webservice digest | Real install, capacity/support, initial recovery and persistence |
| Lab sizing | One webservice/shell/Sidekiq HPA replica; Toolbox/PostgreSQL request 250m and Workhorse 100m; limits and memory retained | Explicit non-HA acceptance, placement, migrations and surge |
| Data services | Shared CNPG operator, dedicated PostgreSQL/Valkey, no-discovery Garage | Approved foundation, credentials/TLS, native startup and S3 behavior |
| PostgreSQL TLS | Supported extraEnv/CA mount with native verify-full, exact CNG transport tests | Real provider CA/SAN, generated application config and database flow |
| Credentials | Private existing-input assembly, create-only immutable Secret/CA delivery | Separately approved real generation/delivery and rotation plan |
| Keycloak | Dedicated disabled-client prepare/activate/disable, S256 and exact scopes | Fresh MFA/browser flow, native account approval and instance-admin assignment |
| Native access | Exact UID/provider/subject, bounded private-group grant/revoke | Real tenant/project cases; complete session/token offboarding is separate |
| Runner | Protected project, paused registration, private token receipt, isolated manager/job identities | Actual registration, CNI/DNAT egress, clone/artifact/deny/drain cases |
| Backup | Owner-selected encrypted external drive; cron disabled | Drive authorization, capacity, backup and independent restore |

## Conservative home-lab CPU requests

For a single GitLab user with a few repositories, the first sizing pass changes
only CPU requests: Toolbox 1000m to 250m, dedicated PostgreSQL 1000m to 250m,
and Workhorse 600m to 100m. All memory requests/limits, CPU limits (respectively
2, 2 and 600m), replicas, chart/image pins and security/storage controls stay
unchanged. This frees 2000m of requests, not physical CPUs. The roughly 40-hour
observation window had one-minute peaks of about 2m, 69m and 8m respectively;
it does not establish demanding backup/restore or future concurrency capacity.

Publication alone does not deploy. Before separately approved release promotion,
check current per-node fit, effective init-container requests, rollout surge,
PVC placement and a recoverable backup. Do not run heavy CI, imports or backups
during replacement. Toolbox uses Recreate and is briefly unavailable; the
single-instance PostgreSQL operator may restart its Pod, briefly interrupting
GitLab. Do not promise a zero-downtime rollout or manually patch live resources.
Freed requests may automatically allow previously Pending workloads to start;
verify their storage and readiness too. Aggregate free CPU does not prove that a
single large Pod fits on either worker.

After promotion, check PostgreSQL/app readiness, login, repository clone/push,
one small CI job, and normal background work before another reduction. Exercise
backup and a separately approved isolated restore before lowering Toolbox memory
or making stronger maintenance-performance claims. Retain the previous immutable
release for source-based rollback if readiness, database response, job completion
or backup behavior regresses. Monitor latency, queues, throttling and OOMs as well
as CPU/memory. Neither low idle use nor these offline tests proves N+1 capacity.
Flux, Nextcloud and other application sizing are outside this change.

The pinned GitLab chart treats discovery of `monitoring.coreos.com/v1` as enabling
monitoring even when `global.monitoring.enabled` is false. The source-owned child
post-renderer removes only `gitlab-gitaly`, `gitlab-webservice` and
`gitlab-webservice-workhorse` ServiceMonitors in `gitlab` while app scrape
integration is deferred. Exporters, Pod annotations and installer permissions stay
unchanged. Offline regression renders include the installed monitoring APIs and
exercise the actual umbrella and child post-renderers; a default Helm template
without those APIs does not reproduce this path. Enabling app scrapes later needs
a separate source/access review, including removal of these exact deletions.

## Authored configuration entrypoints

Ansible owns all configuration management. Python under verification/filter
plugins validates state; independent models and runtime probes live in tests.
Every playbook defaults off and contacts no API in check mode.

- `prepare-foundation.yaml`: existing recovery password and Garage RPC/admin files.
- `prepare-credentials.yaml`: separate `application` (DB/Valkey/OIDC) and later
  `runner` profiles. App preparation never requires or writes a runner token.
- `prepare-object-credentials.yaml`: existing S3 key to GitLab/Fog and Toolbox formats.
- `prepare-registry.yaml`: separately approved existing Registry1 input files to one
  private image-pull manifest; exact app/manager/job delivery profiles, no login.
- `prepare-transport.yaml`: existing directly CA-signed web/object/Valkey leaves;
  verifies reviewed CA hash, constraints, server purpose, hostname, key match and
  at least one day of validity. It issues/renews nothing; intermediate chains
  need an explicit extension.
- `deliver-credentials.yaml`: create-only exact application, runner, foundation, object-store
  or per-leaf TLS profile. Context/API/cluster UID, ownership, private files and
  existing-object comparisons guard every write; no implicit adoption/rotation.
- `deliver-public-ca.yaml`: separately reviewed public trust only, including
  `runner` → `gitlab-runner/gitlab-runner-public-ca` with the hostname `.crt` key;
  no signing key.
- `reconcile-garage.yaml`: owner-local forwarded admin API, full node ID, supplied
  dedicated key, explicit first-layout gate, private intent receipt and local lock.
- `reconcile-client.yaml`: dedicated disabled GitLab client lifecycle with no
  role/group grants. It reuses exact shared canonical mapper validation.
- `reconcile-membership.yaml`: bounded native private tenant-group membership.
- `prepare-runner-network.yaml`: private endpoint-specific NetworkPolicy manifest;
  no DNS lookup or policy application.
- Runner `../gitlab-runner/reconcile-registration.yaml`: paused modern native
  project-runner lifecycle with protected-project checks and one-time token custody.

Private input files are canonical, owned, mode 0600. Output/state directories
must already exist as owner-only mode 0700. Private outputs refuse drift rather
than rotating. Never put passwords/tokens in command-line variables or chat; use
owner-local protected vars/files. No signing keys, credentials or physical IP/MAC
inventory are tracked. Public topology uses hostnames and relationships only.

## Ownership and stages

Shared CNPG lives in `cnpg-system`, initially watches only `gitlab`, and needs
explicit namespace Role bindings. Global CRDs/webhooks and privileged installer
permissions are separate owner-admin foundation inputs, not self-granted by an
application. Additional database namespaces require reviewed watch/RBAC changes.
The application database belongs to GitLab; the operator remains reusable.

Dormant roots select providers → data → app → runner from the same immutable
release. They have no effect until separately approved source promotion. The
review root adds only disabled public values. Provider CRDs must be established
before selecting database CRs, preventing a dry-run/bootstrap dependency cycle.
Private credentials, namespace/pull credentials, trust, delegated installers and
native app/runner approvals must precede their stage.

All package installers are in `bigbang`, matching HelmRelease ownership, with
namespace-scoped app permissions. Installer automount is off. CNPG is explicitly
privileged for its named cluster resources; no installer is bound to cluster-admin.
Kubernetes create cannot be name-scoped. Garage GitOps has no Secret CRUD and no
automatic persistent-data deletion authority.

Registry, KAS, Zoekt, AI, embedded OpenBao, bundled runner, Prometheus, ingress
controllers and cert-manager stay disabled. The required database, Redis and
object store are real external dependencies; chart 10 does not bundle them.
Free OIDC provides login, not paid group sync, group-derived admin or tenant ACLs.
No paid license is assumed. Generated Rails secrets as well as root recovery
material must be preserved and independently restored.

Render, synthetic API and isolated transport results do not establish full
application, browser, runner, persistence or backup success. See
[the acceptance boundary](coordinated-outcome.md#coordinated-acceptance).

Data-stage recovery and pending node-origin checks: [health-read recovery](health-read-recovery.md).
