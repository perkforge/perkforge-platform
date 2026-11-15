# Disabled reader to verified custody

Default off. `activate-keycloak.py validate KC_OPERATOR BAO_OPERATOR OWNERSHIP_RECEIPT
NEW_CUSTODY_RECEIPT INPUTS.json` makes no API requests. `apply` is a separate,
action-approved one-shot setup operation, not a runtime workload. Configuration
writes remain in `keycloak-custody.yaml`; the coordinator validates literal inputs,
locks both receipts and verifies exact non-root custody authority.

Inputs are exactly `run:true`, `scope:keycloak-reader-custody-v1`, a 64-hex
`setup_id`, HTTPS `bao_origin`, public `ca_file`, protected `reader_inputs` and
one approved known `foreign_group_id`. The reader inputs must select Portal,
forbid realm enablement, and match an owned PendingCustody receipt with all five
native IDs. No prior attempt is automatically retried. A fresh attempt requires
review of partial effects; there is no secret rotation, reset or record deletion.

## Authority and order

- Obtain separate informed approval for KC operator access, the one-record Bao
  operator, native client enablement and the bounded probes. Previous home root
  authority is unrelated. No root fallback or generic three-record operator.
- Exact policy `tenant-identity-bootstrap-keycloak-v1`, no other/identity policies,
  nonrenewable TTL 15–60 minutes, and byte-exact checked-in policy readback are
  required. The operator is not created by this source.
- Existing disabled-reader Ansible preflight rechecks native version, client,
  service identity, zero broad role/group inheritance and exact FGAP associations.
  Client token lifespan must be configured to 300 seconds.
- Read only that client's existing generated secret. CAS0 the one exact record,
  then verify version 1 and exact data before enabling the client. Payload is
  client_id/client_secret/setup_id/native_client_id. Only the first two values go
  to the isolated attestor through separately approved ESO delivery.
- Obtain one client-credentials token. Require the actual response TTL in 1–300
  seconds before permission probes. Read selected group/member endpoints, deny a
  known foreign group, and require 403 on each selected group's empty PUT.

Pinned Keycloak 26.8.1 `GroupResource.updateGroup` calls `requireManage(group)`
before rejecting an absent name, and only later updates the group. Therefore
`PUT {}` is non-mutating even if manage permission unexpectedly exists: 400 is
an acceptance failure, never success. This is one endpoint's permission proof,
not exhaustive absence of all write authority. No DELETE, membership write or
human identity change is used. Selected-member profile and descendant visibility
are native FGAP implications, not field-level opaque-subject permissions.

On failure after attempted enablement, disable only the owned client and verify
its disabled state; record failure stage, disable outcome and observed token TTL.
Retain the custody record and any uncertain native effects for review. Disabling
is **not immediate revocation** of issued access tokens: a normally accepted token
can remain valid up to 300 seconds. If the configured limit is ineffective or the
token response is lost, residual lifetime is longer or unknown, explicitly not
bounded by the intended limit. Abrupt process death/timeout may prevent cleanup;
ActivationRequested/ManualRecovery requires operator inspection, not blind retry.

ReaderAccessVerified means this bounded custody and permission check succeeded.
It does not deploy the runtime, prove tenant membership grants, configure all
platform-admin visibility, or complete project/event integration. The currently
empty Portal roster cannot provide positive tenant-grant acceptance.

## Evidence limits

Tests use actual local Ansible against synthetic TLS endpoints and fake secrets.
They cover success, uncertain custody write, foreign/read and manage denial
failures, excessive TTL, failed disable, retained records and retry refusal. No
live Keycloak/Bao activation is implied. The separate preparation fixture covers
native-shaped ownership/role/resource drift and partial creation failures.

Pinned native ordering reference:
[Keycloak 26.8.1 GroupResource.updateGroup](https://github.com/keycloak/keycloak/blob/26.8.1/services/src/main/java/org/keycloak/services/resources/admin/GroupResource.java).
The client `access.token.lifespan` setting is additionally checked against the
actual token endpoint response; source configuration alone is insufficient.
