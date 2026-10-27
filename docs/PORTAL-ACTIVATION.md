# Local portal activation

This is the operator's approved staging sequence, not evidence of a completed deployment.
Only the published v0.2.0 digest is selected. GitLab remains disabled. No PR is auto-merged.

## Review and application order

1. Merge the tenant CA-input companion, then this platform preparation PR. The tenant
   image remains disabled. The existing Keycloak Fleet bundle will resume one replica
   with its current 768Mi request/1536Mi limit and HTTPS hostname. Watch node/host memory
   and existing workloads; pause for an explicit decision if pressure affects them.
   Do not automatically stop Nextcloud or roll back resources.
2. Apply the reviewed `local-lab/fleet/gitrepos/local-lab.yaml` (adds the local TLS bundle)
   and `local-lab/fleet/gitrepos/portal-foundation.yaml`. The latter uses Fleet 0.16.2
   `spec.bundles`, **not an object in spec.paths**. It selects Home's shared templates
   with `enrollments/home.yaml`; existing foundation ownership stays separate.
3. Verify namespace quotas, runtime/deployment identities, all four fail-closed admission
   policies/bindings with current observedGeneration and no expressionWarnings, NetworkPolicies and the paused tenant GitRepo before credentials.
   Home's existing Project ceiling changes; Nextcloud's namespace allocation does not.
4. Wait for `cattle-system/{keycloak-lan,portal-lan}` Certificates to be Ready. They use
   the existing `rancher` namespaced Issuer; its CA private key remains in cattle-system.
5. Reuse `configure-keycloak-tenants.py --portal-only --apply` with explicit existing
   `--secrets-dir`, `--kubectl` and `--kubeconfig`. This mode requires the managed realm,
   reconciles only household-portal and Home's non-composite tenant-reader role grants,
   and writes `portal-keycloak-client-secret` owner-only. It creates no users and does
   not modify the Rancher client. Unowned clients or unexpected role scopes fail closed.
6. Run `configure-rancher-oidc.py --https-only --apply` with explicit kubectl/kubeconfig paths. This mode preserves the live principal list
   instead of reconciling the full catalog. Verify
   its plan first: only HTTPS issuer/browser authorization URL should change; existing
   client, groups/access permissions and local recovery login remain. Internal token,
   userinfo and JWKS endpoints remain compatible HTTP Services. Confirm discovery's
   issuer is HTTPS and validate Rancher login after the coordinated update.
7. Run `prepare-portal-secrets.py` first without `--apply`, then with it, supplying
   `--kubectl`, `--kubeconfig`, `--registry-authfile` (the protected user-staged file) and
   `--oidc-secret-file`. It requires existing namespace/admission, checks every destination
   owner/type before any writes, and copies only issued leaf TLS keys/certificates, the
   public CA bundle, portal client secret and GHCR pull credential. It creates no grants
   or namespace. The GHCR temporary file is removed only after delivery verifies.
8. Verify TLS hostname/CA from browser and the portal route, plus a real authenticated
   image pull. The staged credential already passed an authenticated registry manifest
   digest check; this is not yet a kubelet pull test. Browser clients must trust the
   existing lab CA and resolve portal/keycloak hostnames to the lab ingress.
9. After these prerequisites, prepare the final tiny reviewed activation change:
   tenant `enabled: true`, platform pin to that exact commit and lifecycle `active`.
   Do not enable the workload in this staging PR. Observe Fleet, one replica, health,
   real OIDC authorization-code login, cookie/CSRF behavior and the protected tenant API
   returning explicit disabled-source metadata. Verify unauthorized/non-Home access fails.

## TLS, routing and renewal limits

Only `keycloak.local-lab.test` is mapped in the portal Pod to the verified ingress
Service IP `10.43.163.193`. No cluster-wide DNS change is made. Re-check this address
before activation and after Service recreation. CNI ingress/egress enforcement and
Service DNAT behavior require live acceptance; the policy allows portal ingress from
Traefik on 3000 and portal egress to Traefik's HTTPS target port 8443 plus inherited DNS.

The CA ConfigMap is public certificate material, never a private key. Admission fixes
its name/key, read-only mount/path, NODE_EXTRA_CA_CERTS and hostname mapping, and rejects
additional mounts/hosts/env. The scoped deployer cannot modify ConfigMaps or TLS Secrets.
No TLS verification bypass is allowed.

Cert-manager renews the source leaf Secrets in cattle-system. Until a reviewed secret
synchronization facility exists, the operator must re-run the delivery helper after
renewal (it accepts only its labelled destinations). The helper requires a freshly
staged GHCR credential when rerun. This manual renewal dependency is intentional and
must be replaced/reviewed before production; no new controller or CA authority is added.

## Checks and limits

Tests render pinned Fleet 0.16.2 and Keycloak chart 7.4.0, exercise CA/host/env rejection
through Kubernetes CEL, and retain legacy ownership/transition/role tests. They do not
prove live identity claims, browser CA trust, CNI behavior, node pulls or available
capacity. The initial stage keeps application disabled and registration paused. Pausing
Fleet later preserves resources and does not stop an already running workload.

## Reviewed activation

The Home foundation now selects `active` and pins tenant commit
`2df910faea77f5af71cad75829f6400ee52de890`. Merging this change unpauses
Fleet and deploys one portal replica from the verified v0.2.0 GHCR digest.
Platform controls and operator-owned TLS, OIDC, registry Secret and public CA
were provisioned first. Twelve actual API-server dry-run checks passed, including
seven denied mutations. The temporary registry credential copy was removed.

This is activation intent, not a claim of completed live acceptance. After merge,
verify the node's authenticated image pull, readiness, trusted HTTPS, real Home
OIDC session and protected stub API, Alpha access denial, and existing service
health. GitLab remains disabled. Pausing an existing tenant preserves controls
and does not delete workloads; stopping a running replica requires a separate
reviewed workload change.
