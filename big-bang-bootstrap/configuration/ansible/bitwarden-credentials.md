# Bitwarden credential storage

Use this human-operated procedure to store one explicitly approved bootstrap or
human break-glass **Login** item in Bitwarden Password Manager (`bw`), independently
of the cluster and Keycloak. OpenBao remains the runtime secret store; platform
and tenant scopes stay separate, with ESO access limited to approved consumers
([#31](https://github.com/perkforge/perkforge-platform/issues/31)). This is not a
Bitwarden Secrets Manager (`bws`) integration or a replacement for OpenBao.

No command below is authorized merely by this guide. Credential issuance,
retrieval, vault storage/sharing, rotation, runtime delivery and cleanup each need
their applicable approval. For existing credentials, storage does not change the
issuer's account or password. A generated password is not a working account until
the separately approved issuer operation succeeds.

## 1. Choose custody and approve the exact operation

- Identify the service, environment, purpose, credential owner and existing source.
  Confirm whether this is a new credential or custody of an existing one.
- Select the exact Bitwarden server/account UUID and personal vault **or**
  organization UUID and collection UUIDs. Review who can access an organization
  item, including administrators; approval must cover those recipients. A folder
  or descriptive item name is not an access boundary. Do not create memberships,
  collections or grants, or move/share an existing item, as an implicit fallback.
- Check the operator's item register or selected vault view for an existing item.
  Resolve its exact UUID before reading/updating it; never select by name alone.
  Do not dump/list/export the vault to find one credential. An existing matching
  item means stop and review reuse or an explicitly approved update, not duplicate
  creation. `bw create item` has no idempotency key or unique-name guarantee.
- This procedure excludes root tokens, unseal shares, CA signing keys, SSH private
  keys, MFA seeds and session/API-authentication material. Preserve their separately
  reviewed custody and recovery design. Do not force them into Login fields or
  collect independently held recovery shares into one generic item.

## 2. Prepare a protected workstation session

Use the existing reviewed `bw` 2026.10.1 executable by absolute path (`BW` below),
with its supported Node runtime when installed through npm. Do not install,
reconfigure the server, log in, unlock or create new API credentials implicitly.
The owner authenticates/unlocks the intended account privately and provides the
existing `BW_SESSION` only in the process environment. Never paste it into a
command, shell profile, vars file, chat or Git. Use the already selected
`BITWARDENCLI_APPDATA_DIR` when applicable; do not switch accounts to bypass denial.

Run only in a trusted, owner-controlled shell, with tracing/debugging, terminal
recording and secret-bearing callbacks disabled. Use an encrypted workstation
and approved protected storage outside Git and cloud-synced folders. Set
`umask 077`, disable tracing (`set +x`), enable Bash `set -euo pipefail` in a
reviewed script, and use `set -C` to refuse overwriting output files. Do not use
`tee`, `echo` of values, command substitution of passwords, or secret values in
`jq --arg`, `bw --session` or other command arguments. Base64 is not encryption.

Before running snippets, set these **paths only**, never credential values:

- `BW`: absolute path to the reviewed executable.
- `RUN`: a newly created owner-only 0700 custody directory outside Git, with trusted
  parents and no symlinks. All files in it must be owner-only 0600 regular files.
- `USERNAME_FILE` and `PASSWORD_FILE`: the approved protected input files, with
  verified owner/modes and no symlinks/hard links. Preserve exact bytes; do not
  silently trim whitespace or add a newline when capturing the issuer's values.

Capture `"$BW" status` privately in `"$RUN/status.json"`, with stderr in a separate
0600 file. Check the account UUID, server URL and `unlocked` state against the
approved target before reading or writing any item. After approval to synchronize
that account, run `"$BW" sync` with both output streams redirected to protected
files, require success, then repeat the identity/status check. Stop on stale data,
wrong account/server, locked state, denied access or unexpected permissions.
Never print status/errors wholesale into a task log.

If a new password is explicitly approved, the issuer's supported generation policy
comes first. `bw generate` can prepare a password into a protected file with its
output/error streams redirected; verify the chosen length/character rules and
exact bytes locally. Do not regenerate an existing credential or silently create
an alternative after an error. Issuance/rotation at the service remains separate.

## 3. Prepare one Login item privately

Write `"$RUN/metadata.json"` through a trusted local editor that does not leave
unprotected swap/backup files. Include only the approved `name`, `organizationId`
and `collectionIds`. Personal custody must explicitly use `null` and `[]`;
organization custody must use the exact approved organization and nonempty
collection list. Include service/environment/purpose in the non-secret name.
Verify these values and recipients before continuing; placeholders must not be
submitted. Real item/account metadata belongs in protected operational records,
not tracked examples. Do not include passwords, tokens or recovery bundles in
names, notes, URLs or custom fields.

The authenticated CLI supplies templates. This example creates only a Login with
username/password and no TOTP, notes, custom fields or autofill URIs:

```bash
"$BW" get template item > "$RUN/item.template.json" 2> "$RUN/item-template.err"
"$BW" get template item.login > "$RUN/login.template.json" 2> "$RUN/login-template.err"
jq -e --slurpfile meta "$RUN/metadata.json" \
  --slurpfile login "$RUN/login.template.json" \
  --rawfile username "$USERNAME_FILE" --rawfile password "$PASSWORD_FILE" '
  def uuid: type == "string" and
    test("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$");
  if (($meta | length) != 1 or ($login | length) != 1 or
      ($username | length) == 0 or ($password | length) == 0) then
    error("Missing or invalid input") else . end |
  $meta[0] as $m |
  if (($m.name | type) == "string" and ($m.name | length) > 0 and
      ($m | has("organizationId") and has("collectionIds")) and
      ($m.collectionIds | type) == "array" and
      (($m.organizationId == null and $m.collectionIds == []) or
       (($m.organizationId | uuid) and ($m.collectionIds | length) > 0 and
        all($m.collectionIds[]; uuid)))) then . else
    error("Explicit personal or organization custody is required") end |
  .name = $m.name | .type = 1 |
  .organizationId = $meta[0].organizationId |
  .collectionIds = $meta[0].collectionIds |
  .folderId = null | .favorite = false | .notes = null | .fields = [] |
  .login = ($login[0] | .username = $username | .password = $password |
    .totp = null | .uris = [] | .fido2Credentials = [])
' "$RUN/item.template.json" > "$RUN/item.json" 2> "$RUN/build.err"
```

Privately validate the JSON against the approved metadata and original files,
including nonempty username/password, `type: 1`, exact organization/collection
membership, and absence of unrelated data. Review expected bytes without displaying
values. Stop if any step fails. The complete payload is sensitive even when encoded:

```bash
"$BW" encode < "$RUN/item.json" > "$RUN/item.encoded" 2> "$RUN/encode.err"
```

## 4. Create once, then verify privately

Immediately before the write, confirm approval still covers this exact item,
account, destination and recipients. Recheck account/status and that nobody has
created the item meanwhile. Submit the encoded payload on stdin, never as an
argument. The successful CLI response includes decrypted fields, so capture both
streams privately and never display the response:

```bash
"$BW" create item < "$RUN/item.encoded" > "$RUN/created.json" 2> "$RUN/create.err"
```

Require a successful exit and a valid returned item UUID. Preserve the receipt
privately even if validation fails. **Never rerun create automatically.** A timeout,
interruption, malformed response or failure after submission can have an uncertain
outcome. Stop, inspect the selected vault with the owner, and resolve the created
item's exact UUID before any retry. Do not delete an item to make the run look clean.

After a successful create, synchronize the approved account again, require success,
and retrieve only the returned UUID, with stdout/stderr in new protected files:

```bash
ITEM_ID=$(jq -er '.id | select(type == "string" and
  test("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$"))' "$RUN/created.json" 2> "$RUN/item-id.err")
"$BW" get item "$ITEM_ID" > "$RUN/readback.json" 2> "$RUN/readback.err"
```

The UUID check must succeed before the get; never fall back to a name. Compare the
readback's UUID, Login type, name, organization and exact collection set against
the approval and payload. Compare username/password bytes locally with the source
files; emit only pass/fail, never values, secret hashes or payload diffs. Confirm
no unintended notes, fields, TOTP, passkeys or URIs were added. A mismatch stops for review;
it does not authorize edit, move, rotation or deletion. Fresh sync plus readback
verifies vault custody, not service authentication or disaster recovery.

## 5. Record custody and handle later changes

Keep a protected metadata-only register containing item UUID, server/account,
organization/collections, service/environment/purpose, verification time and
approval reference. Do not retain credential values or hashes in that register.
The response, readback, JSON, encoded payload, stderr files and original inputs
remain sensitive custody until separately approved cleanup. Never remove the only
tested recovery source. Finish through the owner's agreed session-locking procedure
and unset `BW_SESSION` in the task shell; coordinate before locking a shared session.

An existing item's update needs its exact UUID, approved field changes and private
readback. `bw edit item` replaces the supplied object; preserve unrelated fields
and stop if concurrent changes or ownership are uncertain. No automatic upsert,
bulk migration, rotation, collection change, revocation or local-file deletion is
part of this create-only procedure. Removing a file does not revoke a credential.

Use [Bitwarden recovery bootstrap](bitwarden-bootstrap.md) only for its separately
approved, exact Login-field mappings. Its organization/collection requirements
must be checked before selecting an item; personal-vault creation does not imply
adapter compatibility. Initial recovery material stays out of downstream records.
Only selected downstream values may seed OpenBao under that runbook's separate
approval, and existing records are not overwritten. ESO consumers and runtime
rotation need their own reviewed platform/tenant scope. Independently recoverable
vault access and an isolated recovery exercise remain necessary
([#101](https://github.com/perkforge/perkforge-platform/issues/101)).

Command reference: [Bitwarden Password Manager CLI](https://bitwarden.com/help/cli/).
Offline checks of examples do not prove real vault access, sharing permissions,
credential validity, live rotation, ESO delivery or recovery acceptance.
