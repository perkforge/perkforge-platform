# Query runtime credentials through ESO

This optional local renderer builds the same consumer contract for each adopter.
It does not contact OpenBao/Kubernetes, create credentials, deliver CA trust, or
select a deployment root. Use an existing private output directory and provide:

```yaml
query_eso_render_enabled: true
query_eso_output_dir: /absolute/private/output
query_eso_server: https://bao.example.test
query_eso_monitoring_namespace: monitoring
query_eso_gateway_namespace: tenant-observability
query_eso_record_root: observability/cluster-name
```

Run `ansible-playbook -i localhost, render.yaml -e @/absolute/inputs.yaml` from this
directory. Optional inputs are KV mount (`query_eso_kv_mount`, default `platform`),
auth mount (default `kubernetes-eso`), identity prefix (default `eso-query`), public
CA ConfigMap name (default `query-openbao-ca`), and controller namespace/SA
(default `external-secrets`). Server, namespaces and record root are target inputs.

The output uses two namespaced SecretStores and distinct non-mounting auth SAs.
Each generated OpenBao role binds exactly one SA/namespace, audience `openbao-eso`,
5-minute TTL, 15-minute maximum and only its matching policy. Policies read exact
records under `<mount>/data/<root>/monitoring/` or `/gateway/`; no list, metadata,
wildcard or write grants. Existing `eso-platform` policy is not modified.

Each ExternalSecret maps explicit properties from one record named after its
output Secret. TLS records contain `tls.crt`, `tls.key`, `ca.crt`. Gateway auth
records contain `htpasswd`. Monitoring `grafana-query-auth` contains
`GRAFANA_QUERY_USER`, `GRAFANA_QUERY_PASSWORD`, `GRAFANA_QUERY_CA_PEM` for Grafana's
`envFromSecrets` contract. Supply corresponding password/hash material separately;
the renderer neither derives it nor proves the two match.

Before activation, verify ownership/absence of all target Secrets, populate only
approved dedicated records, and deliver verified public OpenBao CA (`ca.crt`) to
the referenced ConfigMap in each destination. Never copy signing keys there.
`Orphan`/`Retain` preserves outputs if the declaration or remote record is removed;
it does not prevent overwriting an existing colliding Secret. Do not apply over
unreviewed existing targets. Pod reload/restart remains a coordinated consumer step.

The generated controller Roles grant namespace-wide Secret creation/update (Kubernetes
cannot restrict CREATE by name), exact auth-SA TokenRequest and local CA reads.
They add no global permissions. ESO's separate foundation still has cluster-wide
Secret list/watch exposure and requires its own approval. Stores/roles do not
hide data from the trusted controller or cluster administrators. Keep these auth
SAs and Store/ExternalSecret authoring unavailable to tenant workloads/users.

Focused offline verification: `PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest
configuration.test_tenant_query_eso -v` from the repository root. Real auth login,
wrong-SA denial, synchronization and refresh are deployment acceptance, not claims
made by this renderer.

`seed.yaml` is a separately opt-in, create-only native OpenBao seed. It verifies
cluster identity/TLS before reading the operator bearer, refuses existing records,
and writes with KV-v2 CAS zero. Its private output directory retains the dedicated
CA key and random credentials outside Git; app records never contain the CA key.
Certificates expire after 90 days (CA after 365): record this operational deadline
and rotate through reviewed new records/consumer refresh before expiration. This
is not an automatic certificate controller. Partial writes are retained on failure;
inspect/reconcile forward rather than rerunning over existing records blindly.

`activate.yaml` applies only the dedicated query policies/roles and rendered ESO
consumers. First verify baseline Kubernetes auth is configured, the target
namespaces/public CA exist, all seven destination Secrets are absent or owned by
this deployment, and the explicit activation scope is approved. Pass the same
verified origin/cluster ID/operator-token path as seeding; secret data is redacted.
