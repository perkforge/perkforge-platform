# Data-stage health-read recovery

The observed kustomize-controller v1.9.5 cannot list Pods in `gitlab` while
assessing Garage StatefulSet health. Workload readiness alone does not establish
Flux root readiness. `prerequisites.yaml` adds a separate `gitlab-data-health-reader`
Role and binding, owned by `gitlab-data-foundation-v1`, granting only core Pod
get/list/watch in `gitlab` to `flux-system/platform-reconciler`. This necessarily
reveals Pod specifications in that namespace, including literal environment
values; keep secrets in Secret references. No Secret, logs, exec, Pod writes,
RBAC writes or cluster-wide rights are added.

## Separately approved delivery

Publish/review/release first. Recheck explicit API, context and cluster UID.
Inspect every existing foundation against the pinned release before any write.
Require all prior foundation objects present and unchanged, with only these two
new objects absent. Stop on any other missing/different object or foreign owner.
Use the existing create-only foundation procedure; never patch the old Role,
adopt foreign objects, or add RBAC to the Flux runtime root. Record exact new
UIDs and verify a zero-change repeat. Verify reconciler Pod reads in `gitlab`,
while Secret reads, exec, writes and Pod reads in unrelated namespaces stay denied.
Wait for root Ready and unchanged healthy workloads. No live delivery is
performed by this source change. If rollback is needed, review removal of only
the two new UID-verified objects; removing them restores the health-read failure.

## Node-origin checks after local SSH unlock

Use only the existing physical inventory, known hosts and public-key agent;
BatchMode, strict host-key checking and ForwardAgent=no. Verify each node's
hostname before testing. No sudo, package installation, trust changes or writes.
From the explicit verified cluster, read the current Ready Garage Pod IP and
PostgreSQL primary Pod IP and verify their exact StatefulSet/Cluster owners.
Do not reuse stale Pod IPs after a replacement.

On each node, run bounded credential-free requests to the Garage Pod IP:

```sh
curl --noproxy '*' --connect-timeout 3 --max-time 8 -sS -o /dev/null -w '%{http_code}\n' "http://${GARAGE_POD_IP}:3900/"
curl --noproxy '*' --connect-timeout 3 --max-time 8 -sS -o /dev/null -w '%{http_code}\n' "http://${GARAGE_POD_IP}:3903/health"
```

The S3 request must never return anonymous success. A reachable 403 establishes
application denial, not network isolation; timeout/refusal establishes only
unreachability. The admin listener must be unreachable from the node address.
Never send an admin token to a node. Kubernetes node-origin traffic may bypass
NetworkPolicy, so report actual outcomes rather than assuming Pod policy applies.

For PostgreSQL, stream only the verified public CNPG CA over SSH to stdin and run:

```sh
timeout 10 openssl s_client -brief -starttls postgres -connect "${POSTGRES_POD_IP}:5432" -servername gitlab-postgres-rw.gitlab.svc.cluster.local -verify_hostname gitlab-postgres-rw.gitlab.svc.cluster.local -verify_return_error -CAfile /dev/stdin -no_ign_eof
```

Require successful chain/hostname verification if reachable; distinguish timeout
from TLS failure. No database password or signing key is copied. The observed run is recorded below; these commands do not establish future
node-origin results. Reconfirm current
certificate validity and workload identities immediately before execution.

## Observed acceptance

On 2026-11-04 the separately approved v0.17.5 delivery created only the two
health objects, preserved all 35 existing prerequisites and repeated with zero
changes. The twelve permission checks passed; use `--subresource=exec` and
`--subresource=log` explicitly with `kubectl auth can-i`, rather than assuming a
slash in the resource argument tests the subresource. Flux root became Ready and
Healthy without a source promotion or workload rollout.

Read-only node-origin checks completed: Garage anonymous access was denied on
its local worker and unreachable from the other nodes; admin was unreachable
from all three. PostgreSQL TLS CA/hostname verification passed on its local
worker; the other nodes timed out. No credentials or remote writes were used.
These outcomes do not establish blanket node-origin NetworkPolicy isolation or
independent backup/restore. The commands above remain a repeat procedure with
fresh identity, certificate and authorization prechecks, not permission to run
future mutations.
