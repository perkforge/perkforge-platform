# Identity activation plan: review before execution

This is a retained staged operational contract, adapted to an operator-selected physical cluster. No refactor, merge or default bootstrap authorizes execution.

1. Record the actual API identity/UID, node and storage inventory, existing controller/ingress ownership and headroom. Configure explicit node/path/storage-class, DNS, trusted issuer/audience, callback, client and credential-file inputs. Render full inventory and inspect scoped installer RBAC and network policies.
2. Approve exact credential generation/reuse, protected local storage and intended Secret delivery. Registry credentials go only to their intended registries/namespaces; CA private keys never go to application Pods. No credentials in CLI arguments/logs/Git.
3. Approve storage and namespace/foundation writes. Retain database PV/data on containment; the static node-bound reference is non-HA. Install PostgreSQL before Keycloak, then verify readiness, verified HTTPS discovery/JWKS and persistence.
4. Initialize a reviewed new realm/client/groups/test identities once with the gated Ansible playbook; do not adopt, rotate or rerun initialization silently. Map the exact admin group only. Developers/no-grants remain restricted.
5. Back up API-server configuration. For RKE2, inspect the pinned OIDC issuer/audience/groups/CA/hosts configuration and actual generated manifest before a separately approved control-plane restart. RKE2 automatically supplies the OIDC CA mount: no duplicate explicit mount. Retain certificate-admin recovery access.
6. Activate Headlamp HTTPS/OIDC. Test real login/logout/session behavior, token issuer/audience/expiry/signature rejection, admin cluster-wide authority, developer scoped reads and sensitive/cross-namespace denials. Restart persistence components sequentially only when explicitly approved.
7. Observe real host/node pressure and workloads with deployment-specific thresholds and duration agreed before activation. Record timestamps, events, failure hypotheses versus causes, fixes and verification locally. No fixed laptop/VM sizing assumption applies to the physical target.

Containment pauses the affected root/stage first to prevent reconciliation undoing manual stops. Stop only the newly activated identity workloads; preserve database storage, backups, existing Flux and previously healthy services. Root suspension pauses manifest updates, not running services or every child controller. Recovery and another API restart require the reviewed action scope.
