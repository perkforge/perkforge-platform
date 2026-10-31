# Physical-cluster execution journal

Chronological, manually sanitized commands and safe output for
[issue #13](https://github.com/perkforge/perkforge-platform/issues/13).
This is a reviewed narrative, not raw operational evidence or shell-wide logging.
Keep raw sensitive evidence private/ignored as required by the
[evidence guidance](../evidence/README.md). Follow the
[staged preparation](PREPARATION.md); a log entry is not approval for the next step.

## Recording rules

Append actual executions in UTC order, with purpose, approval scope, command,
safe output/status, interpretation and next decision. Identify user reports,
source lookups and assumptions separately from executed verification. If the
execution time was not captured, say so; never invent a timestamp or successful
output. Preserve corrections as dated annotations rather than rewriting history.

`$REPO_ROOT` below is a **path placeholder** for the operator's repository checkout;
it is not a recorded assignment or a command to execute now. Original workstation
absolute paths have been normalized to this placeholder in both commands and
output. Any other redaction must use an explicit `<REDACTED: description>` label.
Never include secrets, private host addresses/MACs, usernames, credentials in URLs,
kubeconfig/Secret bodies, passwords, private keys or recovery shares. Review output
before adding it; do not enable `set -x`, terminal recording or shell-wide capture.

## Context carried forward (not new execution)

- **User report:** all physical nodes are off. No node connection, scan or power
  state verification was performed; this journal does not establish current state.
- **Media source:** the parent conversation's official Red Hat download-page review
  identified RHEL **10.2** as the latest listed release and supplied the expected
  x86_64 DVD checksum from
  [Red Hat downloads](https://developers.redhat.com/products/rhel/download).
  This is attributed source context, not a new release lookup by this journal step.
- **Local read-only lookup:** filename `images/rhel-10.2-x86_64-dvd.iso` suggests
  RHEL 10.2/x86_64/DVD media; filename inference alone did not establish contents.
  A prior `cat "$REPO_ROOT/infrastructure/ansible/group_vars/rke2.yml"` lookup
  recorded `rke2_version: v1.36.5+rke2r1`. Its execution timestamp was not captured.
  That is a repository pin, not a detected installation or compatibility result.

## 2026-10-30 20:07:10–20:07:21 UTC — Verify local installation media

**Purpose:** compare the existing ISO with the expected SHA-256 supplied from the
Red Hat listing before deciding whether to proceed with installation planning.

**Approval scope:** the user explicitly approved calculation/comparison of the
ISO checksum as a read-only step. It did not authorize mounting, downloading,
replacement, node access, boot/network changes, disk writes or provisioning.

**Command:** executed against the workstation's absolute checkout path; normalized
here to `$REPO_ROOT`. The two `date` calls and `stat` were executed with the hash
command to capture time and size; no shell variable assignment was recorded.

```sh
date -u '+Started: %Y-%m-%dT%H:%M:%SZ'
stat -c 'Size: %s bytes' "$REPO_ROOT/images/rhel-10.2-x86_64-dvd.iso"
sha256sum "$REPO_ROOT/images/rhel-10.2-x86_64-dvd.iso"
date -u '+Completed: %Y-%m-%dT%H:%M:%SZ'
```

**Safe output:** path normalized; otherwise the recorded output is retained.

```text
Started: 2026-10-30T20:07:10Z
Size: 11059986432 bytes
e15cb333529c332e76e4b1b946efe3515c99f996546675aec18e8effdf2540a5  $REPO_ROOT/images/rhel-10.2-x86_64-dvd.iso
Completed: 2026-10-30T20:07:21Z
```

**Expected SHA-256:**
`e15cb333529c332e76e4b1b946efe3515c99f996546675aec18e8effdf2540a5`.
Source: the official Red Hat download listing cited above, supplied in the parent
conversation. **Result: match.** Size: **11,059,986,432 bytes**. The execution tool
reported exit status **0** for the command batch; this status is tool metadata,
not an extra line emitted by `sha256sum`. No error was reported for the hash read.

**Provenance:** actual `sha256sum`, `stat` and UTC time output from the approved
read-only tool execution in this conversation, transcribed after completion.
The expected value came from the parent conversation's official-source lookup;
this journal creation did not rerun the hash or access the ISO again.

**Interpretation/limits:** the ISO bytes match the supplied published-media hash.
This does not establish Lenovo hardware/UEFI compatibility, RHEL entitlement,
PXE readiness, or support of RHEL 10.2 by the pinned RKE2/Rancher/Big Bang stack.
No media was mounted, downloaded or changed; no node was contacted and no
provisioning step advanced.

**Next decision:** review the selected RHEL 10.2 media against hardware and pinned
platform support requirements together; agree the next bounded step before any
new execution. No boot, disk or network action is authorized by this result.

## After media verification — Proton storage decision (time not captured)

**Purpose/provenance:** record the user's subsequent planning decision:
“I am going to use Proton's tools (pass and drive) for credential backup.”
The decision's exact timestamp was not captured; its position here records the
conversation order, not an invented execution time.

**Decision:** Proton Pass and Proton Drive are selected. Proposed division:
**Pass for credential custody; Drive for encrypted backup files**. Exact contents,
encryption/key custody, access policy, retention and restore workflow still need
review. No command or safe execution output exists for this decision entry.

**Approval scope/status:** planning and local journal documentation only. Proton
was not accessed; nothing was exported/uploaded, no keys or secrets were generated
or stored, and no backup was configured or tested.

**Interpretation/limits:** using Pass and Drive may create a shared Proton-account
recovery dependency. Independent offline recovery confirmation is pending;
selection does not establish recovery after losing the workstation, cluster or
account access. The separate subscription confirmation question remains pending;
this credential-storage decision does not answer it.

**Next decision:** confirm independent offline recovery and review the exact
custody/encryption/backup/restore process before any account access or credential
operation. Resolve the separate subscription question independently.

## After storage decision — Subscription portal confirmation (time not captured)

**Purpose/provenance:** record the user's verification in the Red Hat portal UI.
The user reported the end date as `10/21/2027` and confirmed the subscription was
active when asked about its status or the Active filter. The exact observation
time was not captured; this entry follows the conversation order.

**User-reported result:** **Red Hat Developer Subscription for Individuals
(RH00798)**, **active**, ending **October 21, 2027**. This resolves the subscription
confirmation left pending in the preceding entry, based on the user's portal
observation. No account identifiers, credentials or reset links are recorded.

**Approval scope/status:** local journal documentation only. No command was run
against Red Hat, no agent API/account inspection occurred, and no machine was
registered. There is no command output or execution exit status for this report.

**Interpretation/limits:** subscription status is user-reported portal evidence,
not proof of node registration, repository access or hardware/platform support.
It does not configure the Proton custody/backup plan or establish offline recovery.

**Next decision:** agree the next bounded preparation step separately; machine
registration and other live changes require their own approval.

## After subscription confirmation — Windows preservation preference (time not captured)

**Purpose/provenance:** when asked whether anything on the existing Windows
installations needed preserving, including files or a way to restore Windows
later, the user answered “nothing.” The exact response time was not captured;
this entry records conversation order.

**Decision/status:** the user has no Windows preservation requirement. This is a
preservation preference, **not approval to wipe an unidentified disk**. No command
was run and no disk, partition, boot setting or Windows installation was changed.

**Next decision:** before any destructive step, identify the exact node and target
disk and obtain explicit data-loss confirmation. This entry does not authorize
installation, formatting, repartitioning or any other destructive action.

## After preservation decision — Offline recovery report (time not captured)

**User-reported status:** operator reports an independent offline recovery copy
is secured; contents/location were not collected; recovery has not been tested.
The response time was not captured; this entry records conversation order. This
updates the earlier pending offline-copy confirmation, not restore verification.

**Scope/limits:** local documentation only; no secret, account detail or recovery
material was requested, accessed or recorded. No recovery or backup operation was
performed by the agent.

**Next decision:** USB encryption compatibility remains pending. A 128 GB SanDisk
is a candidate only; the device has not been identified or formatted. Agree the
compatibility choice and verify the exact device before any separately approved
storage operation.

## 2026-10-30 20:33:11 UTC — Read-only USB identification

**Purpose/approval:** the user approved a read-only listing of the attached
128 GB SanDisk to review model, capacity, serial and mount status. This did not
authorize mounting, unmounting, formatting, encryption or credential operations.
Linux-only use is the stated requirement; **LUKS2 + ext4 is proposed, not executed**.

**Commands:** the first batch was executed as shown below. Its start and completion
both reported `2026-10-30T20:33:11Z`.

```sh
date -u '+Started: %Y-%m-%dT%H:%M:%SZ'
lsblk --bytes --paths --output NAME,MODEL,SIZE,SERIAL,TRAN,RM,TYPE,FSTYPE,MOUNTPOINTS
ls -l /dev/disk/by-id/
date -u '+Completed: %Y-%m-%dT%H:%M:%SZ'
```

Follow-up reads inspected sysfs vendor/model, device-path visibility and filtered
udev link metadata. The following paths are normalized placeholders, **not actual
assignments**: `<USB_SYSFS>` is the candidate's sysfs block directory;
`<USB_DEVICE>`, `<USB_PARTITION_1>` and `<USB_PARTITION_2>` are its kernel paths;
`<UDEV_RECORD>` is its udev device-metadata record. Exact follow-up timestamps were
not captured. No filesystem contents were inspected.

```sh
cat <USB_SYSFS>/device/vendor <USB_SYSFS>/device/model
ls -ld <USB_DEVICE> <USB_PARTITION_1> <USB_PARTITION_2> /dev/disk <UDEV_RECORD>
rg '^(S:|E:(DEVLINKS|ID_BUS|ID_VENDOR|ID_MODEL|ID_SERIAL|ID_SERIAL_SHORT)=)' <UDEV_RECORD>
```

**Safe output summary:** manually sanitized from the actual listing/metadata;
kernel paths, serials, topology and unrelated internal-disk identifiers are omitted
or normalized. “None listed” is the listing result, not a global mount guarantee.

| Item | Observed safe metadata |
|---|---|
| `<USB_DEVICE>` | SanDisk Extreme Pro; USB; removable; disk; 128,043,712,512 bytes; no filesystem or mountpoint listed on whole device |
| `<USB_PARTITION_1>` | 128,009,109,504 bytes; exFAT; no mountpoint listed |
| `<USB_PARTITION_2>` | 33,554,432 bytes; VFAT; no mountpoint listed |
| `<INTERNAL_NVME>` | Separate nonremovable NVMe disk; 1,024,209,543,168 bytes; partitions supply `/boot/efi`, `/boot` and a LUKS container |
| Udev identity | USB/SanDisk/Extreme Pro; serial `<REDACTED: hardware serial>` |
| Udev by-id record | `/dev/disk/by-id/usb-SanDisk_Extreme_Pro_<REDACTED: hardware serial>-0:0` |
| Device visibility | `/dev/disk/by-id/`, `/dev/disk` and candidate device nodes are absent in this execution environment; udev metadata record is readable |

**Status/provenance:** actual read-only `lsblk`, sysfs and udev metadata. The first
command batch returned exit 0, but its `ls` explicitly reported the missing by-id
directory; the final `date` must not be mistaken for successful link verification.
The follow-up device-path listing batch returned exit 2 for missing paths; filtered
udev metadata returned exit 0. No live by-id symlink could be resolved here.

**Interpretation/limits:** the SanDisk identity/capacity matches the user-described
candidate. Its existing partition/filesystem metadata is visible; contents were
not read. The internal NVMe is a different disk and must not be selected. Root's
backing mapping was not established by this listing; only the boot mounts and
LUKS-container metadata above are visible. Udev's registered by-id name is evidence
of identity, not proof that its symlink/device node is presently accessible or that
no other host/process has mounted the device.

**Next decision:** review the exact candidate identity together and resolve native
host device/by-id visibility and mount ownership before any future operation.
Recheck identity at action time; kernel device names can change. LUKS2/ext4,
erasure of existing USB data and the exact device still require separate approval.
No mount, unmount, format, wipe, install or provisioning step was performed.

## 2026-10-30 20:36 UTC — Operator approval and native-host preparation

**Purpose/provenance:** the user approved erasing the identified 128 GB SanDisk
Extreme Pro and preparing it with LUKS2 + ext4. The selected kernel device and
serial were confirmed in the conversation; they are normalized here as
`<USB_DEVICE>` and `<REDACTED: USB serial>`. `<USB_BY_ID>` means the exact stable
USB identifier reviewed with the operator, not an arbitrary device or an actual
shell assignment.

**User-performed checks:** user-supplied `readlink` output confirmed that
`<USB_BY_ID>` resolves to `<USB_DEVICE>` on the native workstation. This addresses
the earlier environment-visibility limitation by operator evidence, not a new
agent device check. Exact invocation/time were not retained in this handoff.
Shell `command -v` lookups produced no output; user-supplied `dpkg-query` results
confirmed `cryptsetup`, `cryptsetup-bin`, `parted` and `e2fsprogs` were installed.
An empty PATH lookup was not treated as proof that packages were absent. No package
installation was reported in this step. Exact lookup invocations/exit codes were
not supplied for transcription.

**Approval limits:** this records approval for the specifically identified USB,
not the internal disk, physical nodes or other storage. Disk operations below were
performed by the user; this journal update executed no disk command and grants no
additional agent authority. Passphrases must be entered privately, never logged.

## 2026-10-30 20:42 UTC — User-performed GPT partitioning and verification

**Purpose:** create the reviewed single backup partition on the approved USB.
The supplied output time is recorded here; exact command start/finish times and
exit statuses were not provided.

**Commands supplied for the user-performed step:** stable hardware ID normalized
to the labeled `<USB_BY_ID>` placeholder.

```sh
sudo /usr/sbin/parted --script <USB_BY_ID> mklabel gpt mkpart perkforge-backup 1MiB 100%
sudo /usr/sbin/parted <USB_BY_ID> unit MiB print
```

**Safe output summary:** transcribed values from the user-supplied verification,
not a reconstructed verbatim terminal transcript.

| Field | User-supplied result |
|---|---|
| Partition table | GPT |
| Partition | 1 |
| Name | `perkforge-backup` |
| Start | 1 MiB |
| End | 122111 MiB |
| Size | 122110 MiB |

**Interpretation/status:** the supplied partitioning result supports successful
creation of the GPT partition. Initial `lsblk` output still showed residual exFAT
metadata; this was **not treated as encryption** or as proof of a clean filesystem.
No exit code is inferred from the displayed table. This step alone does not
establish LUKS formatting, ext4, mounting, backup contents or recovery.

**Next decision at that point:** proceed only with the separately reviewed LUKS2
operation on partition 1 of that same USB; keep the passphrase private.

## 2026-10-30 20:44:19 UTC — User reports LUKS2 formatting completed

**Command provided before the user's completion report:**

```sh
sudo /usr/sbin/cryptsetup luksFormat --type luks2 --verify-passphrase <USB_BY_ID>-part1
```

**Safe reported outcome/provenance:** the user replied “completed.” The timestamp
is the completion **report** time, not a captured command start/finish interval.
No passphrase was collected. No command output or exit status was supplied, and
the agent has not independently verified the resulting LUKS header or unlock.

**Interpretation/limits:** record LUKS2 format completion as a **user report**,
not agent-verified encryption or a successful backup/restore test. The prior
partition output and residual exFAT observation remain historical observations;
no new filesystem state is inferred from them after this command.

**Pending:** an unlock command and `lsblk` verification have been provided to the
user, but their outcome is not yet reported. No ext4 creation, mount, backup or
restore has been performed/reported in this sequence. Review the unlock/listing
result before advancing. This journal update performs no storage operation.

## 2026-10-30 20:45:35 UTC — User-supplied unlocked LUKS mapping

**Command supplied for the user-performed step:** stable USB identity remains
normalized to `<USB_BY_ID>`.

```sh
sudo /usr/sbin/cryptsetup open <USB_BY_ID>-part1 perkforge_backup
```

**Safe output summary:** the user's `lsblk` result at 20:45:35 UTC showed this
hierarchy; kernel USB paths are normalized. Exact verification invocation and
individual command exit codes were not supplied.

```text
<USB_DEVICE>          119.3G  disk
└─<USB_PARTITION_1>    119.2G  part   crypto_LUKS
  └─perkforge_backup  119.2G  crypt
MOUNTPOINTS: blank for the displayed tree
```

**Interpretation/provenance:** user-supplied listing supports that partition 1 is
a LUKS container with an open `perkforge_backup` mapping. No mountpoint is listed.
The display sizes are retained as supplied, not substituted for the earlier
byte counts. No passphrase or agent verification was collected/performed.

## 2026-10-30 20:47:24 UTC — User-supplied ext4 formatting result

**User-performed command:**

```sh
sudo /usr/sbin/mkfs.ext4 -L perkforge-backup /dev/mapper/perkforge_backup
```

**Safe output summary:** user-supplied `lsblk` at 20:47:24 UTC showed the same
hierarchy with ext4 on the unlocked mapping and blank mountpoints.

```text
<USB_DEVICE>          119.3G  disk
└─<USB_PARTITION_1>    119.2G  part   crypto_LUKS
  └─perkforge_backup  119.2G  crypt  ext4
MOUNTPOINTS: blank for the displayed tree
```

**Status/provenance:** user execution and user-supplied verification output;
`mkfs` logs, individual exit code and command start/finish interval were not
provided. The timestamp is for the supplied listing. No result is fabricated.

**Interpretation/limits:** reported state is formatted encrypted ext4 on the open
LUKS mapping, unmounted in the supplied listing. This establishes neither a usable
backup nor successful recovery. No real backups or credentials have been stored
in this sequence, and the agent executed no system command for these updates.

**Next decision:** a dummy write → unmount/close → reopen/mount → read comparison
test is proposed, **pending user approval**. No such test has yet been performed;
do not advance to real credential backups on the basis of formatting alone.

## 2026-10-30 20:47:47 UTC — Dummy USB read-back test approved

**Purpose/approval:** the user approved a dummy-only write, close, reopen and read
comparison on the already identified USB. No real credentials or backups were
part of this test. Commands below were supplied to and performed by the user;
this journal update executed no disk command. No individual exit codes were
provided, so none are inferred.

## 2026-10-30 20:48:44 UTC — User-supplied writable mount verification

**Commands supplied:**

```sh
sudo mkdir -p /mnt/perkforge-backup
sudo mount -o nodev,nosuid,noexec /dev/mapper/perkforge_backup /mnt/perkforge-backup
```

**Safe output summary/provenance:** the user's `findmnt` result at 20:48:44 UTC
reported `/dev/mapper/perkforge_backup` mounted at `/mnt/perkforge-backup`, ext4,
with `rw,nosuid,nodev,noexec,relatime`. This is a summary of the supplied mount
metadata, not reconstructed output or a separately captured command exit status.

## 2026-10-30 20:49:42 UTC — Dummy file baseline checksum

**Dummy write command supplied:**

```sh
printf '%s\n' 'PerkForge backup recovery test — no secrets' | sudo tee /mnt/perkforge-backup/recovery-test.txt
```

**User-supplied checksum result:**

```text
edf795427e284f96f9addbaa7d3932d11aec9a055d1ac1711be63b28b01ed941
```

The timestamp belongs to the user's hash report; an individual write/hash exit
status and exact baseline hash invocation were not supplied. The file contains
only the stated dummy text, not backup material or secrets.

## 2026-10-30 20:50:46 UTC — User-supplied first close verification

**Commands supplied:**

```sh
sync
sudo umount /mnt/perkforge-backup
sudo /usr/sbin/cryptsetup close perkforge_backup
```

**Safe output summary:** the user's `lsblk` at 20:50:46 UTC showed only
`<USB_DEVICE>` → `<USB_PARTITION_1>` with `crypto_LUKS`, no mapper child and no
mountpoint. These normalized placeholders preserve hardware-ID privacy. This
supports a closed mapping at that checkpoint; exact listing invocation and
individual exit codes were not supplied.

## 2026-10-30 20:52:00 UTC — User-supplied read-only reopen checksum

**Commands supplied:**

```sh
sudo /usr/sbin/cryptsetup open --readonly <USB_BY_ID>-part1 perkforge_backup
sudo mount -o ro,nodev,nosuid,noexec /dev/mapper/perkforge_backup /mnt/perkforge-backup
sha256sum /mnt/perkforge-backup/recovery-test.txt
```

`<USB_BY_ID>` is the previously reviewed stable hardware identifier, normalized
here; it is not an executable placeholder or a recorded shell assignment.

**User-supplied checksum result:**

```text
edf795427e284f96f9addbaa7d3932d11aec9a055d1ac1711be63b28b01ed941
```

**Result/provenance:** **basic close/reopen dummy read-back PASSED**, based on the
user's evidence: the baseline and reopened-file hashes match exactly. The
read-only open/mount commands are recorded as supplied; no independent agent
inspection or individual command exit status was provided. Timestamp is the
user's read-back report, not an inferred command interval.

**Limits:** this is not a restore on another workstation, a complete backup-system
test, or proof of recovery after account/device loss. Real backups and credentials
remain absent from this test. No passphrase was collected.

**Pending:** final unmount, close and listing/check commands have been supplied,
but their outcome is not yet reported. Do not assume the USB is now closed or safe
to remove merely because the earlier close/reopen cycle passed. Await the final
user verification before recording final device state.

## 2026-10-30 20:52:49 UTC — Final dummy-test cleanup confirmed by user output

**Safe output summary/provenance:** the user's final `lsblk` showed
`<USB_DEVICE>` (119.3G, disk) → `<USB_PARTITION_1>` (119.2G, partition,
`crypto_LUKS`), with **no mapper child and no mountpoints**. Kernel device paths
remain normalized; the output is attributed to the user, not agent inspection.
The timestamp is for the supplied listing; no individual cleanup exit codes or
exact listing invocation were provided.

**Result:** final cleanup is **user-output-confirmed locked/unmounted at this
checkpoint**. This resolves the pending cleanup status in the preceding entry.
The dummy close/reopen read-back result remains passed within its stated limits;
no real secrets or backups were stored by this test.

**Next decision/pending:** independent custody of the USB passphrase still needs
confirmation. Do not collect the passphrase or record its contents/location here.
No actual credential backup, cross-workstation restore or new storage operation
is authorized or claimed by this journal entry.

## After final cleanup — USB passphrase custody confirmed (time not captured)

**Provenance/status:** the user confirmed that the USB encryption passphrase is
recoverable independently of both the USB and Proton. Contents/location were not
collected. This is a user report, separate from the earlier Proton recovery-copy
confirmation, and resolves the preceding pending USB-passphrase custody question.
The exact response time was not captured; position records conversation order.

**Limits:** recovery on another machine remains untested. No secret, passphrase,
account access or real backup operation occurred in this journal update.

**Next decision:** a personal dedicated SSH key name is proposed for review;
**key generation is not authorized yet**. Agree the naming and bounded next step
before any credential creation or authentication change.

## After custody confirmation — Local non-FIPS and personal SSH naming decisions

**User decision/provenance:** the operator explicitly selected a **non-FIPS
installation** for the local security/learning cluster. The parent conversation
explained RHEL 10's install-time FIPS requirement; this entry records the decision,
not a new FIPS evaluation, host-state inspection or configuration change. The
exact decision time was not captured. Other security controls remain in scope;
no compliance or authorization claim follows from this choice.

**Personal key naming:** the user approved a dedicated personal administrator key,
separate from automation. Its approved base name is normalized in this public
journal as `perkforge-local-<REDACTED: operator>-admin`; the actual operator-specific
name remains in the private conversation. This redaction is intentional and does
not mean another key name was chosen.

## 2026-10-30 20:55 UTC — User-supplied SSH-directory/name availability check

**Safe output summary/provenance:** the user's directory listing reported their
SSH directory as `drwx------`, owned by `<REDACTED: operator>`. Both the approved
personal private-key path and its `.pub` companion were absent. Exact listing
invocation, individual exit status and start/finish interval were not supplied;
the timestamp reflects the supplied observation. No directory or key path was
inspected by the agent for this journal update.

**Interpretation/next decision:** passphrase-protected Ed25519 generation is
proposed for the dedicated personal key. The user's explicit generation answer
is **pending**. No key generation, installation, node access or authentication
change is authorized or performed by this entry. Private directory permissions
and absent filenames alone do not approve credential creation.

## 2026-10-30 21:01:28 UTC — Personal SSH key generation approved

**Approval/provenance:** the user approved generation of the dedicated personal
administrator key. This resolves the preceding generation-approval question;
it does not authorize installation on a node or a remote login.

**User-performed command supplied:** operator-specific name and home path are
normalized as `<PERSONAL_KEY_NAME>` and `<PRIVATE_KEY>`. The actual command used
`-a 100` as separate arguments, retained here.

```sh
ssh-keygen -t ed25519 -a 100 -f "<PRIVATE_KEY>" -C "<PERSONAL_KEY_NAME>"
```

`<PRIVATE_KEY>` represents the approved personal key in the operator's SSH
directory; `<PUBLIC_KEY>` represents its `.pub` companion. These are redacted
references, not literal command arguments or recorded shell assignments.

## 2026-10-30 21:02:38 UTC — User reports key generation completed

**Reported outcome:** user completion report; no private-key contents or
passphrase were collected. The report timestamp is not an inferred command
start/finish interval, and no individual exit status was provided.

## 2026-10-30 21:03:37 UTC — User-supplied key metadata verification

**Safe listing/fingerprint summary:** private key mode **0600**, size **464 bytes**;
public companion mode **0644**, size **109 bytes**; both owned by
`<REDACTED: operator>`. A user-supplied `ssh-keygen -lf <PUBLIC_KEY>` result
identified **256-bit ED25519**. The public fingerprint is represented consistently
here as `<REDACTED: personal SSH public fingerprint>` to avoid publishing the
operator's credential identity. Sizes and permissions are metadata, not key bytes.

**Limits:** these are supplied user observations; exact listing invocation,
individual exit codes and generation output were not provided. No node has
received the key and no remote-login test is claimed.

## 2026-10-30 21:06:19 UTC — User confirms private-key passphrase unlock

**Command supplied:**

```sh
ssh-keygen -y -f "<PRIVATE_KEY>" > /dev/null
```

**Provenance/result:** the user confirmed the prompted unlock. Public-key output
was directed to `/dev/null`; no private bytes, passphrase or execution exit code
were collected. This supports decryptability of the workstation key as reported,
not access to any cluster node.

## 2026-10-30 21:07:00 UTC — Encrypted USB key-copy approval

**Approval scope:** the user explicitly approved copying this personal key pair
to the encrypted USB. This is a separate approval from generation; it does not
approve Proton upload, other credentials or node installation. The following
commands/results are user-performed evidence, not agent storage actions.

## 2026-10-30 21:08:11 UTC — User-supplied backup mount verification

**Safe output summary:** user `findmnt` showed the mapper mounted at
`/mnt/perkforge-backup`, ext4, with `rw,nosuid,nodev,noexec,relatime`. This is the
user's mount observation, not agent inspection or a fabricated raw transcript.
No individual command exit code was supplied.

## 2026-10-30 21:08:53 UTC — User confirms private backup directory and no collision

**Commands/checks supplied:**

```sh
sudo install -d -m0700 -o $(id -u) -g $(id -g) /mnt/perkforge-backup/ssh
```

A target-absence listing was also supplied for review; its exact invocation is
not retained here. The user confirmed the expected results: directory creation
and no preexisting target files. Exact listing output and individual exit codes
were not supplied, so they are not reconstructed.

## 2026-10-30 21:09:46 UTC — User verifies copied key pair

**Copy command pattern supplied:** private and public files were copied separately
with preservation and interactive overwrite protection, then listed. USB paths
are normalized as `<USB_PRIVATE_KEY>` and `<USB_PUBLIC_KEY>` inside the reviewed
backup directory.

```sh
cp -p -i "<PRIVATE_KEY>" "<USB_PRIVATE_KEY>"
cp -p -i "<PUBLIC_KEY>" "<USB_PUBLIC_KEY>"
```

**Safe reported outcome:** the user replied “verified” after the copy/listing.
No exact listing or individual exit code is invented. No key contents were
collected by the agent.

## 2026-10-30 21:10:50 UTC — User-supplied backup-key identity/decryptability check

**Command supplied:**

```sh
ssh-keygen -y -f "<USB_PRIVATE_KEY>" | ssh-keygen -lf -
```

**Safe result/provenance:** the user's resulting public fingerprint matched the
workstation public-key fingerprint **exactly**. Both are represented in this
public journal as `<REDACTED: personal SSH public fingerprint>`; no private-key
contents or passphrase were collected. This user-supplied result supports backup
private-key decryptability and matching public identity. Individual pipeline exit
codes were not provided, and are not inferred.

**Interpretation/limits:** the encrypted USB now contains the copied personal key
pair according to user evidence, with a successful same-workstation unlock/identity
check. This is **not** a full independent-machine restore, a Proton copy, node-key
installation or remote-login verification. Earlier dummy-test entries that stated
no real credentials were present describe their earlier checkpoints only.

**Pending:** sync, unmount, mapper-close and final listing/check commands have
been supplied; their cleanup outcome is not yet reported. Do not assume the
current mapper is closed or the USB safe to remove. No disk command or private-key
read was executed by the agent for this journal update.

## 2026-10-30 21:11:41 UTC — User confirms cleanup after SSH-key backup

**Safe output summary/provenance:** the user's final `lsblk` showed
`<USB_DEVICE>` (119.3G, disk) → `<USB_PARTITION_1>` (119.2G, partition,
`crypto_LUKS`), with no mapper child and no mountpoints. Hardware paths remain
normalized. No exact listing invocation or individual cleanup exit codes were
supplied; this is user-output evidence, not agent device inspection.

**Result:** **locked/unmounted at this checkpoint**, resolving the preceding
post-backup cleanup status. Safe unplug was advised; physical unplug has **not**
been confirmed. The copied key's same-workstation decryptability/identity result
stands within its stated limits; no independent-machine or Proton restore is
claimed.

**Next decision/pending:** confirm separate recoverable custody of the **SSH-key
passphrase**, distinct from the USB encryption passphrase and Proton recovery
material. Do not collect its contents or location. No disk operation, private-key
read, node installation or publication occurred in this journal update.

## 2026-10-30 21:12:17 UTC — SSH-key passphrase custody confirmed by user

**User-reported status/provenance:** the user confirmed that the SSH-key
passphrase is recoverably stored separately from the USB. Contents/location were
not collected. This resolves the preceding SSH-key-passphrase custody question;
it is distinct from the earlier USB encryption passphrase and Proton recovery
confirmations. It does not establish a successful independent-machine restore.

**Scope/next decision:** no new credential action occurred. The proposed
operator-specific node login is normalized here as `<REDACTED: proposed node
login>`; node-login choice and sudo authentication are being discussed and remain
**undecided**. No account creation, password/key installation, sudo-policy change,
node access or publication is authorized or performed by this entry.

## 2026-10-30 21:13:06 UTC — Personal node-login design selected

**User decision/provenance:** the operator selected the same personal account on
all three physical nodes for personal SSH-key login and sudo. Its approved name
is normalized in this public journal as `<REDACTED: personal node login>`. This
resolves the preceding login-choice question; it does not record account creation
or establish that the account currently exists on any node.

## 2026-10-30 21:13:36 UTC — Password-authenticated sudo design approved

**User decision:** use **password-authenticated sudo**, with a local account
password separate from the SSH-key passphrase. Intended SSH authentication is
public key, with **SSH password login disabled**. These are selected design
settings, not verified current host configuration.

**Scope/limits:** the local account password is to be entered privately during
installation. No password was collected or generated, and no account, inventory,
SSH configuration or sudo policy was changed. No node was accessed. Existing
passphrase/recovery custody entries refer to their separate credential classes.

**Next decision/pending:** confirm the PXE network topology before any network
service/configuration or installation step. The selected login/sudo design does
not itself authorize such actions or implementation of these security settings.

## After login/sudo design — PXE review and local source cleanup (times not captured)

**User-reported package metadata:** `dnsmasq` and `dnsmasq-base` each reported
version `2.91-1+deb13u2`, status `install ok installed`. Exact report time was not
captured. Installed packages do not establish running services or listener state;
those checks remain pending. Nodes remain off according to the operator report.

**Approval/purpose:** the user authorized deleting obsolete PXE repository
resources. Tracked-file/reference inspection identified the RHEL 9 partial
Kickstart and iPXE example as the obsolete resources; useful guidance is retained.
This is **local source cleanup**, not media deletion or a live PXE operation.

**Actual deletion command excerpt:** executed in the feature worktree, not main;
the rest of the source-edit batch rewrote documentation only.

```sh
python3 - <<'PYTHON'
from pathlib import Path
for name in ['pxe/boot.ipxe.example', 'pxe/kickstarts/rhel.ks.j2']:
    Path(name).unlink()
PYTHON
```

The here-document delimiter/whitespace above is normalized for presentation;
the two actual deleted paths and deletion operation are unchanged.

**Safe result:** removed only `pxe/boot.ipxe.example` and
`pxe/kickstarts/rhel.ks.j2`. Updated `pxe/README.md`,
`infrastructure/PREPARATION.md` and `infrastructure/README.md` to describe the
selected **RHEL 10.2 x86_64, interactive, non-FIPS physical pilot**, explicitly
not implemented as a runnable configuration. The source-edit command batch
completed with exit 0. No tracked test referenced the two deleted examples, and
no test was removed. Existing infrastructure evidence tests remain unchanged.

**Limits/next decision:** preserve the separate worktree's earlier journal edits,
private inventories, ISO/QCOW2/downloads, user files, historical evidence and all
host configuration. No services were installed/started, no sockets/firewall/network
settings changed, and no node or credential was accessed. Service/listener
verification and a side-by-side review remain prerequisites to any separately
approved pilot setup. Repository validation is recorded below after execution.

## During source cleanup — User-supplied service snapshot (time not captured)

**Command/result provenance:** the user reported `systemctl is-active dnsmasq`
returned `active`. Supplied `ss` output showed two dnsmasq process IDs: one with
TCP/UDP DNS listeners on IPv4/IPv6 loopback port 53; another with DNS on
`<REDACTED: existing virtual-bridge address>` port 53 and UDP port 67 associated
with `<REDACTED: existing virtual bridge>`. Process identifiers and private
addresses/topology are normalized rather than copying the raw socket listing.
The exact `ss` invocation, observation time and individual exit codes were not
supplied here.

**Observed limits:** no listeners on ports 69, 4011, 80 or 8080 were listed in the
supplied snapshot. This is not a guarantee of port availability or production
safety, and does not prove that DHCP behavior or interface isolation is safe.
Instance ownership/launch arguments remain unconfirmed. Both existing instances
must remain untouched; neither is assumed to be the future pilot service.

**Next read-only review requested in the parent conversation:**

```sh
ps -ww -C dnsmasq -o pid,ppid,args
```

Its result is pending. This journal update did not run that command, inspect a
service or start/restart/reconfigure any instance. No network change was made.

## After source cleanup — Offline repository validation (time not captured)

**Commands executed in the feature worktree:**

```sh
python3 -m unittest discover -s infrastructure/ansible/tests -v
git diff --check
```

**Safe test output excerpt:**

```text
Ran 18 tests in 47.359s

OK
```

**Status/provenance:** infrastructure test process returned exit 0;
`git diff --check` returned exit 0 with no whitespace errors. Local documentation
checks also passed relative-link existence, code-fence balance, removal of the
two precise obsolete examples and absence of stale runnable references. Exact
validation start/finish times were not captured. Existing infrastructure tests
and the PXE CI path trigger have no source changes; no tests were deleted.

**Limits:** these are offline source checks using existing synthetic fixtures,
not physical boot, installed-service, DHCP targeting, Secure Boot or RHEL 10.2
installation validation. Nothing was committed/pushed; earlier journal edits and
unrelated user media/configuration remain preserved. Stop at source cleanup.

## After source validation — User-supplied dnsmasq instance ownership (time not captured)

**Provenance:** the user supplied the requested process listing. It identifies a
system dnsmasq instance using its system PID file, service user, system
configuration-directory includes, local-service setting and trust anchors. A
second instance and its child use libvirt's default-network configuration,
read-only lease-file handling and libvirt lease helper. Exact process identifiers
are omitted here; no private network addresses or raw unrelated process data are
copied. The observation timestamp was not captured.

**Interpretation/limits:** this resolves launch-argument/ownership uncertainty for
the supplied snapshot, not firewall readiness or safe pilot coexistence. Both
instances remain untouched. A future pilot needs **separate configuration and PID
state outside the system include path**, plus the reviewed interface restriction;
existing system/libvirt configuration is not a pilot deployment destination.

**Next read-only check requested in the parent conversation:**

```sh
sudo nft list ruleset
```

Its result is pending. No firewall inspection or modification was executed by
this journal/source update. No process was started, stopped, restarted or changed.

## After service review — Offline PXE pilot files prepared (time not captured)

**Approval/provenance:** the user approved preparing pilot configuration files
for review, not activation. The supplied firewall snapshot reported iptables-nft
and libvirt-managed IPv4/IPv6 filter/NAT/mangle state, accept input/output policies
and existing virtual-network rules. Raw private addresses/rules are not copied
here. Existing system/libvirt instances and their tables remain untouched.

**Local source result:** added `pxe/pilot/inputs.example.yml`, local-only
`prepare.yml`, standalone dnsmasq/nginx/GRUB/nft/review-manifest templates, a staged
runbook and offline tests. Linked the pilot checks into the existing offline CI
workflow. Prior journal/obsolete-resource cleanup is preserved. The renderer has
only assertions, local path metadata and review-file tasks; no launch, media,
package, command, service or firewall actions.

**Private nonsecret preparation:** created an ignored partial operator input file
at `.secrets/pxe-pilot/inputs.yml`, mode 0600 in a 0700 directory, with known pilot
network fields only. Actual MAC/address/interface values are intentionally not
logged. Media/firmware review, service identity and output remain unset, so no
real operator service configuration was rendered. Synthetic review outputs were
rendered only inside temporary test directories and cleaned up by their fixtures.

**Commands actually executed for validation:**

```sh
/usr/sbin/dnsmasq --version
python3 -m unittest discover -s pxe/pilot/tests -v
ANSIBLE_LOCAL_TEMP=/tmp/perkforge-pxe-syntax ansible-playbook -i localhost, pxe/pilot/prepare.yml --syntax-check
python3 -m unittest discover -s infrastructure/ansible/tests -v
git diff --check
```

**Safe outcomes:** installed dnsmasq identified itself as 2.91 with DHCP/TFTP
support. Latest pilot test run: `Ran 4 tests in 11.142s`, `OK`, exit 0. Existing
infrastructure suite: `Ran 18 tests in 46.039s`, `OK`, exit 0. Ansible syntax and
whitespace checks returned exit 0. Documentation link/fence checks, YAML parsing,
private-input permissions and absence of actual pilot network identifiers from
tracked pilot source also passed. Exact validation times were not captured.

Pilot fixtures invoked dnsmasq **only with `--test --conf-file=<synthetic file>`**
and the installed `grub-script-check` against the synthetic GRUB file. Those native
parser checks passed without starting services or running GRUB commands. Missing
identity/media inputs, unsafe paths/values and preexisting output are rejected;
checks verify controller-local file/validation modules only. None of these tests
sent packets or inspected/mounted/copied the ISO.

**Proposed scope, not applied:** dedicated serving roots under
`/srv/perkforge-pxe-pilot`, runtime/PID state under `/run/perkforge-pxe-pilot`, and
protected logs under `/var/log/perkforge-pxe-pilot`; no system include path. DNS
is off; IPv4 proxy-DHCP supplies no leases/router/DNS/RA overrides. Pilot-only
MAC tags target DHCP/PXE replies; separate source/interface restrictions cover
TFTP (UDP 69 plus proposed 20000–20009) and HTTP (proposed TCP 8080). UDP 67/68 and
PXEBS 4011 are reviewed separately. Pre-address source 0.0.0.0 is retained for
pilot DHCP. An optional new `inet perkforge_pxe_pilot` table has default accept
and restrictions only for pilot-reserved services; existing tables are not edited.
IPv6/alternate-address retrieval is blocked by the proposal. MAC/IP spoofing is
not solved by these controls; nonsecret content and the LAN trust boundary remain
explicit review requirements.

**Outstanding gates:** real DVD EFI layout/signatures, GRUB prefix/command dialect,
firmware architecture/Secure Boot trust, dedicated service identity, media staging
approval and unknown-client tests for both proxy/PXEBS phases. Native nginx syntax
validation is unavailable because nginx is not installed; no package was installed.
Native nft validation was not attempted: no privileged check or apply is authorized.
GRUB waits indefinitely for explicit selection and provides no Kickstart, automatic
installer timeout or disk command. Native parser success does not prove firmware,
packet filtering, household coexistence or RHEL/platform compatibility.

**Next decision:** review these files and proposed service/port reservations
side by side. Request separate approval for media inspection and remaining native
validation before completing real operator inputs; then agree an isolated
positive/negative packet-test and activation scope. Do not launch yet. The runbook
limits shutdown to verified pilot PID/config pairs, listeners and the one dedicated
table; no global process kills or whole-ruleset rollback. No mount, extraction,
service/socket start, firewall/network operation, node contact/power, real-secret
access, commit or push occurred in this preparation.

## 2026-10-30 21:42:32 UTC — Pilot documentation/HTTP design accepted

**User decision/provenance:** the user approved the documentation and nginx as a
design choice. Package installation, activation and configuration of host services
were **not** approved by this choice. Outstanding native nginx/nft and media/trust
validation gates remain in place.

## 2026-10-30 21:43:43–21:44:23 UTC — Non-mount ISO metadata inspection

**Purpose/approval:** the user authorized read-only ISO directory and boot-metadata
inspection using installed non-mount tools. No mount/loop device, filesystem
extraction/staging, install/download, service/firewall change or node action was
approved or performed. `$REPO_ROOT` normalizes the actual checkout path as defined
above; no variable assignment is implied. The times bracket the inspection, not
individual command start/finish intervals.

**Commands executed (paths normalized):**

```sh
date -u '+Inspection: %Y-%m-%dT%H:%M:%SZ'
xorriso -indev "$REPO_ROOT/images/rhel-10.2-x86_64-dvd.iso" -ls /EFI/BOOT -- -ls /images/pxeboot -- -ls / --
7z e -so "$REPO_ROOT/images/rhel-10.2-x86_64-dvd.iso" .treeinfo
7z e -so "$REPO_ROOT/images/rhel-10.2-x86_64-dvd.iso" EFI/BOOT/grub.cfg
7z e -so "$REPO_ROOT/images/rhel-10.2-x86_64-dvd.iso" .discinfo
7z e -so "$REPO_ROOT/images/rhel-10.2-x86_64-dvd.iso" EFI/BOOT/BOOTX64.EFI | file -
7z e -so "$REPO_ROOT/images/rhel-10.2-x86_64-dvd.iso" EFI/BOOT/grubx64.efi | file -
xorriso -indev "$REPO_ROOT/images/rhel-10.2-x86_64-dvd.iso" -ls /BaseOS -- -ls /AppStream -- -ls /images --
7z e -so "$REPO_ROOT/images/rhel-10.2-x86_64-dvd.iso" EFI/BOOT/BOOTX64.EFI | strings | rg '^(sbat|shim)([,\.])'
7z e -so "$REPO_ROOT/images/rhel-10.2-x86_64-dvd.iso" EFI/BOOT/grubx64.efi | strings | rg '^(sbat|grub)([,\.])'
date -u '+Completed: %Y-%m-%dT%H:%M:%SZ'
```

`7z -so` streamed selected members to stdout/process pipes only; it did not write
extracted files. Xorriso used `-indev` and listing commands, no output device,
commit, or media-writing operation. Installed tool discovery found xorriso, 7z,
file, strings and objdump; no new tool was installed.

**Safe observed output/metadata:**

| Item | Actual observation |
|---|---|
| Volume label | `RHEL-10-2-BaseOS-x86_64` |
| `.treeinfo` | RHEL 10.2, `arch = x86_64`; variants `AppStream,BaseOS` |
| EFI members | `EFI/BOOT/BOOTX64.EFI`, `grubx64.efi`, `mmx64.efi`, `grub.cfg`, `fonts/` |
| PE format | BOOTX64.EFI and grubx64.efi both identify as PE32+ EFI applications, x86-64 |
| Embedded SBAT identity | BOOTX64.EFI contains UEFI shim / Red Hat shim 15.8 identity rows; grubx64.efi contains GRUB 2.12 / `2.12-46.el10_2` identity rows |
| Kernel/initrd | `.treeinfo` points to `images/pxeboot/vmlinuz` and `images/pxeboot/initrd.img`; both listed |
| Installer runtime | `.treeinfo` stage2 `mainimage = images/install.img`; member listed |
| Package tree | `BaseOS/Packages`, `BaseOS/repodata`, `AppStream/Packages`, `AppStream/repodata` listed |
| Other boot images | `images/efiboot.img`, `images/eltorito.img`; El Torito EFI image also reported |

**Actual GRUB excerpt:**

```text
set default="1"
set timeout=60
search --no-floppy --set=root -l 'RHEL-10-2-BaseOS-x86_64'
linuxefi /images/pxeboot/vmlinuz inst.stage2=hd:LABEL=RHEL-10-2-BaseOS-x86_64 quiet
initrdefi /images/pxeboot/initrd.img
```

The DVD has a separate `fips=1` entry; that is not the selected non-FIPS pilot.
The stock menu depends on a local DVD label and a countdown/default selection;
it is **not** an unchanged network-pilot menu. The separate reviewed pilot menu
must use the network installation source and explicit selection after approval.

**Status/provenance:** actual stdout from installed tools, not filename inference
alone. Inspection command results reported exit 0; standalone `.treeinfo`/GRUB
reads succeeded. For grouped commands/pipelines the captured status is the batch
or final pipeline component, not independently recorded status for each stage.
The embedded kernel/initrd/runtime checksums in `.treeinfo` are metadata; no
separate per-member hash comparison was performed. The whole-ISO published-hash
match remains the earlier recorded evidence.

**Limits/next validation:** file paths, PE type and embedded shim/GRUB identity
are **not cryptographic signature or firmware-trust verification**. No validation
of the signature chain, target firmware db/dbx/SBAT acceptance, or GRUB's network
prefix/config lookup was performed. `sbverify`/`pesign` were not found on PATH in
the tool lookup; no package availability conclusion or installation follows from
that alone. Review signature-verification tooling and the pilot's firmware state
as separate next steps. No operator input review flag was enabled, no configuration
was activated, and nothing was committed/pushed. Stop after this inspection.

## 2026-10-30 21:48–21:54:30 UTC — User-performed pilot firmware inspection

**Scope/provenance:** after the explicit inspection prompt at 21:48 UTC, the user
powered **control-1 only** into firmware setup. The user confirmed the following
settings, with final confirmation at 21:54:30 UTC:

- Secure Boot: **Enabled**.
- Boot mode: **UEFI Only**.
- Onboard Ethernet / PXE Option ROM / PXE IPv4 stack: **Enabled**.

This is user-reported firmware observation, not an agent probe or a successful
network boot. The timestamps describe the prompt/final confirmation window, not
an inferred machine power/command interval. Earlier “all nodes off” statements
remain historical checkpoints; control-1 is now reported in firmware setup and
both workers remain off.

**Additional photo context:** photo OCR also indicated IPv6/wireless enabled.
Those observations were not treated as requirements to change any settings.
No firmware setting was changed, and no network boot or installation occurred.

**Interpretation/limits:** enabled settings establish the reported firmware
configuration only. ISO loader signature validity, db/dbx/SBAT acceptance and
actual firmware acceptance of that loader remain unproven. This entry grants no
boot, media-staging, disk-write or configuration authority.

**Pending:** the parent conversation proposes a read-only workstation space and
staging-path check; approval is **pending**, so no such check was performed here.
Continue only after the next bounded action is reviewed and approved.

## 2026-10-30 21:55:38–21:56:14 UTC — Read-only staging paths and capacity

**Approval/purpose:** the user approved workstation free-space and proposed-path
inspection only, before reviewing any extraction. No directory creation, permission
change, mount, media extraction/staging, installation, service/network operation or
node action was performed. Times bracket the inspection, not each individual call.

**Commands/checks actually performed:** read the pilot's tracked inputs/runbook;
used `lstat` on only the proposed paths and their parent chains, and `statvfs` on
the nearest existing parent for available bytes/inodes, total space and read-only
flags. No unrelated directory contents were listed. The size/ISO commands were:

```sh
stat -c 'ISO size: %s bytes' "$REPO_ROOT/images/rhel-10.2-x86_64-dvd.iso"
xorriso -indev "$REPO_ROOT/images/rhel-10.2-x86_64-dvd.iso" -lsdl /EFI/BOOT -- -lsl /EFI/BOOT -- -lsl /images/pxeboot --
```

A separate read-only Python verification captured
`xorriso -indev <ISO> -find / -type f -exec lsdl --` in memory and summed listed
regular-file sizes, including a separate EFI/pxeboot subtotal. `<ISO>` denotes the
same normalized ISO path above, not another input. No payload was expanded or
written. Listing/check command results returned exit 0.

**Visible path/capacity results:**

| Proposed path | State | Existing parent / available bytes / available inodes |
|---|---|---|
| `/srv/perkforge-pxe-pilot/tftp` | Absent; pilot parent absent | `/srv`: 749,975,977,984 bytes; 59,278,830 inodes |
| `/srv/perkforge-pxe-pilot/http/rhel-10.2` | Absent; pilot/http parents absent | `/srv`: same filesystem/capacity as above, not additional space |
| `/run/perkforge-pxe-pilot` | Absent | `/run`: 1,603,870,720 bytes; 1,959,235 inodes |
| `/var/log/perkforge-pxe-pilot` | Absent | `/var/log`: 749,975,977,984 bytes; 59,278,830 inodes, shared with persistent staging filesystem |

Visible `/`, `/srv`, `/run`, `/var` and `/var/log` entries are directories with
mode `drwxr-xr-x`; no symlink was found in the inspected chains. Ownership is
shown as UID/GID 65534 and filesystem flags are **read-only in this execution
environment**. This is a namespace/sandbox view, not confirmation that native host
parents are actually owned by that identity or writable by the operator. Native
ownership/write authority remains to be checked before any staging approval.

**Measured media-size evidence:** ISO size remains **11,059,986,432 bytes**.
ISO directory metadata lists **5,992 regular files**, logical payload
**11,040,512,694 bytes**. The EFI tree plus pxeboot files adds **7 files /
247,420,950 bytes** if duplicated into TFTP. Estimated full HTTP tree plus
separate TFTP boot payload: **11,287,933,644 bytes**, before filesystem metadata,
logs or temporary overhead. This is a metadata sum, not a completed extraction
or disk-allocation measurement; file/directory metadata and extraction behavior
can change actual space usage. A proposed **16 GiB content-staging budget** leaves
approximately **732,796,108,800 bytes** of the sampled available persistent space.
No space was reserved. Available counts are point-in-time and may change.

**Interpretation/restrictions:** capacity and inode counts have substantial margin
for this pilot; they do not establish native write permissions, safe service
activation or ownership compatibility with `tftp-secure`. `/run` is runtime state
only, not a media destination. Do not create/write these read-only exposed parents
from this environment or redirect serving into the repository/home as a workaround.
No symlink finding is a guarantee against later path replacement.

**Next proposal for review, not execution:** confirm native parent ownership and
the selected unprivileged service identity, then separately approve creating only
the dedicated serving directories and copying the verified full DVD tree into
HTTP plus the reviewed EFI/pxeboot files into TFTP, with explicit nonsecret
ownership/modes and no overwrite of preexisting paths. Recheck paths/capacity
immediately before that operation. No mount, extraction, service or firewall
activation is authorized by this capacity result; runtime/log creation and launch
remain separately gated. Stop after the read-only report.

## After capacity review — Native ownership report and bounded staging proposal

**User-supplied native evidence (time not captured):** `/srv`, `/run` and
`/var/log` are root:root 0755 on the workstation. Existing nologin service
identities are dnsmasq (UID 999, primary GID 65534) and www-data (UID/GID 33).
The native GID-65534 group name still needs confirmation. No account, group,
permission or directory was changed by this review.

**Local proposal/refinement:** `pxe/pilot/STAGING-PROPOSAL.md` contains two
unexecuted native batches: A creates only fresh root-owned 0700 staging
directories; B performs non-mount copying into those roots, refuses unexpected
objects/collisions and normalizes ownership/modes before exposure. It disables
xorriso startup files, ACL/xattr/hard-link restoration, special-file restore and
overwriting. Root-only ancestors remain closed during extraction. The ISO hash
and native paths must be rechecked before execution; no files are staged now.

Root-owned 0555 directories and 0444 regular files are proposed for both public
media trees, with no shared group. Separate existing HTTP/TFTP identities are
now required by the offline renderer. Its new ownership-policy input remains
UNCONFIGURED until the user accepts root-readonly explicitly. That proposal
omits `tftp-secure`: it rejects root-owned files, while service-owned 0444 files
are not strictly read-only because their owner can chmod them. Dedicated-root,
no-symlink and ingress protections remain required. No live security setting
was changed; retaining tftp-secure would require a separately reviewed read-only
filesystem strategy, not an unapproved mount.

**Read-only extraction-tool/source review:** inspected the installed xorriso help
and manual and enumerated ISO metadata. No symlink or special-object nodes were
reported by the type query. The complete listing includes 5,992 regular files
and 18 directories including root; observed UID/GID pairs include 0:0 and
2024:2024. No setid/sticky modes or traversal/control/backslash names were found.
An early diagnostic's 6,009-entry assumption and then all-root ownership assertion
failed; corrected enumeration identified the included root and nonroot build
ownership. These were read-only diagnostic failures, not extraction attempts.
Ownership normalization in the proposed batch is therefore mandatory.

**Validation:** four pilot tests passed (`Ran 4 tests in 12.624s`, `OK`), including
native dnsmasq syntax and GRUB parser checks on synthetic outputs. Proposal shell
blocks passed `bash -n` via stdin, which parses without executing them. Local
links/fences and YAML checks passed. These checks do not approve or execute the
proposal, verify native write access, inspect private keys or validate Secure Boot.

**Execution restriction/next decision:** this agent's current `/srv` view remains
read-only. Native user execution or separately approved, verified native write
access is needed; no bypass or alternate media destination was attempted. Review
the ownership-policy choice and approve only batch A if desired, then inspect its
results before separately approving B. No runtime/log directories, media copies,
mounts, package/service/firewall/network/node actions, commit or push occurred.

## Before 22:15:02 UTC — Batch A paste incident (exact failure time not captured)

**User report/provenance:** the user approved Batch A, pasted the supplied block
into Konsole and reported that the terminal closed. The supplied workflow was
incorrect: uncontained `set -euo pipefail` changed the interactive shell, so a
failed command could terminate it. The block also relied on an ISO variable it
never assigned, and suppressed checksum diagnostics with `--status`. These are
workflow defects, not grounds to blame the user. Exact shell/failing command and
partial effects were initially unknown; no successful or zero-change result was
inferred and no batch was rerun or cleanup attempted by the agent.

## 2026-10-30 22:15:02 UTC — Native user reports all four proposed paths absent

**Safe output summary:** the native user stat returned “No such file or directory”
for `/srv/perkforge-pxe-pilot`, its `http` and `tftp` directories, and
`http/rhel-10.2`. This establishes **directory creation absent at that observation**,
not proof of which earlier command failed. No cleanup is needed. No extraction or
Batch B operation is inferred from the incident; Batch B has not been authorized.

## After native stat — Local execution-safety correction and offline tests

**Local changes only:** corrected both proposal blocks in
`pxe/pilot/STAGING-PROPOSAL.md` to run as separate Bash processes with an explicit
ISO-path argument, child-only strict options and named ERR-step/status output.
An outer status handler keeps batch failures from terminating the interactive
caller. No inherited ISO variable is required. Guard AND-lists were split;
command-substitution status is captured before inspecting output, so a failed
scan cannot look like a successful empty-tree check. Existing paths still block
writes; no automatic deletion, reset or retry was added.

**Actual offline validation command:**

```sh
python3 -m unittest discover -s pxe/pilot/tests -v
```

**Safe result:** `Ran 9 tests in 12.761s`, `OK`, exit 0. Five new tests parse the
complete Markdown blocks and exercise missing ISO, checksum failure, existing-root
rejection, failed/nonempty directory scans and a mutation failure. They run the
caller with strict options too, confirm it survives, and confirm failures do not
proceed to later writes. All native `/srv` references are replaced with temporary
paths before execution; sudo/mutation commands are mocked and never delegated.
No native staging block, disk command or service action is executed by these tests.

**Lesson/next decision:** never supply uncontained session-changing strict-mode
commands for direct interactive paste. Review the full contained replacement and
explicit ISO argument before any specifically approved retry. The wrapper prints
child completion/failure and its status; its final printf/caller `$?` is not the
batch result. Current absence is recorded, but no retry or Batch B authority is
created by a documentation correction. No native writes, cleanup, extraction,
permission change, commit or push occurred here. Times for correction/testing
were not captured.

## 2026-10-30 22:22:38 UTC — User-supplied corrected Batch A completion

**Provenance:** the user ran the reviewed contained Batch A on the native
workstation and supplied its result. No agent rerun or native write was performed
for this journal update. The timestamp is the supplied result time, not an
inferred execution interval; an individual child exit code was not supplied.

**Safe result summary:** native identity lookups showed dnsmasq UID 999 / GID
65534, www-data UID/GID 33, and the primary group name `nogroup` for GID 65534.
All four selected directories reported **0:0:700**:

```text
0:0:700 /srv/perkforge-pxe-pilot
0:0:700 /srv/perkforge-pxe-pilot/http
0:0:700 /srv/perkforge-pxe-pilot/tftp
0:0:700 /srv/perkforge-pxe-pilot/http/rhel-10.2
Batch A completed. STOP and review; no next batch is authorized.
```

**Interpretation/limits:** directory creation and the displayed ownership/modes
are confirmed by user output at this checkpoint. This supersedes the earlier
absent-directory observation without rewriting that incident history. No media
copy, extraction, mount, service or firewall operation was part of Batch A.

**Next decision:** approval for Batch B is **pending**. Its read-only review
confirms a separate child Bash block with one explicit ISO-path argument, writes
confined to the new `/srv/perkforge-pxe-pilot` payload tree, non-mount extraction,
boot-file comparisons, root ownership/read-only-mode normalization and service
read-access checks. It contains no mount, package install, service start, firewall
or node action. Existing approval and ISO/type/path recheck gates remain. Do not
execute B or reset any paths based on this journal entry.

## After Batch A — Batch B paste incomplete; execution status uncertain

**User report:** the Batch B block did not all paste in; no xorriso progress or
completion output was seen. The parent advised returning from a continuation
prompt only if no extraction was active. No actual Ctrl-C, native process state
or exact stopping point is inferred here. No block retry or cleanup was performed
by the agent. Original Batch B approval does not authorize an uncertain rerun.

## 2026-10-30 22:28:34 UTC — User reports staging destinations still empty

**Safe native listing summary:** TFTP contained only `.` and `..`; HTTP contained
only `rhel-10.2` plus `.` and `..`; that installation directory contained only
`.` and `..`. The reported directories were root-owned mode 0700. No cleanup is
needed for this observed state. This does not prove no preflight command ran or
that no staging process remains active; process verification is still required
before deciding whether execution is safe.

## After empty-tree report — Standalone reviewed Batch B prepared locally

**Local files only:** `pxe/pilot/stage-media.sh` contains the exact reviewed Batch
B child body, plus an explicit completion message. No source/eval, implicit next
step, automatic retry/resume or cleanup was added. The script receives the ISO
path as its explicit argument; strict options and named ERR-step/status handling
remain inside its separate Bash process. The runbook now prefers a short external
script invocation after the uncertain-state hold is cleared; the long block stays
reference/parity material only.

**Validation actually run:** `bash -n pxe/pilot/stage-media.sh` passed without
execution. `python3 -m unittest discover -s pxe/pilot/tests -v` returned
`Ran 12 tests in 12.757s`, `OK`, exit 0. New checks prove body parity, caller
survival and no writes after guard failure; mocked extraction failure stops before
copy/ownership/mode operations. Native `/srv` paths are replaced with temporary
paths before fixture execution; privileged mutation commands are mocked and never
delegated. No real media or native staging path was accessed by these tests.

**Next read-only review proposal:** inspect relevant xorriso/copy/check processes
and, if one is active, its parent staging shell; then reconcile the original
terminal and the approved path metadata before any specifically approved retry.
No xorriso result alone proves idleness after extraction could have advanced.
Do not interrupt an active operation or rerun into partial state. No staging,
cleanup, native permission change, service/firewall/node operation, commit or push
was performed by this preparation. Exact report/preparation times were not
captured except the supplied native listing timestamp above.

## 2026-10-30 22:33:05 UTC — User-supplied native Batch B completion

**Safe output/provenance:** the user supplied xorriso 1.5.6 progress loading 6,009
ISO nodes and extracting `/` into
`/srv/perkforge-pxe-pilot/http/rhel-10.2`, followed by:

```text
11300782080 /srv/perkforge-pxe-pilot
Batch B completed. STOP and review; no next batch is authorized.
```

This is user-performed native execution, not an agent rerun. The byte count is
reported `du` allocation, distinct from the earlier logical-payload estimate.
The completion message supports that the reviewed script's comparison,
root-ownership/read-only-mode and service-read-access gates completed. The agent
has not independently probed the staged tree. No runtime services or network boot
are claimed; stock copied GRUB remains unsuitable for unchanged pilot serving.
No individual process exit code or command start/finish interval was supplied.

## From 2026-10-30 22:33:49 UTC — Read-only package/autostart planning

**Scope:** inspected existing package metadata and installed Ansible/init helper
code, and ran unprivileged install simulations with locking/cache writes disabled.
No package refresh, download, install, policy file creation, unit mask, service
start, firewall or node action was performed. The time is the first captured
inspection timestamp, not a claimed completion interval.

**Commands actually used:** package queries via `dpkg-query`/`apt-cache policy`
for nginx variants, sbsigntool, pesign and policy-rcd-declarative; metadata-only
presence checks for nginx units/configuration and policy-rc.d; read-only installed
helper/module documentation. Resolver commands were:

```sh
apt-get --simulate -o Debug::NoLocking=1 -o Dir::Cache::pkgcache= -o Dir::Cache::srcpkgcache= --no-install-recommends install nginx
apt-get --simulate -o Debug::NoLocking=1 -o Dir::Cache::pkgcache= -o Dir::Cache::srcpkgcache= --no-install-recommends install sbsigntool
apt-cache depends nginx sbsigntool pesign
systemctl show nginx.service -p LoadState -p ActiveState -p SubState -p UnitFileState --no-pager
```

**Safe results:** in this execution view, nginx/nginx-common and the signature
packages were not installed; no nginx unit/configuration or policy-rc.d path was
present. Cached nginx/nginx-common candidate: **1.26.3-3+deb13u10**. Nginx simulation
returned exit 0 and proposed exactly two new packages, zero upgrades/removals,
nine held back. Separate sbsigntool simulation returned exit 0, one new package
**0.9.4-3.2+deb13u1**, zero upgrades/removals, nine held back. Autoremove suggestions
were not acted on. No cache age/current-mirror availability guarantee follows.
System Python could import `apt`; module dependency installation is unnecessary
in this view and should be explicitly disabled in a bounded future apt task.

**Native-state limitation:** systemctl could not connect to the system scope bus:
`Operation not permitted`. Native nginx unit state therefore remains **unknown**;
no assumption of inactivity is made and no stop is proposed for an existing
service. The package/path view must also be confirmed natively before writes.

**Supported next-batch proposal, not executed:** after native unit/policy checks
and explicit approval, mask only the verified-absent/inactive default nginx unit
as a persistent no-autostart guard, then use `ansible.builtin.apt` with exact
reviewed versions, `policy_rc_d: 101`, `update_cache: false`, no recommends,
no removals/upgrades and `auto_install_module_deps: false`. This documented module
option backs up/restores an existing policy-rc.d on normal completion; verify
original type/link/mode/owner/content metadata afterward. Abrupt interruption
still needs recovery review, not a promise of unconditional restoration. Preserve
preexisting masks/admin policy; abort on active/custom nginx rather than stop it.
Keep the new default-unit mask in place pending separate activation review;
policy suppression alone does not establish boot-time disablement. No manual
policy overwrite, new declarative-policy package or blanket service suppression
is applied here. This future batch requires explicit install/download, temporary
policy handling and default-unit masking authority.

**Separately scoped tooling:** sbsigntool is the smaller proposed signature-tool
install; pesign pulls additional tooling and is not currently needed. `sbverify
--list` only lists signatures; cryptographic verification requires a reviewed
public certificate and does not itself establish firmware db/dbx/SBAT acceptance.
No signing key, credential or new trust setting is proposed. Native verification
and approval are the next gate; stop after this read-only plan.

## After 2026-10-30 22:39:57 UTC — Approved nginx install prepared, native execution pending

Operator supplied native `systemctl show nginx.service` output: `LoadState=not-found`, `ActiveState=inactive`, `SubState=dead`, empty `UnitFileState`; reports `/usr/sbin/policy-rc.d` absent. Operator explicitly approved installation of nginx/nginx-common 1.26.3-3+deb13u10 with temporary maintainer-start denial and masking nginx.service. This does not authorize HTTP/PXE activation, firewall changes or node actions.

Prepared `pxe/pilot/install-nginx.yml`, localhost-only. It rechecks exact initial unit/policy state and the resolver transaction before mutation, masks only nginx.service, uses Ansible apt `policy_rc_d: 101` with no refresh/recommends/removals/dependency auto-install, verifies policy restoration even on normal task failure, then checks versions, masked/inactive state and no new listening sockets. Abrupt process termination/power loss can bypass cleanup; inspect policy and package state before any retry. An unexpected policy is never automatically deleted. No concurrent package operations should run during this batch.

Offline checks actually run: Ansible `--syntax-check` passed; two unittest tests passed, including synthetic resolver acceptance and rejection of extra packages, changed versions and removals. Fixtures execute only Ansible assertions; they do not invoke package/system/service operations. `git diff --check` passed. Syntax-only Ansible uses `ANSIBLE_LOCAL_TEMP` under `/tmp` because the execution view cannot write the default home temporary directory.

Native installation has NOT been attempted by the agent: system bus access was previously unavailable and system directories are read-only in this execution environment. No bypass/escalation attempted. The approved batch is prepared for operator execution using the absolute playbook path, explicit localhost inventory/local connection and become password prompt. Password must be entered only at the native Ansible prompt, never in logs or arguments. Expected success ends with a STOP message; a failed guard or partial install requires review rather than automatic rerun. Default nginx unit remains masked pending separate activation review. Package output may include local socket details; sanitize before recording publicly.

## 2026-10-30 22:44–22:46:13 UTC — User-performed nginx install and verification

First operator run failed at the first privileged read-only task because of a mistyped sudo password; reported changed=0, no installation. The operator reran after correcting authentication. At 22:45:31 the supplied recap was ok=20 changed=2 unreachable=0 failed=0. At 22:46:13 native unit output showed LoadState=masked, ActiveState=inactive, SubState=dead, UnitFileState=masked; operator confirmed temporary policy-rc.d absent/restored. These are user-supplied native results, not an agent rerun. Successful playbook recap supports its installed-version and listener-comparison assertions; no packet or HTTP-serving test was performed. No service activation authorized.

Under earlier offline-file preparation approval, updated the ignored mode0600 nonsecret pilot inputs with existing service identities, root-readonly ownership selection, observed EFI/kernel/initrd paths and observed GRUB command dialect. Kept media/signature and firmware review flags false, architecture tag and network GRUB lookup path unresolved, output unset. No real operator config rendered: existing gates correctly block it. Filenames and enabled Secure Boot do not establish signature validity or firmware acceptance. Native signature tooling availability and reviewed public trust material remain prerequisites; no tools installed for this step.

Parser distinctions for subsequent review: `dnsmasq --test --conf-file=<review-file>` parses without starting service; `nginx -t -c <absolute-review-file>` can open configured logs/create temporary directories and therefore is not automatically an authorized read-only action for the live-path template; `nft -c -f <review-file>` requires native privilege but does not apply rules. None of those native operator-config checks executed in this step. Proposed minimum next read-only native lookup: `command -v sbverify; command -v pesign` to determine signature-tool availability before separately approving any installation. Signature listing alone would not verify trust. No service, firewall, firmware, credential or node changes; no commit/push.

## Subsequent read-only boot-chain review — signatures, media identity and finite boot gate

Operator reports installation of sbsigntool 0.9.4-3.2+deb13u1: one new package, no upgrades/removals. Operator supplied `sbverify --list` shim output with three signature chains (Microsoft UEFI CA 2011, Microsoft UEFI CA 2023, Red Hat UEFI CA 2024) and GRUB signed by Red Hat Secure Boot CA 8. Listing is not signature verification. Agent reproduced shim listing read-only; warning: `data remaining[910008 vs 1038016]: gaps between PE/COFF sections?`.

Upstream [sbsigntools image.c](https://kernel.googlesource.com/pub/scm/linux/kernel/git/jejb/sbsigntools/+/b05afccde0b9e664bdf492f92e812a0ba53d41ea/image.c) emits that warning when accounted image bytes plus certificate-table bytes differ from file size. It is a structural accounting warning, not a signature verdict. That historical source explains the message, not a guarantee about every installed-version hashing edge case. Do not dismiss it or modify/re-sign the vendor image.

Agent read-only commands included `objdump -h` and `objdump -s -j .vendor_cert` on the staged shim, `strings` on GRUB, and `sbverify --help/--list`. A bounded Python stdout-only check parsed public EFI X.509 signature lists from objdump output and piped DER through `openssl x509` to PEM, then `sbverify --cert /dev/stdin <staged-grub>`; no certificate files were written. Initial PE section-name parser failed before verification (long section name not resolved); corrected inspection used objdump's resolved section. Shim contains Red Hat Secure Boot CA 5 and CA 8 public certificates. GRUB verification against CA 5 failed as expected for this signer; against embedded CA 8 returned exit0 `Signature verification OK`. CA8 public SHA256 fingerprint: 72:56:80:59:45:5C:17:74:B3:66:8B:5F:D6:7B:A3:57:85:51:92:5A:DF:A5:2B:69:99:CA:D5:49:F5:2E:46:D6. This verifies GRUB's signature against public trust material embedded in this ISO shim; it does not validate shim against the target firmware's db/dbx or establish SBAT acceptance.

Agent compared `7z x -so <verified-ISO> EFI/BOOT/{BOOTX64.EFI,grubx64.efi}` bytes in memory with both HTTP and TFTP staged copies using SHA256. All four comparisons matched. Shim SHA256 bada1f231e3569aaa161e0a0a89504d569d4b575fcc4c3abd8dc3bc2695033ad; GRUB aff32af97f1a714dd05dd3894ba1f721a3685df4513fa948fff166e88d938a34. No extraction to filesystem or writes to staging occurred. Source ISO identity was independently matched to Red Hat's published checksum earlier. Kernel signature/firmware execution not tested.

[Red Hat RHEL10 PXE instructions](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/preparing-a-pxe-installation-source) explicitly use option93=0x0007 for UEFI x86_64, copy DVD EFI files and place the menu in EFI/BOOT/grub.cfg beside the loaders; linuxefi/initrdefi are documented. [Current dnsmasq source](https://raw.githubusercontent.com/imp/dnsmasq/master/src/option.c) maps index7 to x86-64_EFI and9 to BC_EFI; do not blindly use old RFC label assumptions or advertise both. [GRUB manual](https://www.gnu.org/software/grub/manual/grub/grub.html#Network) documents network config search relative to boot path and machine-specific variants before grub.cfg. Proposed documented pilot values are architecture7 and EFI/BOOT/grub.cfg; actual firmware advertisement/requests remain a later controlled-boot observation, not a preboot fact.

Finite next gate: review and authorize using those documented candidates for offline configuration preparation, explicitly retaining target firmware trust/architecture/lookup acceptance as pending runtime evidence. Do not claim verified firmware flags or weaken existing gates silently. Later separately approved, restricted pilot services/firewall and one-time network boot with Secure Boot ON can establish shim/GRUB acceptance and actual requests; stop at the indefinite menu, without selecting installer or writing disks. If rejected, record error and shut down dedicated pilot services; no key enrollment or Secure Boot disablement. No services/packets/firewall/node/key changes performed in this review, no commit/push.

## Subsequent workstation-only candidate rendering and parser results

Minimal gate correction: replaced conflated firmware-reviewed input with `pxe_boot_candidates_reviewed`, which attests review of documented source candidates, not runtime firmware observations. Manifest explicitly labels NODE-FACING RUNTIME EVIDENCE PENDING: architecture advertisement, db/dbx/SBAT acceptance, actual requests and installer/kernel acceptance. Installed dnsmasq reports2.91; its installed manpage architecture sequence and upstream v2.91 option.c map7=x86-64_EFI,9=BC_EFI. Selected7 only. Reviewed source values do not imply node contact.

Updated ignored mode0600 nonsecret input file and executed Ansible local renderer with `-i localhost, -c local`, private vars and `/tmp` local/remote temp directories. Render recap ok9 changed2 unreachable0 failed0. New private output `/tmp/perkforge-pxe-review-20261030-candidates` contains dnsmasq.conf, nginx.conf, grub.cfg, ingress.nft, review.txt (0600; directory0700). No live configuration paths written. Rendered source candidates include EFI/BOOT/BOOTX64.EFI, EFI/BOOT/grub.cfg and media-observed linuxefi/initrdefi. Workers excluded.

Actual safe checks: `/usr/sbin/dnsmasq --test --conf-file=<review>/dnsmasq.conf` returned syntax check OK; `grub-script-check <review>/grub.cfg` returned0 without output. Created private nginx-check-runtime/nginx-check-logs under review output and used the same Ansible template to generate nginx-syntax.conf with only runtime/log path substitutions there. Ran `/usr/sbin/nginx -t -p <review>/ -e stderr -c <review>/nginx-syntax.conf`: reported configuration syntax OK, warned nonroot user directive ignored, then FAILED exit1 at `socket() <WORKSTATION_IP>:8080` with Operation not permitted. This corrects the earlier assumption that -t would avoid sockets: it attempts socket creation even during testing. No listener started, no packets sent by the check, no retry/bypass. Complete nginx test remains pending, not passed. Native retry requires explicit approval of socket/log/temp behavior; original live-path config has not been tested natively. No nft check or apply executed; privileged native `nft -c` remains pending.

No services/unmasking/firewall/node changes, commit or push. Offline tests cover default missing candidates, rejected unreviewed candidates, preserved runtime-pending label and original safety checks. Private review paths are ephemeral, not durable deployment configuration.

## Subsequent correction — nginx test mode and loopback-only test copy

Parent reports a native nginx-t command was sent before the bind/listen warning was read, then immediately issued HOLD and asked whether it had already run. Operator execution/outcome is UNKNOWN at this entry; no rerun authorized. Prior descriptions of nginx-t as a socket-only probe were incomplete. [Nginx1.26.3 cycle source](https://raw.githubusercontent.com/nginx/nginx/release-1.26.3/src/core/ngx_cycle.c) calls ngx_open_listening_sockets in test mode; the [TCP path](https://raw.githubusercontent.com/nginx/nginx/release-1.26.3/src/core/ngx_connection.c) calls socket, bind and listen. ngx_test_config changes some error handling and skips later socket configuration, not those calls. It exits rather than starting request-serving workers; a native test can briefly bind/listen. Agent's earlier attempt failed at socket creation before binding.

Prepared only the private nginx-syntax.conf test copy through the existing Ansible template, changing listen to 127.0.0.1:18080 and retaining review-local PID/log/temp paths. Activation candidate nginx.conf is unchanged. Attempted read-only `ss -H -ltn 'sport = :18080'` was denied at netlink socket creation; no retry/bypass. Therefore port18080 is a proposed test port, NOT verified unoccupied. Native read-only occupancy/path checks must precede separately approved loopback-only nginx-t execution. No socket test executed after this correction. The loopback check cannot validate final LAN binding or live directory permissions. nft-c remains an unapplied check; no firewall operation performed.

## 2026-10-30 22:59:54–23:00:44 UTC — User-approved native validation

Operator explicitly approved loopback nginx-t at22:59:54; user-supplied results at23:00:44 report loopback nginx-syntax.conf test successful and `nft -c -f <private-review>/ingress.nft` exit0. This is configuration testing, not service activation or rule application. Operator was holding the earlier LAN test; no evidence it ran. No agent rerun. Native loopback test may create/re-own review-local temp/log artifacts and briefly listen, as previously disclosed. No assertion of LAN binding, packet enforcement, firmware boot or actual rollback testing follows from these results.

Prepared `pxe/pilot/ACTIVATION-PROPOSAL.md` offline only: exact workstation mutation scope, root-controlled config copies/hashes, final validation after placement, safe TFTP menu replacement, dedicated transient unit names, ingress-first launch ordering, finite tests, separately gated node boot and bounded rollback. Review found current root0700 runtime parent would prevent www-data temp-directory traversal: final layout/config must resolve that before activation. Required isolated pilot/unknown-client DHCP4011/TFTP/HTTP packet fixture remains unexecuted; no activation command is certified ready. No services/firewall/node changes, commit or push.

## Subsequent offline runtime-layout correction and isolated-check proposal

Updated dnsmasq/nginx templates and tests to use separate runtime/log service subdirectories. Proposed runtime/log parents root0711 permit traversal without listing/write; runtime/config root0700 protects root0600 configs. dnsmasq state/log children service0700 and HTTP state/log/temp children www-data0700 provide service-only write access. No live directory/permission changes. Proposed shutdown uses recorded unit identity, not a service-writable PID alone.

Re-rendered revised candidates into new private `/tmp/perkforge-pxe-review-20261030-runtime-layout`, preserving prior validated outputs. Ansible recap ok9 changed2 failed0. Templates changed after prior native validation: revised native final-config checks remain pending; do not reuse old success as acceptance of new paths. New synthetic tests verify revised PID/temp/log separation, existing review gates and pending runtime label. No socket tests rerun.

Read-only tool lookup found ip, dnsmasq, nginx, nft, Python standard library, curl, timeout, BusyBox udhcpc/tftp available; scapy/tcpdump/tshark/dhclient absent. Prepared bounded PACKET-VALIDATION-PROPOSAL.md: two named temporary namespaces and a veth wholly inside them, documentation subnet/synthetic MACs, reviewed foreground services, first daemon-only then namespace nft enforcement, positive/negative controls for proxy67/4011 and TFTP/HTTP, exact cleanup. No extra dependencies proposed. Verification helper/Ansible fixture entrypoint not yet implemented; namespace/packet scope approval is pending. No namespaces, interfaces, sockets, firewall or nodes changed, no commit/push.

## Subsequent approved fixture preparation — offline implementation only

Operator approved preparing and validating the bounded fixture before reviewing a native execution command; this is not approval to execute namespace/packet operations now. Implemented packet-fixture.yml with Ansible-owned synthetic config/lifecycle, recorded namespace inodes, bounded dedicated transient units and always-cleanup; packet-cleanup.yml refuses mismatched unit/run identity, invocation IDs, namespace inode or remaining processes. probe_packets.py performs standard-library synthetic packet verification and passive server observations, with mandatory expected namespace checks before sockets. No Scapy/new dependency, real media/credential inputs or household interface participates.

Protocol based on dnsmasq v2.91 rfc2131.c: discover port67 offers no lease (yiaddr0); boot-item DHCPREQUEST4011 uses option43/sub71 type32768/layer0, ACK yiaddr reflects existing ciaddr and must not be misdescribed as allocation. Unknown MAC negatives bracketed by positives; server AF_PACKET observations require each DHCP/PXE transaction to arrive. Architecture menu matching differs from boot-item lookup; test/document limits explicitly. Separate daemon-only and namespace-firewall file-policy tests use tiny public dummy files, bounded timeouts, missing-file distinctions and final positive controls. Cleanup correctness remains subject to native execution evidence; no pass claim for actual packets.

Offline review additionally isolated shared-template dhcp-leasefile and nginx lock_file under dedicated runtime state, preventing default host state access. These are template changes after prior native parser checks; revised native acceptance pending. Offline validation: Ansible syntax check and Python compile passed; codec tests (including checksum/option71), expected-namespace refusal, observation necessity, configuration-scope assertions and actual Ansible cleanup tasks against temporary mocks passed. Cleanup scenarios include normal removal, wrong unit identity, changed namespace inode and residual process refusal. All mutations in these tests are temporary files; no actual ip/systemctl/nft/socket operation was executed. Full offline test results recorded in report. Full suite:19 offline tests passed; expanded cleanup mocks additionally passed invocation-ID mismatch and partially recorded namespace residual cases. Ansible syntax, Python compilation and git diff checks passed. No fixture execution, services/firewall/node changes, commit or push.

## 2026-10-30 23:19:22–23:21:08 UTC — User-performed isolated fixture

Operator explicitly approved and executed the isolated fixture at23:19:22. User supplied final recap at23:21:08: ok54 changed16 unreachable0 failed0 rescued0 ignored0. This supports all implemented packet assertions and always-cleanup assertions completing successfully, including server observation checks, identity-checked dedicated-unit stops, no remaining namespace PIDs before deletion and both fixture namespace names absent. It is isolated synthetic evidence, not household-LAN/router/firmware/Secure Boot or node-installation validation. No LAN activation approved by this result.

Read-only agent lookup found exactly one matching evidence directory: `/tmp/perkforge-pxe-packets-ppw7hgs2`, containing daemon.json, guarded.json, wrong-interface.json and final-controls.json, each mode0600; file metadata UTC23:20:47–23:20:48 corresponds to this run. Direct agent read of daemon.json was denied by file permissions; no sudo/escalation/bypass attempted, no contents claimed inspected. Prepared a single native read-only summary command using this exact run path (not an ambiguous latest glob) plus namespace-name presence check. Cleanup has no persisted cleanup.json: its historical evidence is the successful Ansible assertions/recap, and the command can check current named namespace absence. No rerun, runtime changes, commit or push.

## 2026-10-30 23:24:27 UTC — User-supplied compact fixture results

Exact run perkforge-pxe-packets-ppw7hgs2: daemon PASS; guarded PASS; wrong-interface PASS; final-controls PASS; fixture namespaces ABSENT. This supplements the earlier successful recap with explicit phase results/current namespace absence. It does not certify physical firmware, Secure Boot, router interoperability or LAN activation.

## Subsequent offline activation/shutdown preparation — no live execution

Prepared activate.yml, activation-placement.yml, verify-activation-copies.yml, shutdown.yml, shutdown-tasks.yml and pilot.sh. The short wrapper dispatches Ansible only; strict shell options stay in its child process. Both Ansible approval flags defaultfalse; native activation is pending a separate exact confirmation. Prepared new private review directory /tmp/perkforge-pxe-review-20261030-activation-reviewed using current shared templates tested in the native namespace fixture. Ansible render ok9 changed2 failed0; dnsmasq-test and GRUB parser passed. Hash-snapshotted four sources in ignored0600 .secrets/pxe-pilot/activation-review.yml. Original TFTP menu hash124ffaa1424fa839e5505c04d2c534a9cf70ca97a16d6db03fe864299164cbec matches ISO menu via read-only 7z stdout verification. No native nginx/nft test rerun during this preparation.

Proposed activation: current interface/address/port/unit/table/media checks, unique root-controlled config session and state/log layout, source/copy hash checks, original-menu backup outside served roots, only TFTP menu replaced with reviewed indefinite/default-exit menu, exclusive atomic dedicated nft table creation before LAN nginx-t/start, final installed-file parser checks, two transient units capped1800seconds/no restart or reboot enablement. Original system/libvirt dnsmasq identities and masked/inactive default nginx preserved and rechecked. No node boot, installer choice or extra packet probe included.

Shutdown validates protected transaction, unique config paths, unit invocation/KillMode identity; stops only dedicated units, verifies no MainPID/reserved listeners and original process baseline/default mask, removes only unchanged recorded guard table and verifies absence. Evidence dirs and safe menu retained; changed identity/guard or partial placement blocks blind retry. Activation failure after network mutation attempts same bounded shutdown; failure remains visible. Actual LAN activation/shutdown is not yet tested. Official nft manual supports exclusive create-table failure on an existing table; composed native batch remains subject to gated installed-file check.

Offline evidence: both playbooks Ansible syntax passed, wrapper bash-n passed, full22test suite passed; added port-guard assertion cases and wrapper dispatch tests use only temporary mocks. Shutdown mocks cover success, unit/invocation mismatch, changed guard and residual listeners, with no real systemctl/nft/ss operations. Final expanded activation subset result recorded in report. No live placement, service, firewall/node changes, commit or push.

## 2026-10-30 23:37:23 onward — User-approved activation failed, read-only diagnosis

Operator explicitly approved activation at23:37:23 and executed pilot.sh activate. Supplied final recap: ok96 changed15 failed1 rescued1 ignored0, final intentional failure task says activation failed/bounded shutdown attempted. Original failing task supplied separately: Recheck original dnsmasq processes without including new pilot, activate.yml188, module nonzero return, changedfalse, no_log censored. No rerun, node boot, dnsmasq restart or additional shutdown authorized by this report.

Read-only source inspection shows final fail task follows shutdown-tasks include without ignore_errors; reaching it supports that rollback tasks/identity and absence assertions completed at that time. This is not an independent current-status check. Protected runtime/log directories exist; agent stat of active.json was permission-denied; no privilege escalation/bypass or protected log reads attempted.

Offline synthetic reproduction of the exact YAML/Jinja PID expression, using only dummy process rows and Ansible debug, produced literal backreferences rather than numbers: backslash1,backslash1,backslash1. A read-only ps invocation with that synthetic invalid PID list returned1, first error 'process ID list syntax error'. The expression over-escapes regex replacement; this explains the reported command failure without evidence of system/libvirt service changes. Proposed fix is split each process row and take its first token, with numeric PID assertions and a regression test; no code fix or live retry performed in this read-only diagnosis step.

Original Ansible module failure output was censored and not separately persisted by this playbook; terminal output is original task-failure evidence. Root config/active.json preserves baseline/session metadata, session unit-identities.json and applied-guard.json preserve accepted state, service logs are in protected log subtrees; none should be broadly dumped. Exact current status can be checked natively with systemctl show only Id/ActiveState/MainPID for both dedicated units, reserved-listener ss filter and nft list tables (table names only). No claim of current residual absence until supplied evidence. No firewall/config/service changes, commit or push.

## Subsequent local PID-query correction — no live retry/reset

Replaced the over-escaped regex replacement with split/first token extraction. New pre-network assertions reject empty/blank/nonnumeric/zero/negative/duplicate PID rows; query uses only the validated original PID list, preserving exclusion of the new pilot and exact original PID/argv equality checks. Baseline snapshots in protected native state are untouched. Captured command output remains no_log; separate assertions now show safe exit code/count or mismatch checkpoint only. Rescue saves authored failed-task name/return code and includes those in the final failure message, without argv/stdout/stderr disclosure. Shutdown baseline-query errors likewise provide a safe return code and retain the guard on failure.

Added actual Ansible-expression regression tests with synthetic multiline original processes and an extra simulated pilot: exact query tokens are110,220,221, excluding99999. Empty/invalid/duplicate inputs stop before mocked ps; simulated query-error and changed identity remain failures. Tests assert synthetic private argument text never appears in output. All command mocks affect temp files only, no native process/security state.

Current native status evidence is pending user commands. Corrected code still deliberately refuses a retry because native runtime/log roots remain, and current served menu is now reviewed rather than the original stock hash. Proposed next reset, only after status and protected metadata/hash inspection plus explicit approval: quarantine exact owned runtime/log roots via same-filesystem renames to absent held paths, preserving records; no recursive deletion or stale root reuse. A separately reviewed safe-menu retry guard adaptation would avoid restoring the stock timeout menu. No rename, cleanup, native retry, service/firewall/config change, commit or push performed in this step.

## 2026-10-30 23:42:10 UTC — User-confirmed bounded rollback status

User native output: both dedicated pilot units inactive/MainPID0; reserved listener filter69/4011/8080/20000–20009 empty; nft table listing contains only the previously present ip/ip6 filter,nat,mangle tables, no inet perkforge_pxe_pilot. This confirms absence of the pilot processes/listeners/guard within the checked scope at that time, not proof that every host property is unchanged. Node boot remains unapproved; no additional native action performed.

PID fix verification completed: five activation-focused tests passed, including exact multiline token extraction/new-pilot exclusion, all invalid/empty/duplicate rows, safe query-error/mismatch diagnostics, port guards, bounded shutdown mocks and wrapper dispatch. Both playbooks syntax and diff checks passed. Current retained-state reset and safe-menu retry adaptation remain pending explicit review; do not rerun activation yet.

## 2026-10-30 23:45:37 UTC — User-supplied retained-state metadata

Native ls output: /run/perkforge-pxe-pilot and /var/log/perkforge-pxe-pilot are root:root0711 directories; both proposed held destinations ending20261030-2337 absent. No rename yet. Together with prior status, this supports preparing a precise preservation move, not deletion or proof of mount/symlink subtree state.

Prepared local explicit retry mode: same bounded activation, numeric PID fix, default false retry selector, exact reviewed safe-menu hash required for retry versus exact original hash for first activation. Snapshot hashes/baseline files unchanged. Fresh-root refusal remains until approved quarantine. Tests exercise original/reviewed/unknown hashes in both modes, plus wrapper dispatch; no arbitrary hash acceptance. Verified installed mv help supports --no-copy and --update=none-fail for proposed same-filesystem no-overwrite moves. Proposed native read-only checks are served/original-backup sha256sum and mountpoint checks; no move/native operation executed in this preparation. No commit/push.

## 2026-10-30 23:48–23:53:09 UTC — User-approved quarantine and successful corrected activation

At23:48 operator supplied expected hashes: served reviewed menu14cf84c19eeb8844174acce28402436294e7954a083a4033fb75fde8db750f55 and original backup124ffaa1424fa839e5505c04d2c534a9cf70ca97a16d6db03fe864299164cbec; both retained source roots reported not mountpoints. Explicit quarantine approval at23:49. User native23:50:53 confirmed both preservation renames to held20261030-2337 succeeded, retaining original runtime/log evidence. No deletion or stock-menu restoration reported.

Operator then executed corrected pilot.sh retry. User recap23:53:09: ok78 changed12 failed0 rescued0 ignored0. Current code success supports hash-verified source/root copies, reviewed safe TFTP menu, successful final dnsmasq/GRUB/nft and LAN nginx-t checks, ingress-first dedicated table apply, both dedicated units active with nonzero MainPID/InvocationID at their check, preserved original dnsmasq PID/argv baseline and masked/inactive default nginx, and reserved listener presence. No rescue occurred. This is user-performed live workstation activation evidence, not an agent run and not node/firmware/router/installer acceptance.

Unit current-state/MainPID confirmation requested by parent remains pending. RuntimeMaxSec1800 is configured per unit; exact start/expiry timestamps were not supplied and are not invented. A read-only systemctl show including ActiveEnterTimestamp/RuntimeMaxUSec can establish them. Guard removal still requires explicit reviewed shutdown; timer expiry alone does not withdraw the table. Node boot remains separately gated, initial stop at indefinite GRUB. No new traffic probe, restart, timer extension or native operation performed in this journal-only update. Held logs remain preserved; no commit/push.

## 2026-10-30 23:55–23:58:38 UTC — User pause before first boot

Operator supplied dedicated-unit active status at23:55: dnsmasq MainPID1351037 and HTTP MainPID1351067; these are historical process IDs, not signal targets. Operator paused for supper and requested all docs/scripts updated in the feature branch before returning for the first boot test. Parent requested reviewed pilot.sh shutdown. At23:58:38 operator replied "Stopped"; shutdown recap and explicit listener/guard verification are still pending. Do not treat this as proof of complete cleanup or extend/restart services. No node boot reported.

Local consolidation reviews all tracked/untracked task files, removes stale planning-only status from current guides, preserves chronological failures/evidence and adds a first-boot resume handoff. It explicitly documents retained-root refusal, new absent quarantine targets (never overwrite first held attempt), ephemeral review-source checks and separate GRUB-only boot approval. Private inputs/held logs/keys are excluded. User's request authorizes a local feature-branch commit only; no push/PR/main action or native operation is part of this consolidation.

## Pause consolidation — local feature-branch verification

On docs/physical-execution-journal, reviewed every task-modified/untracked source file. Current READMEs/handoff now distinguish completed operator staging/fixture/activation from pending physical boot and pending pause cleanup verification. Historical failures, recovery and custody decisions remain chronological; old staging examples are reference-only. Added dedicated return checklist that refuses blind reactivation/held-path overwrite and stops first boot at GRUB.

Checks completed:25 PXE offline tests,18 infrastructure tests,8 evidence tests (all51 pass), nine Ansible entrypoint syntax checks, two shell scripts bash-n, packet verifier compilation, relative documentation links, diff checks and scan of task additions/new files for private IP/MAC/workstation identifiers and private-key markers. Private inputs/review snapshots are verified ignored; no keys, raw host logs or held evidence included. No native fixture/activation/shutdown, node contact, package/network/credential operation or push performed by consolidation. Local feature-branch commit is authorized; publication is not.

## Reusable entry template — not an execution record

Copy this structure for the next approved step; replace placeholders only with
actual captured facts. Do not leave a planned command looking like an execution.

```markdown
## <UTC start–finish, or explicitly uncaptured> — <step>

Purpose: <why this step was run>
Approval scope: <specific approved action and limits>
Command: <actual command; label any normalized/redacted paths>
Safe output: <reviewed excerpt; label omissions/redactions>
Exit/status: <actual status and its source, or unknown>
Provenance: <tool result, user report, or cited source; distinguish them>
Interpretation/limits: <what this proves and what remains unverified>
Next decision: <review/approval needed before continuing>
```
