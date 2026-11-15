# One fixed identity custody issuer

Source only; fresh informed root-token authorization is required. Existing home
setup approval is unrelated. There is no known restricted issuer that can mint
itself. Root is used only to install these five named ACLs, three exact ESO roles,
and two one-hour setup tokens, then revoke those tokens. It never writes/reads KV
values, signs into GitLab/Keycloak or enters any workload. No generic admin API
wrapper, wildcard ACL, auth-mount creation/reconfiguration or root rotation exists.

`run-issuer.sh --validate ROOT_FILE NEW_RECEIPT INPUTS.json` is network-inert.
`--apply` is separately gated; default/check are inert. Inputs are exactly
run:true, scope:identity-custody-issuer-v1, setup_id:64hex, bao_origin HTTPS,
public ca_file and expected cluster_id UUID. Protected ownership/ancestry,
nonblocking native receipt lock and literal schema are required. Public health
checks exact OpenBao2.7.2 cluster before reading/sending root. Source preflight
verifies the existing kubernetes-eso mount/config; it does not rebuild it.

## Fixed effects

- Setup ACLs: tenant-identity-bootstrap-gitlab-v1 (two exact GL records) and
  tenant-identity-bootstrap-keycloak-v1 (one exact KC record), byte-exact existing
  checked-in HCL. No inheritance/default policies.
- ESO policies/roles: eso-identity-writer, eso-identity-reader,
  eso-identity-keycloak. Each reads just its respective runtime record and self
  token metadata. Writer binds same-name SA in tenant-identity-writer; other two
  bind their same-name SAs in tenant-identity-attestor. Audience openbao-eso,
  TTL300/max900/explicitmax900, no default/periodic/selector/broad grants.
- All eight objects are read before any mutation; different existing content
  stops. Create absent objects only, verify readback. API policy/role creation
  lacks CAS: exclusive administrative window is required, not claimed atomic.
- Mint two service tokens via auth/token/create with exactly one setup policy,
  no_default_policy:true, renewable:false, ttl/explicit_max_ttl3600. Validate native
  response and each token's own lookup, including no extra/identity policy.
  Save only to fixed gitlab-setup-token/keycloak-setup-token private files beside
  the receipt, exclusive-create with file+directory fsync; never overwrite.
- Setup tokens' remaining TTL must still meet each consumer's900–3600s gate.
  Create only once the separately reviewed application/runtime batch is runnable.
  ESO authentication and workload-native denial tests remain separate acceptance;
  role source alone does not prove absence of effective identity inheritance.

## Failure and cleanup

Each token request is recorded durably before issuance; returned accessor before
secret storage. Source failure attempts revocation of exact known new accessors
only after lookup verifies unique display name, policy, explicit maximum and that
it is not root. No blind retries/remint on lost response or existing attempt.
An unknown created token may remain until the one-hour expiry; manual inspection
is required. Nonsecret receipts preserve partial stages/accessors, never tokens.

After consumers complete, run the same wrapper `--cleanup` with the original
receipt and inputs. It verifies exact owned accessors, revokes and checks lookup
returns400. Both must be accounted for before Cleaned. It never resets root,
deletes runtime records, removes ESO roles or erases local evidence. Setup ACLs
are deliberately retained, inert without tokens; removing newly created ACLs is
an optional separately reviewed cleanup, not silently done amid uncertainty.
Private local child-token files remain for operator cleanup and must not be
reused. Abrupt process termination can prevent cleanup; do not infer revocation
from a failed command. No background renewal/rotation is established.

Actual local Ansible/synthetic TLS fixtures use fake credentials and cover fixed
scope, foreign objects, health-before-root, default/validation inertness, extra
policy refusal, exact accessor cleanup and lost second mint. This is not live
root-use, ESO authentication or GitLab/Keycloak acceptance.
