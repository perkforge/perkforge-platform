# Native-host staging reference — completed, do not rerun

Operator completed BatchA at22:22:38UTC and standalone BatchB at22:33:05UTC.
Full extraction and final readonly checks succeeded; size11,300,782,080bytes.
The earlier partial-paste uncertainty was resolved before that approved run.
Keep the blocks below as reviewed reference/parity fixtures, not current next steps.

Review ownership first: native user reports `/srv`, `/run`, `/var/log` are
root:root 0755. Existing identities are `dnsmasq` (UID 999, primary GID 65534,
nologin) and `www-data` (UID/GID 33, nologin). Confirm the GID-65534 group name on
the native host before filling the dnsmasq group input; do not guess or add groups.
HTTP workers use www-data, not the dnsmasq account or a new shared group.

## Ownership decision to approve

Recommended: **root:root directories 0555 and files 0444** in both serving trees.
The existing unprivileged identities can read public installer content but cannot
write or chmod root-owned files. They receive no new group membership. ISO mode
and ownership are not accepted as final host policy: metadata includes UID/GID
2024 as well as 0, so normalize everything inside the new roots before exposure.

This conflicts with `tftp-secure`, which requires ownership by dnsmasq's effective
user. Service-owned 0444 files can be chmodded by their owner, so they are not
strictly read-only. The offline template now requires explicit
`pxe_tftp_ownership_policy: root-readonly` acceptance and omits `tftp-secure` for
that policy. The mandatory alternative safeguards are the dedicated fixed TFTP
root, no symlinks/special files, root-owned non-writable tree and independent
interface/source ingress filtering. The operator selected this policy and completed its staging gates.
If retaining `tftp-secure` is required, stop and review a read-only filesystem/mount
strategy separately; no mount is part of the batch below.

Current execution environment exposes `/srv` read-only with remapped ownership.
The assistant cannot stage there with current permissions. Native execution, or
separately approved and verified native write access, is necessary. Do not redirect
media into home/the checkout or bypass the projection. No such access was attempted.

## Proposed commands: choose a bounded batch for explicit approval

These are **proposal text**, not permission to run now. Use a native Bash
terminal. Each whole block starts a separate Bash process with an explicit ISO
path argument; replace its single quoted `/ABSOLUTE/PATH/TO/...` argument only
when execution is approved. No inherited `PXE_ISO` variable is needed. An unchanged
placeholder stops before writes and prints the named failure step/status.

Strict options and ERR trap stay in the child process. The parent `if` handles
failure and keeps the caller open. The child's printed completed/failed status is
the result; the wrapper's final printf means the caller's `$?` is not the batch
status. Do not copy only the inner body or wrap that body in an `if`/function that
would mask `errexit`. Capture command-substitution status before testing output.
Stop on failure; preserve partial state for review, with no automatic deletion.

**Historical incident:** the uncontained paste closed Konsole. Native stat at
22:15:02 found the four paths absent; no cleanup was needed then. The corrected
child-process workflow was reviewed and separately approved, and both batches
later completed. This reference does not authorize another staging run.

### A — preflight and new private directories only

```sh
if BASH_ENV=/dev/null bash --noprofile --norc -s -- '/ABSOLUTE/PATH/TO/rhel-10.2-x86_64-dvd.iso' <<'PXE_BATCH_A'
set -Eeuo pipefail
step='startup'
trap 'rc=$?; printf "Batch A stopped at [%s] (status %s). Inspect partial state before retrying.\n" "$step" "$rc" >&2; exit "$rc"' ERR
step='explicit absolute ISO argument'
PXE_ISO=${1-}
[[ "$PXE_ISO" == /* ]]
step='ISO regular file and no symlink'
test -f "$PXE_ISO"
test ! -L "$PXE_ISO"
step='ISO canonical path'
canonical_iso=$(readlink -e -- "$PXE_ISO")
test "$canonical_iso" = "$PXE_ISO"
step='ISO SHA-256 match'
printf '%s  %s\n' 'e15cb333529c332e76e4b1b946efe3515c99f996546675aec18e8effdf2540a5' "$PXE_ISO" | sha256sum --check --status
step='native /srv ownership and write authority'
test ! -L /srv
parent_metadata=$(stat -c '%u:%g:%a' /srv)
test "$parent_metadata" = '0:0:755'
sudo test -w /srv
step='existing service users and primary group'
getent passwd dnsmasq www-data
getent group 65534
step='available bytes and inodes'
python3 - <<'PYTHON'
import os
v = os.statvfs('/srv')
assert v.f_bavail * v.f_frsize >= 16 * 1024**3
assert v.f_favail >= 10000
PYTHON
step='pilot root must not already exist'
test ! -e /srv/perkforge-pxe-pilot
test ! -L /srv/perkforge-pxe-pilot
step='WRITE SECTION: new private pilot root'
sudo mkdir -m0700 /srv/perkforge-pxe-pilot
sudo chown 0:0 /srv/perkforge-pxe-pilot
step='WRITE SECTION: private child directories'
sudo mkdir -m0700 /srv/perkforge-pxe-pilot/http /srv/perkforge-pxe-pilot/tftp
sudo mkdir -m0700 /srv/perkforge-pxe-pilot/http/rhel-10.2
sudo chown 0:0 /srv/perkforge-pxe-pilot/http /srv/perkforge-pxe-pilot/tftp /srv/perkforge-pxe-pilot/http/rhel-10.2
step='new directory metadata'
sudo stat -c '%u:%g:%a %n' /srv/perkforge-pxe-pilot /srv/perkforge-pxe-pilot/http /srv/perkforge-pxe-pilot/tftp /srv/perkforge-pxe-pilot/http/rhel-10.2
PXE_BATCH_A
then
    printf '%s\n' 'Batch A completed. STOP and review; no next batch is authorized.'
else
    pxe_batch_status=$?
    printf 'Batch A failed (status %s). Caller remains open. Do not rerun or clean up automatically.\n' "$pxe_batch_status" >&2
fi
```

Stop to verify all new directories are root:root 0700. This is the smallest
practical write batch; it copies no media. It creates no runtime/log directories.
Native `/srv` must have no unexpected ACL/write delegation; stop for review if
its native metadata differs or the permission check fails.

### B — non-mount media staging, only after A is reviewed

### Standalone invocation — historical reference, completed by operator

The incomplete paste was held, destinations were inspected empty, and a separate
approved standalone run then completed successfully at22:33:05UTC. Do not rerun
against populated staging; any future changed/partial state needs inspection and
specific recovery approval.

`stage-media.sh` contains the same reviewed Batch B body; an offline parity test
prevents drift. Execute it with Bash and an explicit ISO argument, never `source`
or `eval`. No executable-bit change is needed. After state review and approval,
from this review worktree root the short invocation shape is:

```bash
if BASH_ENV=/dev/null bash --noprofile --norc pxe/pilot/stage-media.sh '/ABSOLUTE/PATH/TO/rhel-10.2-x86_64-dvd.iso'; then :; else pxe_status=$?; printf 'Batch B exited %s; inspect before retrying.\n' "$pxe_status" >&2; fi
```

Use the exact reviewed native absolute script/ISO paths if not in the review
worktree. The script names its failure step/status, preserves partial data, and
prints completion only after all checks pass. The parent wrapper keeps an
interactive caller alive even if it has errexit enabled.

**Read-only state checks to propose before any retry:** first inspect
`ps -ww -C xorriso,cp,find,diff,cmp,du -o pid,ppid,etime,args`. If work is active,
do not interrupt it; inspect that PID's parent to identify the staging shell.
No xorriso result alone proves the batch is idle: it may have advanced to copying
or mode checks. Review the original terminal's prompt/output too.

Once no active operation is confirmed, use `sudo stat -c '%F %u:%g:%a %N' --`
against only the four approved paths, and a bounded
`sudo find -P /srv/perkforge-pxe-pilot/http/rhel-10.2 /srv/perkforge-pxe-pilot/tftp -mindepth 1 -maxdepth 1 -printf '%y %f\n'`
to report whether payload entries exist. Missing/denied paths are observations,
not permission for reset. Do not infer completion from presence alone; check
reported named status and verification evidence. Any nonempty or changed state
requires review, not a blind rerun into it. These checks are proposals, not run by
this preparation.

**Reference only:** the full heredoc below is retained for review/parity, not for
another long paste. Prefer the reviewed standalone file after the hold is cleared.

Before approving B, repeat the read-only ISO type/path inventory. Current evidence:
5,992 regular files and 18 directories including root; no symlink or special-file
nodes; no traversal, control-character or backslash names; no setid/sticky bits.
Reject any difference. `xorriso -find / -not -type d -not -type f -exec lsdl --`
should report no special objects. Do not use a tar/7z extraction or blindly assume
that xorriso's path handling makes an unreviewed image safe.

The private root from A must still be intact and empty except its three selected
directories. Keep its mode 0700 throughout extraction/normalization. The exact
source hash is rechecked before extraction; metadata and paths are from that same
verified ISO. No source ISO attribute is modified in memory or written back.

```sh
if BASH_ENV=/dev/null bash --noprofile --norc -s -- '/ABSOLUTE/PATH/TO/rhel-10.2-x86_64-dvd.iso' <<'PXE_BATCH_B'
set -Eeuo pipefail
step='startup'
trap 'rc=$?; printf "Batch B stopped at [%s] (status %s). Inspect partial state before retrying.\n" "$step" "$rc" >&2; exit "$rc"' ERR
step='explicit absolute ISO argument'
PXE_ISO=${1-}
[[ "$PXE_ISO" == /* ]]
BASE=/srv/perkforge-pxe-pilot
HTTP="$BASE/http/rhel-10.2"
TFTP="$BASE/tftp"
step='ISO regular file and no symlink'
test -f "$PXE_ISO"
test ! -L "$PXE_ISO"
step='ISO canonical path'
canonical_iso=$(readlink -e -- "$PXE_ISO")
test "$canonical_iso" = "$PXE_ISO"
step='ISO SHA-256 match'
printf '%s  %s\n' 'e15cb333529c332e76e4b1b946efe3515c99f996546675aec18e8effdf2540a5' "$PXE_ISO" | sha256sum --check --status
step='previously approved private staging directories'
for p in "$BASE" "$BASE/http" "$HTTP" "$TFTP"; do
    sudo test ! -L "$p"
    observed_metadata=$(sudo stat -c '%u:%g:%a' "$p")
    test "$observed_metadata" = '0:0:700'
done
step='HTTP/TFTP staging trees must be empty'
existing_entry=$(sudo find -P "$HTTP" "$TFTP" -mindepth 1 -print -quit)
test -z "$existing_entry"
step='WRITE SECTION: approved non-mount extraction'
sudo xorriso -no_rc -abort_on FAILURE -return_with SORRY 32 -hardlinks off -acl off -xattr off -follow off -overwrite off -indev "$PXE_ISO" -osirrox on:concat_split_off:auto_chmod_off -extract / "$HTTP"
step='reject unexpected extracted object types'
unexpected_entry=$(sudo find -P "$BASE" -xdev ! -type d ! -type f -print -quit)
test -z "$unexpected_entry"
sudo test -f "$HTTP/.treeinfo"
sudo test -f "$HTTP/images/install.img"
sudo test -d "$HTTP/BaseOS/repodata"
sudo test -d "$HTTP/AppStream/repodata"
step='WRITE SECTION: approved TFTP boot-file copies'
sudo cp -R --no-dereference --preserve=timestamps -- "$HTTP/EFI" "$TFTP/EFI"
sudo mkdir -m0700 "$TFTP/images"
sudo cp -R --no-dereference --preserve=timestamps -- "$HTTP/images/pxeboot" "$TFTP/images/pxeboot"
step='reject unexpected copied object types'
unexpected_entry=$(sudo find -P "$BASE" -xdev ! -type d ! -type f -print -quit)
test -z "$unexpected_entry"
step='compare copied boot assets'
sudo diff -r --no-dereference -- "$HTTP/EFI" "$TFTP/EFI"
sudo cmp -- "$HTTP/images/pxeboot/vmlinuz" "$TFTP/images/pxeboot/vmlinuz"
sudo cmp -- "$HTTP/images/pxeboot/initrd.img" "$TFTP/images/pxeboot/initrd.img"
step='WRITE SECTION: root ownership and read-only modes'
sudo find -P "$BASE" -xdev -exec chown 0:0 -- {} +
sudo find -P "$BASE" -xdev -type f -exec chmod 0444 -- {} +
sudo find -P "$BASE" -xdev -type d -exec chmod 0555 -- {} +
step='final ownership and non-writable modes'
unsafe_entry=$(sudo find -P "$BASE" -xdev \( ! -user root -o ! -group root -o -perm /222 \) -print -quit)
test -z "$unsafe_entry"
step='unprivileged service read-only access'
sudo -u dnsmasq test -r "$TFTP/EFI/BOOT/BOOTX64.EFI"
sudo -u dnsmasq test ! -w "$TFTP/EFI/BOOT/BOOTX64.EFI"
sudo -u www-data test -r "$HTTP/.treeinfo"
sudo -u www-data test ! -w "$HTTP/.treeinfo"
sudo du -B1 -s "$BASE"
PXE_BATCH_B
then
    printf '%s\n' 'Batch B completed. STOP and review; no next batch is authorized.'
else
    pxe_batch_status=$?
    printf 'Batch B failed (status %s). Caller remains open. Do not rerun or clean up automatically.\n' "$pxe_batch_status" >&2
fi
```

The last two mode passes remove write/execute/setid permissions from regular
files and make directories traversable but non-writable to both service users.
Archive ACL/xattr restoration and hard-link restoration are disabled; native
inherited ACLs must not grant service write access. The final permission checks
are required. No files are executed; EFI files need read permission for network
transfer, not host execute permission. No shared group is created or used.

Expected payload is about 11.29 GB before filesystem overhead, within the proposed
16 GiB budget. HTTP contains the full tree including hidden metadata. TFTP adds
only the complete `/EFI` tree (5 files) and `/images/pxeboot` (2 files), about
247.4 MB. There is no overwrite of a preexisting serving tree, path traversal,
symlink following, mount/loop device or output outside this newly created root.
Root-trusted concurrent changes still require reinspection, not blind retries.

After B, stop. The copied DVD GRUB menu remains stock, with local-media label and
auto-timeout; it must not be served unchanged. Signature/dbx/SBAT acceptance,
network GRUB-prefix lookup, reviewed pilot menu placement, service/runtime/log
setup, nginx installation/native checks, nft checks/apply and any launch or node
boot remain separate approval gates. Staging alone is not a successful install.
