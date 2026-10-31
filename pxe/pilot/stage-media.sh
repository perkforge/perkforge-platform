#!/usr/bin/env bash
# Reviewed Batch B only. Do not source this file.
# Execution status from the previous paste is UNKNOWN: resolve native state first.
# No automatic retry/resume/cleanup, and no service, firewall, mount or node action.
# BEGIN REVIEWED BATCH B BODY
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
# END REVIEWED BATCH B BODY
printf '%s\n' 'Batch B completed. STOP and review; no next batch is authorized.'
