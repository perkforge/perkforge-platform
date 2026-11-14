# Operational Mattermost channels

Related #39. Default/check execution is inert; selected-target input and explicit
execution approval are required. This is a reusable source procedure, not a
second continuously running controller.

| Private channel | Authorized canonical human groups |
|---|---|
| `portal-deployments` | `/tenants/portal/{admins,developers,viewers}`, `/platform/{admins,engineers}` |
| `platform-alerts` | `/platform/{admins,engineers}` only |
| `platform-deployments` | `/platform/{admins,engineers}` only |

All belong to the existing private, invitation-closed `perkforge` team. A shared
team membership does not grant private-channel access. These are ordinary channel
memberships, never System/Team/Channel Admin. The existing independent recovery
operator is the explicit native creator/admin exception, not a derived role.
The existing `portal-alerts` channel and webhook remain unchanged.

1. `prepare.yaml` requires `mattermost_channels_apply/approved=true`, the existing
   protected bootstrap receipt plus origin/public CA/short-lived administrator
   token. It creates only missing exact channels and immediately writes protected
   per-channel receipts. Existing objects without matching receipts are refused;
   reconcile uncertain creation privately, never blindly repeat/adopt.
2. Before any ordinary membership, separately approve `invitation-policy.yaml`.
   It removes **only** `manage_private_channel_members` from the global ordinary
   `channel_user` role. Supply exact previously inspected role ID and permission
   list; all other permissions and admin roles are preserved. This affects all
   ordinary members, including existing channels. Exact drift stops. Verify live
   unauthorized invitations fail; do not equate metadata with permission proof.
3. Resolve current canonical Keycloak group UUIDs and complete enabled membership,
   then immutable `openid` subject/native-account bindings. Use the existing
   `context/plan.yaml` with `audience_model: operational-v1`, exact channel slug,
   `context_id: portal` or `platform`, and exact required groups. Reuse its guarded
   apply/readback; unknown/missing groups, unlinked accounts or unexpected native
   privilege block. No email/display-name matching, silent team joins, new humans,
   or global role elevation. Empty successful groups can remove channel members;
   failed authority reads cannot. Preserve only the recovery operator exception.
4. `bootstrap/webhook.yaml` accepts the new channel receipts and requires a unique
   `mattermost_hook_output_prefix` per channel. Each incoming hook is natively
   channel-locked. URLs and native receipts remain protected, never Git or logs.
   Caller owns short-lived session revocation and OpenBao/ESO delivery to exact
   consumers. No alert-controlled channel override is permitted.
5. Delivery and current role membership must both be verified before announcing
   availability. Verify ordinary invitation denial, foreign content denial, PE
   access, removal/offboarding, exact destination receipts and no ntfy regression.

This procedure does not schedule continuous membership reconciliation, create
accounts, join missing shared-team users, establish full tenant lifecycle or
close broader #39 acceptance. Do not promise that later Keycloak membership edits
synchronize automatically. Live state and any operator exception must be recorded
in the Portal C4 model after activation.
