# Lab Grafana HTTPS

The optional `clusters/local-metrics-limited-pilot-ui` root retains the limited
pilot and adds Grafana's route, Traefik-only backend policy and HTTPS URL/secure
cookie settings. Existing roots remain unchanged. No app scrape, SSO, tenant
access, anonymous access, logging or notification routing is enabled.

The endpoint is `https://grafana.perkforge.home.arpa/`. Existing RKE2 Traefik in
`kube-system` terminates TLS using **dedicated** `monitoring/grafana-local-tls`,
then uses HTTP `monitoring-grafana:80` -> Pod3000. This is the existing lab ingress
pattern; backend transport is not TLS. The policy combines the kube-system
namespace selector AND `app.kubernetes.io/name=rke2-traefik` Pod selector, with
only Grafana's two exact labels and TCP3000. Existing same-namespace monitoring
access remains. Grafana uses its existing `grafana-admin` input; no credential
read, copy, rotation, identity or login automation is added. Anonymous/OAuth stay
off. The HTTPS configuration replaces the Grafana Pod on reconciliation; claims,
resources, worker selector and existing data are unchanged.

## Separately approved preparation and activation

Use a clean published release containing this change, verify its actual tag and
commit, cluster UID, source/root identities and current app/storage health.
Nothing below is authorized by rendering or publication.

1. Verify the existing lab ingress has no WAN/public forwarding, tunnel, public
   DNS or unintended router reachability. `home.arpa` is naming, **not access
   control**. This source adds no firewall change or internet exposure and cannot
   establish the external router's configuration. Check existing Traefik entrypoint
   binding/source-address behavior; stop if the lab-only boundary is unproven.
2. Approve dedicated leaf issuance using the existing trusted CA, locally:
   `ansible-playbook -i localhost, infrastructure/ansible/playbooks/issue-grafana-certificate.yml`
   with protected reviewed inputs `grafana_certificate_apply=true`, absolute
   existing `grafana_certificate_ca_bundle`, reviewed
   `grafana_certificate_expected_ca_fingerprint` and private0700
   `grafana_certificate_output_parent`. The passphrase is entered locally, never
   in chat/Git/arguments. The default/check modes do not prompt or issue. A fresh
   private bundle contains a separate Grafana key, one-year SAN certificate and
   public root; the encrypted CA key is used in place, never copied or replaced.
   This is not a new CA or trust-store operation. Missing CA custody/passphrase,
   incorrect fingerprint, insufficient CA lifetime or unapproved key access stop
   issuance. Existing keys/credentials are never read during readiness checks.
3. Approve first creation of `monitoring/grafana-local-tls` using
   `configuration/ansible/platform-tls.yaml`, the existing protected platform
   inventory/release inputs, `platform_tls_applications=[grafana]`,
   `platform_tls_apply=true`, `platform_tls_namespaces_apply=false`, the new
   bundle and reviewed public fingerprint. This transmits the dedicated private
   leaf key/certificate to the Kubernetes Secret API using existing owner access.
   It refuses preexisting resources; Grafana readback requests only type/public
   certificate. No registry/admin Secret is copied. No automatic renewal, key
   rotation or replacement is provided: review renewal before expiry. Do not run
   `create-lab-pki.yml` to replace the existing CA.
4. Approve DNS scope `grafana-dns-record-v1` in the existing
   `infrastructure/ansible/playbooks/maintain-lab-dns.yml` procedure. Its owner is
   the root-owned `perkforge-lab-dns` service/config on control-1; its target is
   **worker-1's reviewed ingress address** from protected physical inventory,
   never a guessed or tracked IP. Requires all seven existing app records and a
   fresh exact base checksum. It appends only Grafana, validates, and restarts
   only that DNS service once (brief DNS interruption). Existing checksum,
   loaded-unit state and live UDP/TCP answers must be freshly verified; repository
   values are not live proof. Follow infrastructure/ansible/DNS-MAINTENANCE.md.
5. Approve the separate owner-admin `access.yaml` prerequisite only if absent.
   It grants `flux-system:platform-reconciler` monitoring-namespace create of
   Ingress/NetworkPolicy objects and named get/patch/update of `grafana-lab` and
   `grafana-from-traefik`. Kubernetes cannot restrict create by resourceName:
   this persistent ability can create **other routes/policies in monitoring**;
   it is material authority, not harmless namespace bookkeeping. No Secret,
   workload, RBAC or cross-namespace permission is added, and the app installer
   is not broadened. This file is deliberately excluded from receiving roots.
6. With separate action-time approval, conditionally select the exact released
   source and UI root, preserving platform-reconciler, prune=false, and existing
   temporary registry overrides until the containing release's effective values
   are verified. Guard UID/resourceVersion/current full specs and stop on drift.
   Do not reapply existing foundation, reset Helm, force reconciliation or
   broaden permissions. Normal controller reconciliation replaces Grafana for
   its URL/config checksum and creates only the reviewed route/policy.

## Acceptance and stopping

Verify existing app identities/readiness, all Helm releases/root/source, worker
placement, claims/Longhorn and baseline preservation. Verify authoritative DNS
UDP/TCP and workstation resolution, exact hostname/chain/CA over HTTPS (never
`-k`), authenticated login by the owner, anonymous dashboard denial, Grafana
health, datasource health/query and Prometheus targets/strict kubelet TLS.
23/23 healthy targets and HTTP200 health were observed through temporary
loopback-only forwards on 2026-11-06; this is not authenticated UI/datasource proof.
No test identities or new forwards are implied. Existing Grafana login is used;
Secret retrieval/login needs its own applicable approval.

Stop on drift, certificate mismatch, permission denial, unexpected exposure,
failed hook, unhealthy existing app/storage or unexpected rendered object. Do
not automatically rollback/uninstall/reset, remove a claim/Secret, relax admission
or disable reconciliation. `prune=false` means switching back alone does not
remove route/policy; any withdrawal must explicitly review those exact objects
and URL settings, preserving data/access. DNS maintenance's guarded restoration
is its documented transaction behavior, not authority for unrelated rollback.

Registry override retirement (#229), CA bootstrap lifecycle/install-versus-upgrade
regression and eventual pilot scope cleanup remain separate reviews. Never
remove functioning roots, trust bundles or claims as cosmetic cleanup.
