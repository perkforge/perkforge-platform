# Pipeline snapshot collector source package (inactive)

This packages an exact reviewed-source candidate patch against upstream v0.6.0,
not an upstream release or deployed exporter. `source.json` binds official upstream
commit, local prototype commit, complete patched Git tree, patch SHA256 and unchanged
Apache-2.0 license. Changed-file notices and rationale are in the patch's prototype
documentation. No configuration, project identity, token, CA, hostname or environment
is embedded in the binary. The same artifact is built once and configured per target.
Do not push this patch or branch to the upstream project or create another repository.

The patch-local Git attribute disables outer diff whitespace lint for unified-diff
context markers only; patch bytes are hash-verified and the applied source was linted.
`python3 verify.py` is offline and read-only. `prepare.sh` and `build.sh` are explicit
operator actions, never triggered by a selected root, workflow or import:

1. Obtain the official repository into a NEW isolated checkout and select the exact
   `upstream_commit` from `source.json`. Acquisition/network permission is separate.
2. `bash prepare.sh /path/to/isolated-checkout` refuses a different HEAD or any dirty
   files, applies the exact patch to its index, and verifies the complete patched tree.
   This intentionally alters only that checkout. An uncertain interruption is inspected,
   not blindly rerun; no reset/clean command is supplied.
3. With separately approved official Go1.26.8 available, run
   `bash build.sh /path/to/isolated-checkout /new/local/output`.
   Dependencies are those in unchanged upstream go.mod/go.sum, fetched through the
   official module proxy/checksum database. Tests include fake TLS only; no real API.
   The command produces a static Linux/amd64 binary, license, source receipt and hashes.
4. Independently repeat in a second fresh build environment and compare binary hashes.
   This recipe is reproducibility-oriented; two-build equality is NOT yet established.

No container base is silently chosen. Before any image publication, review a pinned
approved runtime base, CA mounting, nonroot user, SBOM/license/vulnerability evidence,
image-signing/provenance, reproducibility and destination registry authorization.
Do not bake target settings or credentials into an image. Platform deployment still
requires approved resources/network/custody/project scope and native API compatibility,
freshness/restart and notification acceptance. No artifact has been installed/published.

Default upstream behavior is unchanged without the explicit snapshot config flag.
See patched docs/pipeline-snapshot-prototype.md for metric/config ABI and limitations.

## Local reproducibility checkpoint

Two local builds of collector `51b74af0cff98191b61d073baa051f9d8b8d78f5`
with the pinned Go1.26.8 recipe produced byte-identical static Linux/amd64
binaries: SHA256 `c56aaaa66c596269dd20694756ce1d5142c184603f0a8e701694de440d6ef5f3`.
The second source tree was reconstructed from the exact upstream commit plus the
packaged patch; module verification and the full race suite passed. This is
same-host, distinct-source-tree evidence, not independent-environment, container,
vulnerability, native API or deployment acceptance. No image was published.
