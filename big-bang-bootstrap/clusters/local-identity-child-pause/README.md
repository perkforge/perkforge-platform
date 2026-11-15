# Corrected-artifact all-child hold checkpoint

Select H only after the old attempt's three children are proven suspended and
quiescent. Keep the existing local-identity-child-pause path and parent explicitly
unsuspended so it can apply child holds while switching to enrollment
`8bc0dd10acef2f40971502a26f42f74f16e5b9f4` with foundation digest
`c5cde73be1b1c02ed0d71db4172be70aec4751b15d0ed2c07cce6185620ce7df`.

The corrected released artifact has new Job suffix 74a1fd77a43038f5, but all three
children remain suspended. No provider Job may start at H. Preserve the failed
predecessor Job and receipts. Retry generation zero and empty predecessor are
deliberate: no issuer receipt existed; new code revision changes the invocation.

Before A, verify exact child UIDs, suspend:true, current-leader post-generation
suspension handling, new source/Job identity and no active predecessor work.
Failed or unknown parent/child Ready is not suspension proof. A parent-only hold
is insufficient. Do not weaken health, delete Jobs or infer automatic retry.
Audit shared-source consumers including metadata-only Helm reconciliations.
Image and budgets remain unchanged. A resumes foundation/attest only; B releases
membership only after fresh issuer/SSA acceptance. Those separate immutable
checkpoints require their live gates; this document is not execution authority.
