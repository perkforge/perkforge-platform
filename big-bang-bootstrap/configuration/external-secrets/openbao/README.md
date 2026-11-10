# Dedicated ESO machine authentication

Source preparation only. Nothing here is imported by legacy `platform-config`,
human SSO, Bitwarden recovery seeding or an active cluster root. Do not run the
old mixed human/machine playbook to activate ESO.

The default-off [adapter](../../ansible/openbao-eso.yaml) supports `inspect` and
`apply` only. It never changes Kubernetes RBAC, deploys ESO, creates credentials,
performs a Kubernetes JWT login, reads/writes KV values, deletes anything or alters
OIDC/legacy machine roles. Existing `kubernetes/eso-home-portal`, human identities,
recovery tokens, unseal material and KV mounts remain outside its write scope.

## Explicit inputs and boundaries

Copy [the public example](operator.example.yaml) to reviewed external inputs.
Use the existing local inventory and a clean, immutable published checkout. The
adapter verifies release metadata/tag, commit and clean tree before API use. Run
only during an exclusive approved configuration window: OpenBao policy/role
creation has no compare-and-swap here, so pre-read checks cannot prevent another
administrator racing a create. Stop on concurrent activity or ambiguous results.

Default/check mode performs no credential read or API contact. Real execution
requires the exact reviewed scope `openbao-eso-machine-v1`, explicit run/recovery
confirmation, expected OpenBao cluster UUID, HTTPS origin, public CA and an
existing separately approved operator-token file. The file must be owner-only
0600, owned by the operator, regular and neither a symlink nor a hard link. No
credential values belong in vars files, shell arguments, Git or output.

Before reading or transmitting a bearer, the adapter verifies trusted HTTPS,
initialized/unsealed active health, exact cluster UUID and OpenBao **2.7.2**.
Redirects, proxies, netrc and skipped certificate verification are disabled.
A no-log block contains authenticated representations and token use. Release
checks are read-only and do not authorize the subsequent security changes.

```sh
ansible-playbook -i /ABSOLUTE/reviewed-inventory.yaml \
  big-bang-bootstrap/configuration/ansible/openbao-eso.yaml \
  -e @/ABSOLUTE/reviewed-eso-inputs.yaml
```

Set operation/run/scope only in the separately approved external inputs. Merely
copying the example does nothing. Inspect reports counts/presence, not values;
it may report incomplete configuration without creating it. Apply creates only
missing objects after **all** preflight conflict checks and then independently
reads back the complete configuration. Exact repeats write nothing. Existing
mismatched state is refused rather than silently adopted, updated or widened.
A partial failure remains partial: inspect before any authorized retry, preserve
completed objects, and do not automatically rollback or reset authentication.

## Reviewed public API contract

1. Existing `platform/` and `tenants/` engines must already be KV-v2. No engine is
   created and no record is inspected by this adapter.
2. The only auth mount is `kubernetes-eso/`, type `kubernetes`, owner description
   `PerkForge eso-machine-v1`, default lease 300s and maximum 900s. Other mount
   types/descriptions, unexpected roles, conflicting config or broader existing
   policy content stop before mutation.
3. [Kubernetes auth config](kubernetes-auth.json) selects the existing pod-local
   rotating reviewer token and API CA. No `token_reviewer_jwt` or custom
   `kubernetes_ca_cert` is supplied. Pinned OpenBao source stores neither when
   using pod-local inputs; login-time loading is separate. The adapter refuses
   stored reviewer credentials, foreign CA/issuer settings or unknown fields.
4. Exactly `eso-platform` and `eso-tenant-portal` policies/roles are proposed. Each
   role binds one SA and namespace, audience `openbao-eso`, no default policy,
   300-second TTL and 900-second explicit maximum. Namespace selectors, periodic
   tokens, extra policies and inherited entity/group authority are refused.
5. Platform data is deliberately ungranted until each consumer's exact path is
   approved. Portal reads only three proposed records under `tenant-portal`,
   with no LIST, metadata access, writes/deletes, sibling or historical paths.
   This create-only adapter does not implement future permission updates;
   those need their own reviewed current-state/change contract.

## Separate Kubernetes and trust stage

[reviewer.yaml](reviewer.yaml) grants the existing `openbao/openbao` SA only
TokenReview creation, not SubjectAccessReview or `system:auth-delegator`. It is
not applied by the auth adapter or controller foundation. Verify the existing
OpenBao Pod has its rotating projected service-account token and API CA, exact
cluster identity and recovery before that separately approved grant. No static
reviewer token Secret is created.

Public OpenBao CA delivery and Store/auth-SA resources are separate post-controller
stages. Never reuse Keycloak CA trust without verifying the actual issuer and
rotation lifecycle. A Ready Store does not prove data delivery or tenant denial.

## Evidence and remaining acceptance

Real Ansible HTTPS fixtures test default/check, trusted-target-before-bearer,
protected input files, conflict/inheritance refusal, exact missing creation,
partial retry, no-change repeat and inspect. Release commands are mocked in the
fixture copy while source guards are asserted. The pinned native OpenBao test
checks real ACL allow/deny and role API compatibility with synthetic values and
root-minted test tokens, not Kubernetes authentication.

Separate live acceptance must prove wrong SA/namespace/audience denial; exact
role and identity policy closure; token expiry; tenant denial of platform/sibling/
historical records and metadata; no tenant use of the platform ClusterSecretStore;
and exact consumer synchronization/rotation without replacing unrelated Secrets.
Cleanup needs explicit scope. No live acceptance or deployment is claimed here.

Source behavior: [OpenBao config API](https://github.com/openbao/openbao/blob/v2.7.2/internal/builtin/credential/kubernetes/path_config.go)
and [stored versus login-time pod-local configuration](https://github.com/openbao/openbao/blob/v2.7.2/internal/builtin/credential/kubernetes/backend.go).
