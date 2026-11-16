# One-record rotation issuer (default off)

`run-writer-issuer.sh --validate|--apply|--cleanup ROOT_FILE ISSUER_RECEIPT INPUTS.json`
uses native Ansible HTTPS operations only. Default invocation and Ansible check
mode are inert. This source is not consent to read root, mint authority or rotate
GitLab. Require fresh exact approval of root use, the one policy/child, custody,
cleanup and an exclusive administrative window. No KV, ESO, auth-mount or GitLab
operation occurs in this issuer. The child policy permits only the separately
reviewed existing writer-record rotation coordinator.

Protected literal JSON contains exactly `run:true`,
`scope:"writer-rotation-issuer-v1"`, `setup_id` (64 lowercase hex), `bao_origin`
(verified HTTPS), `cluster_id` and `ca_file`. All paths use the reviewed private
ancestry/regular-file/no-follow/size rules; root/input/receipt/output/lock/CA are
separate. A nonblocking receipt lock serializes the whole transaction and direct
playbook execution cannot bypass the Linux owner/descriptor lock proof. Keep the
reviewed checkout and custody directory exclusive to the trusted operator; this
is not isolation from another malicious process running as that same OS user.

The issuer checks public health, exact cluster identity and pinned Bao2.7.2 before
reading root through a guarded descriptor. Root must have only the root policy,
no identity policy. Only `tenant-identity-writer-rotation-v1` is read/created from
byte-exact `writer-rotation-policy.hcl`. An existing mismatch is never overwritten.
The ACL endpoint has no CAS: the exclusive administrative window is a real
precondition, not a claim of atomic create. An uncertain ACL response retains the
receipt and stops before minting. The ACL is retained after cleanup.

One normal **service child** is requested: explicit one policy, no default,
nonrenewable, TTL and explicit max3600s. `no_parent` is omitted, preserving native
false/default child semantics; no orphan or periodic endpoint is used. Returned
identity must differ from root, match accessor/token, exact policy/display marker,
service/nonorphan/creation TTL/max/creation time, and remaining900..3600s. Only then
is the token exclusively written to the fixed0600 sibling
`writer-rotation-setup-token`, usable as the TOKEN argument to `rotate-writer.py`.
Neither root nor child is printed by normal commands; Ansible's entire active
block is no_log. All durable receipt/file transitions fsync file and parent.

The separate issuer receipt contains selection binding, stage/request time,
accessor and output hash, never bearer values/root accessor. Existing attempts
never remint, including Requesting with no response or absent output. Unknown
mint outcome can leave a child alive for at most its requested3600s; manual
recovery/expiry is required. **If a returned accessor cannot be durably recorded,
no token is delivered and automatic cleanup is unverified**, even though the
response existed in memory. This deliberately does not turn an undurable or
arbitrary response into revocation authority. Preserve the receipt and inspect
under separately approved recovery; do not rerun issuance.

Cleanup reauthenticates the selected root only after health, uses only the exact
durable owned accessor, excludes root, and verifies the child's policy/display,
creation time/TTL/type/nonorphan before revoking. Already expired/revoked requires
exact native400 `errors:["invalid accessor"]`, not any400. A second readback must
confirm the same denial. That exact error-body compatibility is synthetic-tested,
not yet corroborated against pinned native2.7.2; a different body must report
cleanup unverified, never silently relax the guard. Only then is the matching private token artifact removed;
foreign bytes are retained and reported, never repaired. The ACL, receipt and root
input remain. Cleanup failure is not reported as verified revocation. A separate
explicit cleanup invocation never mints or rotates anything.

`test_writer_rotation_issuer.py` runs real local Ansible against synthetic TLS
with fake tokens: inert/check, wrong cluster before root, nonroot, foreign/uncertain
ACL, exact single mint, strict child and root-accessor rejection, lost response/no
replay, safe cleanup/error400/foreign artifact refusal and durability failure.
This is not live OpenBao acceptance, root authorization or an expiry extension.
