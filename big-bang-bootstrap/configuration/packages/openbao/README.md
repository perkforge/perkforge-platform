# OpenBao initial administration stage

Observed 2026-11-01: v0.13.0 default stage deployed OpenBao; one-time approved
3-share/threshold-2 initialization, unseal, root-token API access and fresh
root/umbrella/package readiness passed. Headlamp/Keycloak stay disabled.

This package adds OpenBao after the Rancher source stage. Publishing it does not
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
   username/password. Use the separately approved protected recovery subdirectories, never generic
   username/password flat files.
   Unseal and verify token/UI access privately; record only safe results. Root-token
   retirement/scoped break-glass design and audit/backup remain explicit follow-up.

The chart does not operate or recover the server for us. Until initialization,
unseal, verified client access and independent custody are completed, installation
alone does not meet the admin-login acceptance goal. Real activation and these
security operations require their own approval; this draft performs none.

## Executed one-time Ansible procedure

[openbao-initialize.yaml](../../ansible/openbao-initialize.yaml) runs on the
workstation, disabled by default. Explicit apply verifies cluster identity and
protected fresh custody, then checks `/sys/init` over a separately established
127.0.0.1-only TLS port-forward. Existing initialized data refuses execution.
It initializes exactly 3 shares / threshold 2, persists the response before any
further operation, separates root-token custody from unseal shares, submits two
shares through stdin, and verifies unsealed health plus root-token lookup-self.
Secret tasks use `no_log`; no token/share is placed in command arguments.
The temporary full response is rewritten to share-only after root custody saves.
A failure during initialization or custody is **uncertain**, requiring inspection;
never rerun automatically. This playbook is not a restart/unseal recovery tool.

The approved temporary custody is `~/src/perkforge-tmp-secrets/openbao-v0130-<run>/`
with `root/` and `unseal/`, owner-only 0700/0600. Keeping every share together is
single-location custody, not independent holders; the operator owns migration
and explicit cleanup. Root-token retirement, scoped recovery, audit/backup and
restart/recovery testing remain separate work. No live realm/policy mappings.
[Synthetic tests](../../../tests/security/test_openbao_initialization.py) exercise
actual Ansible success, initialized-store refusal and default-no-action paths.
