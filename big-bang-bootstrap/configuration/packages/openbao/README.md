# OpenBao initial administration stage

This candidate adds OpenBao after the Rancher source stage. Publishing it does not
promote the physical cluster's release or authorize credentials, TLS delivery,
initialization or unseal. No Keycloak integration is activated. Existing proven
OIDC roles, policies and Ansible API configuration under `operations/` are retained
for the later authorization review, not applied at server startup.

## Deployment and trust

Official chart **0.30.6**, OpenBao **2.7.2**; the existing source pin/checksum is
retained. A single worker-hosted server uses a 10 GiB Longhorn claim and PebbleDB.
This is a **non-HA lab** configuration, not the production architecture recommended
by [OpenBao](https://openbao.org/docs/platform/k8s/helm/run/). Longhorn replication
is not an OpenBao backup or a substitute for independent recovery material.
The StatefulSet uses OnDelete updates; upgrades need backup and explicit unseal
planning, not a blind rolling restart or assumed downgrade.

TLS is required at the server. No ingress, public service, injector, CSI provider,
Kubernetes-auth delegation, service discovery, auto-init or auto-unseal is enabled.
The server account has no chart-created Role/ClusterRole bindings or persistent
service-account-token Secret. The namespaced installer manages the six rendered
objects; the StatefulSet controller creates its claim. Helm tests stay disabled.
No cluster-admin bind/escalate grant is needed for this selected chart render.

A separately approved delivery must create `openbao/openbao-server-tls` containing
`tls.crt`, `tls.key`, and public `ca.crt`. Use **current physical-cluster PKI**,
never old trial keys. Verify chain, expiry/key match and SANs for
`openbao.perkforge.home.arpa` (including any additional service DNS names actually
used by clients). The existing frontend-only `platform-tls.yaml` does not create
this backend TLS Secret; don't repurpose it or silently disable TLS verification.
No certificate or private key is generated or delivered by this MR.

## Separately approved activation and first access

1. Select a reviewed published release; verify target UID, capacity and Longhorn.
   Apply common/Rancher then OpenBao installer prerequisites using
   `configuration/ansible/openbao-prerequisites.yaml`,
   `openbao_foundation_apply=true`. Rancher's already-reviewed source-writer role
   supplies ordinary Flux root HelmRepository access; root cannot self-grant RBAC.
2. Deliver the checked TLS Secret, then promote the existing source. Don't rerun
   bootstrap or replace existing data/Secrets. Stop on conflicts and preserve logs.
3. Expect an uninitialized/sealed server to be **NotReady**. The HTTPS health probe
   deliberately does not remap sealed/uninitialized responses to success. Kubernetes
   HTTPS probes test health, not certificate identity; administrator clients must
   separately verify the trusted CA/hostname. Coordinate the finite Helm timeout
   with the separately approved init/unseal window; if it expires, diagnose and
   approve a single reconciliation reset after unseal. Never hide the state.
4. Use a separately approved **loopback-only** pod port-forward and a client with
   current CA trust and TLS server name `openbao.perkforge.home.arpa`. No skip-verify,
   token in URL/arguments, or ingress exposure. Initialize **only after proving
   this is a new uninitialized store**. Never reinitialize an existing store.
5. Securely capture the initial root token and separate unseal shares using the
   approved private workflow. OpenBao has token administration, not a native admin
   username/password. Do not put unseal/recovery material in the generic app cache.
   Unseal and verify token/UI access privately; record only safe results. Root-token
   retirement/scoped break-glass design and audit/backup remain explicit follow-up.

The chart does not operate or recover the server for us. Until initialization,
unseal, verified client access and independent custody are completed, installation
alone does not meet the admin-login acceptance goal. Real activation and these
security operations require their own approval; this draft performs none.
