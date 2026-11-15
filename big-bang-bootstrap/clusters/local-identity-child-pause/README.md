# Corrected-artifact all-child hold checkpoint

Select H only after the old attempt's three children are proven suspended and
quiescent. Keep the existing local-identity-child-pause path and parent explicitly
unsuspended so it can apply child holds while switching to enrollment
`6890df6284170548c389742e61de7a0db6d00ef4` with foundation digest
`26fc17d269d3da67bbd202361fe3259117e6a6ce6d564a58d97ef35191e792f8`.

The corrected released artifact has new Job suffix 54819c8b56bfc3e8, but all three
children remain suspended. No provider Job may start at H. Preserve the failed
predecessor Job and receipts. Retry generation one binds the actual successful foundation predecessor and an
explicitly empty attestation predecessor. No issuer receipt existed; source CAS
migrates the owned group receipt rather than recreating the native group.

Before A, verify exact child UIDs, suspend:true, current-leader post-generation
suspension handling, new source/Job identity and no active predecessor work.
Failed or unknown parent/child Ready is not suspension proof. A parent-only hold
is insufficient. Do not weaken health, delete Jobs or infer automatic retry.
Audit shared-source consumers including metadata-only Helm reconciliations.
Image and budgets remain unchanged. A resumes foundation/attest only; B releases
membership only after fresh issuer/SSA acceptance. Those separate immutable
checkpoints require their live gates; this document is not execution authority.
