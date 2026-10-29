# Browser names and trust

Use the operator-selected Headlamp/Keycloak HTTPS names from `identity/context.yaml` and the routing inputs. Publish them through reviewed DNS or a deliberate local hosts edit to the selected physical ingress address. There is no assumed IP address or DNS domain.

Inspect the public CA's subject, dates and SHA-256 fingerprint before trusting it. A trusted CA can validate certificates for the names it issues, so trust only a reviewed public CA file; never install its private key. Use the workstation OS/browser's supported certificate settings, obtain local administrator approval when needed, and record where the trust entry was added so it can be removed afterward. Do not bypass certificate warnings.

Confirm browser issuer/callback/origin match configuration. Keycloak's retained route uses `/auth`; its admin console is `<Keycloak origin>/auth/admin/master/console/`, not the unconfigured root URL. Keep bootstrap/admin test passwords in protected files, never chat or screenshots.
