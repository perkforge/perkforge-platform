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

## 2026-10-31 00:18:59 UTC — User-confirmed pause shutdown and resume preflight

User native status: both dedicated pilot units inactive/MainPID0, reserved listener filter69/4011/8080/20000–20009 empty, nft table listing only the original six ip/ip6 filter,nat,mangle tables and no inet pilot table. This verifies stopped pilot processes/listeners/guard within those checked scopes at that time; not a complete unchanged-host audit. Supper pause shutdown is now confirmed beyond the earlier word "Stopped". No first physical boot reported; control-1 still-in-setup confirmation pending.

Read-only agent metadata lookup found retained successful-attempt runtime/log roots and preserved held20261030-2337 roots; proposed new held20261031-resume-001859 destinations absent in execution view. The suffix labels this verified resume checkpoint, not an invented original service start time. Current served TFTP menu SHA256 remains14cf84c19eeb8844174acce28402436294e7954a083a4033fb75fde8db750f55. All four ephemeral review sources remain mode0600 and match the ignored activation-review snapshot. No refresh/test rerun needed; no protected process arguments or credentials read.

Proposed next native read-only checks: directory/record metadata, mountpoint status of both retained source roots, current menu and this successful attempt's original-grub.cfg backup hashes (both expected reviewed-safe hash; original DVD backup remains in first held logs), and native new-target absence confirmation. After exact quarantine/reactivation approval, preserve roots with no-copy/none-fail same-filesystem renames to new absent hold names, verify originals absent/holds present, then pilot.sh retry for the same bounded1800second services. No overwrite of first held attempt, automatic timer extension, node boot, restart or native mutation performed by this preparation. No commit/push.

## 2026-10-31 00:23:24 onward — Resumed pilot and first physical GRUB menu

Operator resumed the bounded workstation pilot; supplied recap at00:23:24 was ok78 changed12 failed0. Exact service start/expiry timestamps were not supplied. One-time F12 attempt instead reached existing WindowsOOBE. Operator explicitly approved temporary primary BootSequence Network1first around00:38, retaining reported UEFIOnly and Secure Boot settings. Subsequent network boot fetched the loader and displayed OUR indefinite GRUB menu with Exit network boot without starting installation / Start RHEL10.2 interactive installer; operator confirmed. No installer entry selected or disk write reported.

This is physical runtime evidence that the network loader/GRUB/menu chain executed under previously reported enabled Secure Boot, not measured attestation, complete firmware db/dbx/SBAT inventory or kernel/installer acceptance. Actual option93 and all request details were not independently captured in this update. Temporary firmware boot-order change is now part of the session and must be reviewed for later restoration; do not repeat the earlier blanket "no firmware changes" status as current.

Before installer selection, inspect service ActiveEnterTimestamp/RuntimeMaxUSec/current MainPID. Original1800second cap may expire around00:52 depending actual start; no exact deadline invented. Read-only installed systemd version257.13-1~deb13u1/manual and upstreamv257 source review: dbus-service.c permits RuntimeMaxUSec through its transient-property setter only when transient unit load_state==UNIT_STUB; running loaded services do not meet that condition. Therefore do not suggest an unverified live set-property RuntimeMaxSec extension. service.c computes maximum runtime from active_enter monotonic timestamp; increasing an effective cap would not reset elapsed time.

No native mutation attempted. Proposed finite option, only after explicit approval and while stopped at loaded GRUB before any installer transfer: identity-verified brief stop/start of ONLY the two dedicated pilot units using existing protected configs/guard, fresh7200second limits, preservation/update of unit invocation/lifetime records, then current-state/deadline verification. No full re-quarantine/reinstall, default-service changes, infinite cap or automatic restart. This rearm is a proposal, not implemented/executed in this update. Installer selection remains separately gated. No commit/push.

## 2026-10-31 after00:45 UTC — Explicit session lifetime choice and offline rearm preparation

Parent supplied actual current-unit start00:23:09UTC and original1800second expiry00:53:09UTC. Operator initially approved bounded two-hour rearm at00:45, then explicitly selected no runtime timeout for this pilot session with explicit shutdown/verification when done; the latter decision replaces the proposed two-hour choice. Exact later reply timestamp was not supplied. No installer/disk approval accompanies this lifetime change.

Prepared rearm.yml/rearm-units.yml and shared verify-pilot-identity.yml; shutdown uses the same extracted unchanged identity guards. Wrapper has short rearm action. Native operation remains for operator execution: protected records/config/menu/hash and unchanged guard verification, root-only unique history archive of old transaction/invocations, stop matching two units, require old names/listeners gone, recreate only those units with RuntimeMaxSec=infinity, verify fresh InvocationIDs/nonzero PIDs/actual start timestamps/unlimited property, atomically update shutdown identity and lifetime records. Original system/libvirt baseline and default mask are rechecked. Expired absent names are accepted only with trusted prior records; loaded expired-failed units are rechecked for exact old InvocationID/config/KillMode and MainPID0 before resetting only that dedicated failure state so its transient name can unload; expiry between preflight and stop is resolved through authoritative absence checks, not guessed PID signals. Guard remains untouched even on rearm failure; no media/staging/quarantine cycle.

Offline verification only: rearm/shutdown syntax and wrapper bash-n passed; timer/identity tests accept explicitly approved infinity and reject stale30minute/two-hour properties, zero PID and old InvocationID; absent-expired tests require prior records; structural checks forbid guard/media mutation. Existing activation/shutdown temporary-mock regressions rerun after extracting shared identity tasks. No native change or rearm result claimed; existing timers may expire before operator executes, which the guarded absent-unit path handles. No commit/push.

## 2026-10-31 00:53:27 UTC — User-reported no-timeout rearm completion

Operator executed reviewed pilot.sh rearm and supplied recap: ok64 changed8 unreachable0 failed0 skipped1 rescued0 ignored0. This is user-reported successful native execution, not agent-independent live-state inspection. Code success supports its protected record/config/menu checks, guard equality, archived prior records, matched dedicated-unit replacement, new invocation/timer assertions and updated shutdown ledger; the skipped task's reason was not supplied and is not invented. Parent requested separate current systemctl Id/ActiveState/MainPID/RuntimeMaxUSec output; response pending. Do not state current active/infinity status independently verified until that output arrives.

Next checkpoint only after service verification and explicit operator approval: from our indefinite GRUB menu, select the named RHEL10.2 interactive installer entry to load the kernel/initrd/Anaconda environment. Keep Secure Boot and existing scoped network controls unchanged. Stop on any signature/network/media error rather than disabling controls or choosing another path. Loading the installer does not authorize storage configuration, reclaim/delete/format, partitioning, Windows erasure, Begin Installation, subscription registration or credential/account actions. Pause at installer UI before storage changes, record screen/status, and obtain separate exact node/disk/data-loss approval later. No native action, installer selection, new code, commit or push performed by this update. Explicit shutdown and verification still required when done.

## 2026-10-31 00:54:13 UTC — User-verified current rearmed services

Native user systemctl output for the exact dedicated pilot units: dnsmasq RuntimeMaxUSec=infinity, MainPID1379037, ActiveState=active; HTTP RuntimeMaxUSec=infinity, MainPID1379067, ActiveState=active. These are observed historical PIDs, never reusable signal targets. This verifies current service state/no-runtime-limit at that timestamp, supplementing the successful rearm recap. Protected invocation records remain authoritative for shutdown. Explicit shutdown and verification are required when done.

Parent asked permission to select Start RHEL10.2 interactive installer and stop at the welcome screen, without disk selection/installation. Operator answer pending; no installer selection or further native action performed in this journal-only update. No commit/push.

## After 2026-10-31 00:54:13 UTC — Operator approved installer loading only

Parent asked: load Start RHEL10.2 interactive installer and stop at its welcome screen, no disk selection or installation yet. Operator replied "Sounds great". Parent instructed the operator to choose that named GRUB entry and report the resulting screen/errors. Exact approval timestamp was not supplied. Authorization covers kernel/initrd/interactive installer loading to welcome/language screen only; no disk selection, partitioning/reclaim/format, Begin Installation, account/credential or subscription action. Actual selection/loading outcome remains pending. No native execution, installer result, commit or push performed/claimed by this journal-only update.

## 2026-10-31 00:55:48 UTC — Operator reports dark screen after approved installer selection

Operator selected the approved interactive installer entry and reported screen staying dark around one minute later. Parent asked whether monitor has signal versus No signal, and instructed not to reboot yet. This is a symptom report, not proof of boot failure or completed installer loading. No storage action reported.

Read-only source/media metadata: current GRUB linuxefi loads /images/pxeboot/vmlinuz with ip=dhcp and HTTP inst.repo; initrdefi loads /images/pxeboot/initrd.img. Kernel16,259,888bytes; initrd222,651,716bytes. Both boot files are fetched by GRUB from TFTP before the kernel/installer uses HTTP installation tree. This substantial initrd can make transfer time material; no actual speed/ETA is inferred without logs. Config has no inst.ks/automatic storage instruction.

Agent reads of protected dnsmasq/nginx log metadata/content were permission-denied; no escalation/bypass attempted and no transfer outcome claimed inspected. Proposed single native bounded tail of dedicated dnsmasq log and nginx error/access logs, redacting IPv4/MAC text before sharing. Dnsmasq sent lines indicate completion rather than a continuous progress meter; absence of a sent line alone cannot locate a failure. HTTP requests would provide evidence of progression beyond GRUB loading. Await real log/signal evidence before diagnosing loading delay, signature/handoff or display failure. No reboot, configuration/security/network change, native command execution, commit or push.

## 2026-10-31 00:56:54 UTC — Operator reports visible boot activity

Operator said "i see boot" after the dark-screen report. Exact displayed content was not supplied. Parent instructed to let startup continue and stop at welcome/language, or report the exact error if any. This supports visible progress, not completed installer loading or absence of errors. Bounded log diagnostic remains available if progress stops; no escalation, reboot, configuration/security/network change, native log execution or storage action authorized/performed by this update. No commit/push.

## 2026-10-31 00:57:43 UTC — Operator reports installer GUI language screen

Operator reports "gui at lanuages selection". This is user-observed arrival at the RHEL installer GUI through the approved PXE/kernel/initrd loading path, not installation completion or disk selection. Parent instructed English (United States), Continue, then stop at Installation Summary and report screen without disk/Begin Installation actions. That navigation outcome remains pending.

Prepared next proposed read-only node-console inventory method, not executed: Red Hat RHEL10 console documentation specifies Ctrl+Alt+F1 for tmux, Ctrl+b then release and2 for root shell, Ctrl+Alt+F6 to return GUI. In that shell, lsblk -b -o NAME,PATH,TYPE,SIZE,MODEL,SERIAL,WWN,TRAN,FSTYPE,MOUNTPOINTS reports actual disks/partitions, exact byte sizes and identifiers without writes/mounts. Ask separate read-only inventory approval before operator runs it; preserve full identifiers privately for exact disk decision, normalize identifiers in public journal. No storage layout/default/device is selected or inferred. Source: https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/interactively_installing_rhel_from_installation_media/consoles-and-logging-during-installation . No node command, config change, disk action, commit or push performed in this update.

## 2026-10-31 around01:00 UTC — Installer shell unavailable; proposed GUI-only identity inspection

Operator reports Ctrl+Alt+F1 shows only blinking cursor; Ctrl+b then2 still no visible shell prompt. No lsblk execution reported; do not type blindly. Parent instructed Ctrl+Alt+F6 once to return GUI and is awaiting confirmation. Published RHEL10 console chapter still documents F1/tmux and F6/GUI; no verified10.2-specific replacement mapping or cause was found. Observed console behavior differs from the documented expectation and is not treated as user error.

Verified alternative from RHEL10 Anaconda source: Installation Destination builds disk overview cards with description, size/device name and serial passed as popup-info; DiskOverview widget documents that info as hover tooltip. Proposed after GUI restoration: open Installation Destination only to inspect cards, hover without clicking a disk, read model/capacity/device and available serial tooltip. Do not toggle checkmarks, choose boot device, Done/reclaim, partitioning or Begin Installation. Existing automatic/default checkmarks should be reported rather than changed. Full disk summary/bootloader is documented but includes boot-device controls, so not first choice for a view-only identity check. If tooltip/labels differ or serial absent, stop and report actual UI instead of inferring identity. Source is RHEL10 branch, not proof of exact running10.2 build behavior.

Sources: https://raw.githubusercontent.com/rhinstaller/anaconda/rhel-10/pyanaconda/ui/gui/spokes/storage.py and https://raw.githubusercontent.com/rhinstaller/anaconda/rhel-10/widgets/src/DiskOverview.c . No node command, settings/config change, disk action, commit or push performed.

## After 2026-10-31 around01:00 UTC — GUI restored and first disk candidate observed

Operator returned to GUI with Ctrl+Alt+F6 and opened Installation Destination for inspection. Parent supplied extracted screen text: PC711 NVMe SK hynix256GB, current device nvme0n1,238.47GiB,2.3MiB free; Automatic selected, encryption checkbox present but its state not established. Treat this as RHEL installer UI, not the unrelated image caption. No serial/WWN supplied yet; only-disk count confirmation pending. Card free space is unpartitioned capacity, not proof of existing filesystem file usage. Parent asked to leave Automatic/encryption unchanged while reviewing storage. No disk changes or Begin Installation reported.

Read-only repository review: no partition/filesystem/swap automation or Longhorn deployment found; configure-hosts is still a report-only scaffold. RKE2 tasks/config use normal /var/lib/rancher/rke2 state and do not implement a separate data mount or swap policy. Existing Keycloak local PV path is UNCONFIGURED, worker-targeted, not a proposed control-plane partition layout.

Engineering proposal, NOT selected/approved:600MiB EFI System partition,2GiB standard /boot,160GiB ordinary LVM XFS root including /var and /home directories, remainder roughly76GiB free inside the VG after overhead. No separate large /home or swap by default for this deliberate node baseline; no thin provisioning or Longhorn allocation yet. Free VG space can grow root or later create a reviewed data LV; XFS cannot shrink. Exact sizing is a starting proposal, not workload-capacity certification. A logical volume on this same SSD does not isolate failure or IO contention from etcd. Longhorn recommends dedicated physical storage for production; later worker/dedicated-disk design is separate, and any same-root lab use needs explicit capacity/reserve controls.

Encryption decision pending: Red Hat LUKS installer encryption requires passphrase at each boot unless separately designed/tested TPM/Clevis/NBDE unlock is configured. At-rest encryption is recommended for control-plane data, but manual console availability versus unattended recovery must be chosen explicitly. No auto-unlock/key placement/custody has been implemented on nodes; recovery must survive loss of this disk/cluster, not depend solely on services hosted inside it. Keep encryption checkbox unchanged until operator chooses.

Primary sources: RHEL10 partition recommendations (500MiB minimum/600MiB automatic EFI, /boot at least2GiB, LVM free-space/XFS limits): https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/pdf/interactively_installing_rhel_from_installation_media/index ; RKE2 state default: https://docs.rke2.io/reference/server_config ; Longhorn physical disk guidance: https://longhorn.io/docs/1.13.0/best-practices/ ; LUKS boot implications: https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/managing_storage_devices/encrypting-block-devices-by-using-luks . No live storage/security/configuration change, node command, commit or push performed.

## 2026-10-31 01:02:36 UTC — Operator confirms only displayed disk

Correction to the preceding pending-count note: when asked whether the256GB NVMe is the only disk shown, operator replied "yes" at01:02:36UTC. Only-disk confirmation is complete; serial remains unknown. Parent presented the600MiB EFI/2GiB boot/160GiB XFS root on LVM/remainder free/no separate home/no swap proposal and asked encryption preference, explaining manual reboot unlock versus separately designed automatic unlock. Encryption decision and partition/destructive approval remain pending. No new native command, storage action, commit or push.

## Subsequent operator layout decision — allocate remaining drive to root

Operator asked why not use the whole drive rather than resize later. Parent explained the simpler layout: EFI600MiB, /boot2GiB, remaining capacity as XFS root on LVM, no separate /home or swap. Operator replied "Let's do that then". This replaces the earlier160GiB-root/free-VG proposal as the selected layout concept. It is not approval to destroy Windows, delete partitions or write the disk. Encryption decision remains pending; parent asked manual passphrase unlock versus unencrypted unattended boot. Only disk count/model/capacity/device observed; serial still unknown.

Prepared manual-GUI sequence for later review, not executed: settle encryption and exact disk identity first; choose Custom on the confirmed target, open Manual Partitioning; inspect existing Windows partitions and stop before deletion planning unless separately approved; create standard EFI System partition600MiB and standard /boot2GiB, root as ordinary LVM/XFS consuming remainder (roughly236GiB less metadata/alignment), no separate home/swap, no thin provisioning. Review actual root LV capacity and VG allocation rather than assuming full VG means full root. Before accepting any Summary of Changes/Begin Installation, pause with exact planned delete/create/format actions for explicit destructive approval. Keep original existing layout untouched until that scope is approved.

RHEL10 manual partition guidance provides the Custom/Manual Partitioning and Summary of Changes review route; no UI labels beyond known documented ones are assumed from a screenshot not yet supplied. No node action, storage change, credential action, commit or push performed.

## 2026-10-31 01:07:24 UTC — Operator chooses unencrypted pilot-node installation

Parent asked disk encryption/passphrase each reboot versus unencrypted unattended boot. Operator replied "I think unencrypted, it's a home lab" at01:07:24. Recorded deliberate current pilot-node choice: unencrypted disk for unattended boot, acknowledging physical-disk data exposure. This is not a deployment-wide/IL2 policy and does not change SSH-key/backup passphrase requirements or other controls.

Parent instructed leave Encrypt my data unchecked, select Custom, click Done to open the partition editor, then stop and report listed partitions. UI navigation outcome pending. No deletion, formatting, storage-summary acceptance, Begin Installation or disk-write approval. Revised layout remains EFI600MiB + standard /boot2GiB + remaining ordinary LVM/XFS root, no separate home/swap. Next step is inspect actual listed existing partitions and serial if visible; do not invent their names/sizes or choose delete-all/autocreate before review. No node execution, storage change, commit or push performed by this journal update.

## Subsequent explicit approval — replace the identified pilot drive contents

Parent supplied extracted current manual-editor layout: EFI200MiB, BitLocker237.42GiB, NTFS859MiB; a possible Unknown entry was not fully legible. These are observed UI labels/sizes, not a complete partition inventory or serial identification. Preserve uncertainty rather than invent the missing entry.

Parent explained replacing this layout erases Windows, recovery partitions and all files on control-1's only256GB SK hynix NVMe, and asked whether all contents are disposable and replacement with the agreed RHEL layout is approved, while retaining review before installation. Operator replied "yes". This explicitly authorizes replacement/deletion planning for that drive and the agreed unencrypted EFI600MiB + /boot2GiB + remaining XFS root/LVM layout, no separate home/swap. Exact reply timestamp not supplied.

Parent instructed select the large BitLocker entry, click minus and report the confirmation dialog before confirming. Actual deletion/confirmation outcome remains pending; do not claim any partition deleted or disk written. Proposed changes still must be reviewed before starting installation. No agent native execution, storage action, commit or push performed in this journal-only update.

## 2026-10-31 01:12:01 UTC — Operator reports all old entries removed from staged plan

Operator said "k, all gone, I see 238.47" after the approved partition-removal planning. Record this as old entries removed from the installer staged layout and238.47GiB shown available, not proof that existing disk data has already been erased. Begin Installation has not occurred/reported.

Parent instructed add mount /boot/efi with600MiB desired capacity, then verify Device Type Standard Partition and File System EFI System Partition. Creation/type verification outcome pending. Remaining agreed planned mounts are /boot2GiB and all remaining capacity as ordinary LVM/XFS root, no home/swap/encryption. No agent node execution, disk action, commit or push performed.

## 2026-10-31 01:13:48–01:16:04 UTC — New staged partition entries

At01:13:48 operator confirmed /boot/efi600MiB, Device Type Standard Partition, File System EFI System Partition. At01:15:07 operator confirmed /boot2GiB, Standard Partition, XFS; Update Settings gray because displayed fields already matched. These are user-confirmed staged UI settings, not agent inspection or completed formatting.

Parent instructed add root / using remaining capacity (blank desired capacity), ordinary LVM rather than thin, XFS, unencrypted. At01:16:04 operator reported root235.89GiB. Root device type, filesystem and encryption fields were not explicitly reconfirmed in that message; do not claim independent verification. Parent instructed only if fields match, click Done to Summary of Changes and stop before Accept Changes for review. Expected plan contains only agreed old-layout removal and EFI600MiB, boot2GiB, remaining root; no separate home/swap. Summary/field verification outcome pending; no Accept Changes, Begin Installation or actual disk write reported. No agent execution, commit or push.

## 2026-10-31 up to 01:20:13 UTC — User-reported storage summary review

Parent supplied photo text confirming destruction targets on nvme0n1, PC711 SK hynix 256 GB. Operator then typed new formats "xfs and EFI System Partition" and at 01:20:13 said "I see lvmvg and lvmlv", supporting the planned filesystem types and LVM structure. These are user-reported summary observations, not independent agent verification of every field. Earlier unencrypted whole-drive choice remains the selected plan.

Parent instructed Accept Changes to save the staged plan and return to Installation Summary, not Begin Installation, and asked about Software Selection. Acceptance/navigation result is pending; no completed formatting or disk-write/installation result claimed.

Read-only software-baseline review: repository does not encode a prior installer environment selection. Recommended next choice is Minimal Install with no optional add-ons for this headless RKE2 node, subject to operator selection, not an already approved package decision. Current host preparation is scaffolding; RKE2 task only installs curl/tar/gzip before the pinned installer. Python, openssh-server/key-only access and sudo, working BaseOS/AppStream repositories, time sync and enforcing SELinux must be verified/configured before remote automation/RKE2. No assumption that a package group completes those controls.

New relevant prerequisite from current official RKE2 requirements: RHEL 10 needs kernel-modules-extra for nf_conntrack. It is not listed in the repository RKE2 prerequisite task, so subsequent approved host preparation must handle/verify it before RKE2. No package or network/firewall changes performed; NetworkManager/CNI and firewall policy remain separately reviewed. Longhorn host packages are a future storage-stage decision, not current installer add-ons. Sources: https://docs.rke2.io/install/requirements and RHEL 10 Software Selection guidance at https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/interactively_installing_rhel_over_the_network/customizing-the-system-in-the-installer . No native execution, commit or push.

## 2026-10-31 01:20:56 UTC — Return to summary; software/network observations pending

User photo shows Installation Summary after the Accept Changes instruction, consistent with returning from acceptance of the staged storage plan; no Begin Installation reported. Initial Software Selection displayed Server With GUI. Operator acknowledged the proposed headless baseline; parent instructed Minimal Install, no add-ons, Done, then read current Network & Host Name IP/hostname. Actual Minimal Install selection and network/hostname values remain pending fresh observations. Do not claim package changes, hostname configuration or installed OS.

Preserved host-preparation gap in current handoff: official RKE2 RHEL 10 prerequisite kernel-modules-extra/nf_conntrack is absent from repository prerequisite task. Verify/install it only during separately approved host preparation before RKE2; no package changes now. No native command, storage write, commit or push performed by this update.

## 2026-10-31 01:24:17 UTC — User reports hostname/time configuration done

Operator reported the pilot's reserved IPv4 and a prior Windows hostname. Public log normalizes them as <PILOT_RESERVED_IPV4> and <PRIOR_WINDOWS_HOSTNAME>; no private address/name copied. Parent instructed hostname control-1, Apply while retaining DHCP, then America/Chicago with network time enabled. Operator replied "done" at 01:24:17. This is user report, not independent address/time synchronization verification.

Parent asked readiness to create the named personal administrator with a strong console/sudo password stored privately in Proton Pass; account-creation approval/outcome pending. No password/private key collected. SSH public-key enrollment remains post-installation, separately approved.

Read-only SSH exposure review: current GRUB command omits inst.sshd. Official RHEL 10 boot-options reference says installer sshd is not started by default on x86_64 unless inst.sshd is supplied (IBM Z differs). This is documented installer behavior, not an observed port scan and not installed-OS SSH policy. Minimal Install must not be assumed key-only or service-disabled; actual installed sshd state/effective options require console verification. Repository does not yet implement SSH hardening/key enrollment.

Proposed post-install console-first plan, not executed: after package fetching/completion, separately approve a first boot with node network disconnected if avoiding any initial password-SSH exposure; use physical console/admin sudo, verify tools, install only the approved PUBLIC key with directory/file0700/0600 and correct ownership/SELinux labels, compare fingerprint, set and validate effective public-key-only SSH/password+keyboard-interactive disabled/root SSH disabled (retain PAM/account checks and OS crypto policy), then separately approve network reconnection and pinned-host-key key-only SSH/sudo test. Never use temporary password SSH or copy workstation private key. Exact commands/public-key delivery remain for later approved review; installed root console behavior is not assumed from unavailable installer tty.

Compact pre-Begin review prepared: correct single disk and agreed three mounts/no home/swap/encryption; source ready at served tree; Minimal Install confirmed; hostname/DHCP/time displayed; usable named admin with password privately saved and admin checkbox; root locked; no new security-profile/FIPS toggles; final reviewed storage actions then explicit Begin Installation approval. These are checkpoints, not claims all complete. Kernel-modules-extra and remaining host prep remain before RKE2. No native execution, storage/SSH/security change, commit or push.

Sources: https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/interactively_installing_rhel_over_the_network/boot-options-reference and https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/securing_networks/using-secure-communications-between-two-systems-with-openssh .

## 2026-10-31 01:25:35–01:26:47 UTC — Final user checks and installation initiated

At 01:25:35 operator approved finishing personal administrator creation, asking whether Done could be clicked; parent instructed Done if administrator enabled, password required and privately saved in Proton Pass. At 01:25:57 user reported root disabled. Parent asked Minimal Install, source ready, no error, personal user administrator and warning triangles; user replied "all good, no triangles" at 01:26:27. These are user-reported pre-install checks, not independent inspection. No security profile/FIPS change reported.

Under the prior explicit identified-drive replacement approval and reviewed staged layout, parent instructed Begin Installation, retain workstation PXE/HTTP services and stop before Reboot to restore disk-first boot. Operator confirms Begin Installation clicked at 01:26:47. Installation/destructive disk changes are now initiated per user; completion, success and installed-OS boot remain unobserved. Do not continue describing the layout as merely staged after this event. Parent instructed let it run and report completion/error; no reboot yet.

Read-only media inspection for SSH defaults: selected ISO contains BaseOS/Packages/openssh-server-9.9p1-23.el10_2.x86_64.rpm. Using 7z stdout, in-memory RPM header parsing, zstd stdout decompression and cpio metadata parsing, inspected only public packaged sshd configuration/service files; nothing extracted to filesystem or installed. Packaged sshd_config includes drop-ins and commented PasswordAuthentication yes, PubkeyAuthentication yes, KbdInteractiveAuthentication yes and PermitRootLogin prohibit-password; 50-redhat.conf actively sets UsePAM yes. This is not an active key-only policy and not proof of actual installed effective values or service enablement; WantedBy multi-user.target alone does not prove enabled. No real host/private keys were read. Installer x86_64 inst.sshd default remains distinct from installed OS behavior.

Safe first-boot proposal: after installation completes and before reboot, separately approve restoring installed-disk-first/one-time local boot and disconnecting only node Ethernet while console key enrollment/hardening is performed, if avoiding any first-boot password-SSH exposure. Do not unplug during package fetching. Via visible installed-console admin/sudo, enroll only approved public key with ownership/0700 directory/0600 authorized_keys/SELinux labels, verify public fingerprint, validate sshd syntax and effective user/source-specific key-only policy, keep root SSH disabled and PAM/crypto policy intact. Reconnect network and test pinned-host-key public-key-only SSH plus password-authenticated sudo only after separate approval. No temporary password SSH/ssh-copy-id bridge or workstation private-key transfer assumed. Exact commands remain for later scoped review. No native action, configuration change, commit or push performed by this update.

## 2026-10-31 01:30:56–01:31:23 UTC — Installation completion confirmed; offline first boot approved

Operator saw the Reboot button at 01:30:56. Parent explicitly asked whether installation completed successfully and requested approval to restore local-disk-first boot plus disconnect only the pilot Ethernet after completion, before checking installed SSH policy at the console. Operator replied "Yep" at 01:31:23, confirming success and approving those bounded steps. This is user confirmation, not agent inspection of installer logs.

Parent instructed disconnect pilot Ethernet, click Reboot, tap F1 and stop in firmware setup. Actual disconnection, reboot, firmware entry and boot-order restoration remain pending observations. No installed-OS login or SSH policy verification yet; no other node, disk or credential action authorized by this entry.

Prepared next-step proposal only: at a visible installed-console prompt, log in as the named administrator, verify hostname/account and inspect installed sshd state/effective authentication options without starting or reconfiguring it. Public-key delivery option is a separately reviewed spare USB containing only the existing public key, never the encrypted backup USB containing the private key. Identify media before any copy/mount; no formatting, private-key transfer, new key generation or delivery tooling implemented. Network reconnection and SSH configuration changes remain separate checkpoints. No native commands, commit or push performed by this journal update.

## 2026-10-31 01:35:13–01:36 UTC — First installed-disk login and hostname observed

Operator moved the SK hynix drive first in firmware boot order; parent instructed save/exit with Ethernet unplugged. Operator reached the installed login prompt at 01:35:13 and logged in as the named personal administrator. At approximately 01:36 UTC, operator reports hostnamectl --static returned control-1. This is user-observed evidence of installed-disk boot, console login and hostname, not an independent agent inspection.

Command reported: hostnamectl --static. Safe output: control-1. Exit status not supplied. Ethernet disconnection was approved and instructed but has not been separately verbally confirmed; do not treat it as independently verified. Parent next instructed sudo -v and systemctl is-active sshd; their outcomes remain pending. No SSH public-key enrollment, policy change, network reconnection or remote login reported. Journal-only update; no native execution, commit or push.

## 2026-10-31 — First-boot sudo and SSH policy reported

Operator confirms sudo succeeds, sshd is active, and effective passwordauthentication is yes, observed using sudo sshd -T | less. Exact observation time and exit codes were not supplied. This is user-reported installed-OS evidence, distinct from earlier packaged defaults; public-key-only policy is not yet configured or verified. Ethernet was instructed to remain disconnected; separate physical-disconnection confirmation remains absent.

The long filtered command was burdensome to type at the physical console. Prefer short commands and reviewed file delivery for subsequent approved steps. Parent asked whether a spare USB is available for the public key and a reviewed setup script, explicitly excluding the encrypted backup drive containing the private key. Answer and any enrollment/script/policy-change approval remain pending. No script or additional infrastructure created, no public key installed, no SSH policy or network change performed by this journal update. No native execution, commit or push.

## 2026-10-31 — Public-only HTTP enrollment approach approved; script prepared offline

Operator reports no spare USB and approves stopping SSH while offline, checking listeners/socket activation, reconnecting Ethernet and transferring only the public key plus a reviewed script through the existing guarded HTTP server. Files must be independently verified before execution; key-only policy must precede re-enabling SSH. Parent instructed sudo systemctl stop sshd then is-active while Ethernet remains unplugged; results are pending in this entry. No temporary password-SSH window or private-key transfer authorized.

Prepared pxe/pilot/console/enroll-key.sh and its README plus six offline rejection tests. Script validates one Ed25519 public key, named sudo operator/home, stopped SSH/no socket/listener, existing configuration/host keys and safe file types. It preserves existing authorized keys, installs the public key and a dedicated key-only drop-in, validates syntax and effective user/client-address policy including PAM and authorization-file location, then starts SSH. Failure attempts to keep SSH stopped and preserves partial files for console inspection. Existing earlier directives/Match rules may require review; host-based Match rules are not fully simulated by an address-only check. No automatic host-key generation, private-key reads, password collection or blind retry.

Offline results: bash -n passed; six unittest rejection cases passed using malformed dummy public data only; git diff --check passed. Script SHA-256 at this preparation checkpoint: f753d44d0b742fc250e41556208841a7af685905181954021e3d2aa9107c7872. Successful RHEL integration is not tested offline. A proposed root-owned read-only console subdirectory beneath the existing allowed HTTP media prefix needs no nginx/firewall change; no publication performed. Actual public-key digest must be captured on the workstation and independently compared with the downloaded file, alongside full script digest and known public-key fingerprint. Same-channel downloaded checksum files alone are insufficient. No native action, commit or push.

## 2026-10-31 01:41:28 UTC — SSH stopped and listener absence reported

Operator reports sshd.service inactive, sshd.socket inactive and no TCP22 listener from sudo ss -lntp. These are user-observed results; socket enablement has not been separately reported. Parent instructed reconnect Ethernet under the approved public-only HTTP delivery workflow, with no reboot or SSH start, then check command -v curl. Reconnection and download-tool availability remain pending. Enrollment script preflight permits an inactive, disabled socket but refuses active/activating or enabled SSH sockets and captures listener-query failures before writing. Six offline rejection tests and bash syntax check pass after this refinement; successful node integration remains untested. No native action, publication, commit or push performed here.

## 2026-10-31 — Download tool confirmed; public-only publication prepared

Operator confirms curl at /usr/bin/curl. Read-only workstation commands sha256sum, ssh-keygen -lf and stat were run against only the approved existing .pub file: regular0644,109 bytes, ED25519, fingerprint matches the previously recorded operator identity. No private key read. Personal public-key digest/fingerprint remain operator metadata, omitted from this public journal; supplied to parent for independent download verification.

Prepared console/publish-console.sh for the native operator: validates one public key and enrollment-script syntax, requires root-owned non-symlink serving parents and absent console directory, creates only that directory and two root-owned0444 public files, compares source/copies and prints hashes/fingerprint. No listeners/configuration/firewall changes or publication executed here. Both shell syntax checks and six dummy-data rejection tests pass; enrollment-script digest unchanged. Effective SSH validation, not filename order alone, gates start despite earlier Include/directive/Match precedence. User-specific home resolves from the sudo operator, without a hardcoded personal name. Await native publication output and full independent hash/fingerprint comparison before script execution. No commit or push.

## 2026-10-31 01:45:52–01:50:23 UTC — Public delivery completed and hashes compared

Operator reports native publication succeeded at 01:45:52 and downloaded both public files on the pilot. At 01:50:23 operator explicitly confirms both complete SHA-256 values match the independently supplied conversation values. Enrollment-script digest is f753d44d0b742fc250e41556208841a7af685905181954021e3d2aa9107c7872; personal public-key digest is omitted from this public journal. This is user-verified comparison, not independent agent inspection or photographic proof. No private key transferred.

Under the approved enrollment workflow parent instructed sudo bash setup.sh key.pub <WORKSTATION_IPV4>, with the actual workstation address supplied privately and correct argument spacing. Console remains open. Script execution result, effective node policy and SSH service state are pending. Do not claim enrollment success yet. Next checkpoint after success is the node console's public Ed25519 host-key fingerprint, compared against the SSH client prompt before trusting that host. No workstation connection performed, no commit or push.

## 2026-10-31 01:52:23 UTC — Enrollment did not start SSH; early-exit defect identified

Operator ran the verified enrollment script and observed the public-key fingerprint/comment but no visible error or completion line. At 01:52:23 systemctl is-active sshd returned inactive. Parent instructed no rerun and sudo sshd -t, whose result is pending here. Do not infer successful enrollment or that nothing changed solely from inactive service.

Read-only source review identifies a concrete early-exit defect: systemd v257 systemctl-list-unit-files.c returns -ENOENT when its filtered list is empty. The script's enabled-socket query was an unguarded assignment under set -e, so a legitimate empty enabled-socket set can silently exit before the mutation section and before its cleanup trap is installed. This matches reported symptoms but actual node exit location remains unconfirmed. Source: https://github.com/systemd/systemd/blob/v257/src/systemctl/systemctl-list-unit-files.c .

Prepared local correction: enumerate all unit files with an explicit failure message, then filter enabled socket entries using awk; a legitimate empty match succeeds, while enabled sockets remain subject to rejection. Two added mocked command-output regression cases verify empty-list continuation and enabled-runtime socket retention; eight total offline tests, bash syntax and diff checks pass. Revised enrollment-script SHA-256 is 2157bf7f7ef6050ec6a9608bf614adf389cc4ce8d0316d0a1a2462764fb19547. Previously published script remains unchanged on the workstation/native node; no republish, retry, service start, policy weakening, commit or push performed. Inspect partial file state before any approved replacement/retry.

## 2026-10-31 approximately 01:53 UTC — Existing SSH syntax check silent; replacement prepared

Operator reports sudo sshd -t produced no output; no explicit exit code supplied. This is consistent with syntax validation success, not evidence of enrollment or key-only authentication. Parent requested .ssh existence and SSH drop-in directory listing to establish partial state; results pending.

Prepared console/update-console.sh: requires root-owned non-symlink delivery directory, regular single-link0444 delivery files, exact originally published script hash and exact reviewed replacement hash. It atomically replaces only setup.sh and verifies key.pub hash remains unchanged; does not alter nginx/firewall/services. Shell syntax and diff checks pass. No native update, download retry, node enrollment rerun, commit or push executed. Await partial-state evidence before retry.

## 2026-10-31 approximately 01:58 UTC — Corrected script rejects SSH socket state

Operator reports bounded workstation replacement succeeded, downloaded replacement's complete2157-prefixed digest matches, and second enrollment attempt now prints the explicit active-or-enabled SSH socket stop message after the public fingerprint. At 01:58:14 operator reconfirms sshd inactive. Earlier socket inactive/noTCP22 observations do not establish disabled socket state. No second-attempt mutation section is reached when this specific preflight guard exits.

Offline reproduction against realistic unit listings: ordinary non-SSH sockets pass; enabled sshd.socket rejects even when inactive; enabled-runtime sshd-unix-local.socket also rejects. Therefore a real enabled socket is plausible; exact native unit remains unknown. Current grep searches any SSH text in active-socket listing, so a description-only false positive or non-TCP SSH socket must be distinguished rather than assumed unsafe TCP exposure. Proposed read-only native diagnostics are systemctl list-unit-files '*ssh*.socket' and systemctl list-units --all '*ssh*.socket'. No socket disabled, guard weakened, live service started, commit or push performed.

## 2026-10-31 — Pause manual console work; inspect media and test complete enrollment flow

Operator expressed frustration with prolonged manual command transcription. Parent acknowledged the burden and script defects and promised no further console commands while diagnosis continues. No new native command or publication requested by this entry.

Read-only ISO inspection used 7z stdout, in-memory RPM/cpio parsing and zstd stdout against openssh-server9.9p1-23.el10_2, systemd257-23.el10_2.1 and redhat-release10.2-17 public packages. No media mounted, package installed or payload files extracted to the filesystem. The supplied openssh-server sshd.socket has ListenStream=22, Accept=yes and Conflicts=sshd.service: it is real TCP22 socket activation, not a Unix-only socket. Inspected systemd package socket/service definitions contain no SSH Unix socket definition. Red Hat's90-default.preset enables sshd.service;99-default-disable.preset disables unmatched units, including sshd.socket absent other overrides. Packaged presets are not installed-node state and cannot establish which socket triggered the guard.

Confirmed offline design defect: searching all active-socket output for SSH text is overbroad; a description-only SSH reference rejects before writes, and a Unix-only SSH socket would also be rejected without endpoint classification. Do not conclude that this is the native cause or bypass a possibly real enabled TCP22 socket.

Added four full-flow fixture tests alongside eight prior tests. The actual Bash script body executes with only root gate/absolute paths/PATH adapted to a temporary fixture; OS service, sshd effective output and SELinux operations are mocked, public data is an RFC8032 test vector. Successful flow preserves prior authorized_keys, writes0600 authorization and expected drop-in, validates policy then records service start. Policy-failure fixture never starts SSH; real enabled TCP socket rejects before writes; description-only case reproduces overbroad rejection. All12 tests pass. This is orchestration evidence, not real RHEL/sshd/SELinux integration. Current script bytes/hash remain unchanged; no new script published or run on node.

Unresolved evidence: exact node socket unit, active/enabled state, Listen endpoints and Triggers. Any eventual diagnostic handoff should report only these short structured fields automatically for matched units, rather than requesting more long manual commands or disabling all sockets. No live change, commit or push.

## 2026-10-31 — Operator requests simpler finish; temporary password bridge pending approval

Operator asks to finish simply and permits workstation access in principle. Parent proposes a short explicitly approved password-SSH LAN exposure: verify node host fingerprint, enter the account password locally, use standard ssh-copy-id for the existing public key, verify a public-key-only login, then install/validate a small key-only drop-in and reload SSH while preserving the existing session. Specific temporary-password-exposure approval is still pending; broad access wording is not treated as blanket authorization. Console-script development stopped; no additional enrollment revision published.

No live execution, SSH start, password collected, host-key bypass, network-guard change, commit or push. Node state and installed-file state must be observed before replacing any drop-in. Keep console/current session until a fresh key-only login and sudo check succeed after hardening. Earlier media findings and12 fixture checks remain evidence with their stated limits, not proof of native socket identity.

## 2026-10-31 02:01:37 UTC — Temporary password-SSH setup window explicitly approved

Parent explicitly described starting sshd in its current configuration for a short home-LAN setup window, temporarily allowing password SSH while installing the public key and hardening authentication. Operator replied "sure" at 02:01:37. This supersedes the earlier no-password-bridge preference only for this bounded setup window; it does not authorize unrelated access or irreversible changes.

Parent instructed node sudo systemctl start sshd and ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub, followed by workstation SSH constrained to the Ed25519 host-key algorithm. Operator must compare the full host fingerprint against the console before accepting and enter the password locally. Service-start result, host fingerprint comparison and workstation login remain pending. No credentials supplied to agent and no agent connection performed.

Prepared next steps remain standard ssh-copy-id of the existing public key, independent public-key-only session verification, then reviewed key-only drop-in syntax/effective-policy validation and reload while preserving console/current session. Verify another fresh key-only login and sudo afterward. Do not conflate approval with execution or completion. Journal-only update; no native operation, commit or push.

## 2026-10-31 approximately 02:05:32 UTC — Host identity compared; connection closes before password

Operator ran a service-start command on the Debian workstation by mistake; it reported sshd.service unit not found. This did not establish a node service-start outcome. Parent clarified not to change the workstation SSH service. The subsequent workstation SSH attempt reached the pilot's Ed25519 host-key exchange. Operator manually compared the complete fingerprint against the node console, confirmed a match at 02:05:32, accepted the host and saved it in workstation known_hosts. Exact personal host fingerprint remains private operator metadata, omitted from this public journal.

The connection then closed from the pilot TCP22 before a password prompt. This proves a responding SSH endpoint/host-key exchange, not successful account authentication or usable SSH access. Parent requested one retry preferring password and disabling public-key authentication to distinguish client identity selection from server-side failure; outcome pending. Do not remove the trusted host key, weaken checking, alter workstation services or infer that authentication policy has already been hardened. If repeated, inspect bounded SSH client debug/server journal evidence before any configuration change. No agent connection, live mutation, commit or push performed.

## 2026-10-31 02:08:46 UTC — Password session reported connected; standard key installation next

Operator reports the verbose attempt completed key exchange/host identity checks, offered password authentication and now appears connected. At 02:08:46 parent instructed retaining the session and using a separate workstation terminal for ssh-copy-id of the existing public key, with password entered locally. Key-added result and an independent key-only login remain pending. No agent connection or password collection.

Prepared one stock-command contained Bash paste block in console/KEY-ONLY-PASTE.md for use only after key-only login succeeds. It refuses an existing managed drop-in, writes the small public-key-required/password+keyboard-interactive+root-disabled policy, preserves PAM/vendor crypto configuration, checks syntax and effective operator/root policy, and reloads rather than restarts SSH only after validation. A failure retains session and named file for inspection; no blind overwrite or socket change. Generic tracked placeholders require reviewed private substitution before use. Bash syntax validation passes; no node execution, commit or push.

## 2026-10-31 02:09:40 UTC — Public key added; standalone hardening prepared

Operator reports ssh-copy-id added one key at 02:09:40. Parent supplied the separate public-key-only client login command; successful key-only login remains pending. Password session remains open. No agent network access or private-key read.

Prepared console/harden-ssh.sh, the reviewed stock-command policy block as a standalone file, plus four full-flow mocked tests: valid effective policy reloads; password-policy mismatch and invalid syntax never reload; an existing managed file is preserved and rejected. All16 console tests pass, shell syntax and diff checks pass. Fixtures adapt root/path boundaries and mock sshd, SELinux and service operations; they do not establish real node policy. Transfer should use scp over the already host-verified SSH connection, followed by one short sudo bash command only after key-only login succeeds. No HTTP republication, manual checksum transcription, new framework, native execution, commit or push.

## 2026-10-31 02:10:21–02:13:22 UTC — Key-only SSH and sudo access checkpoint passed

Operator confirms independent key-only login at02:10:21. Standalone harden-ssh.sh was transferred over the host-verified SSH connection; at02:12:29 operator reports its completion message: key-only policy validated and SSH reloaded, with session retained for fresh test. This is the successful standard ssh-copy-id/hardening path, not success of the earlier rejected console enrollment script.

At02:13:22 a fresh workstation SSH command used the existing personal identity, IdentitiesOnly=yes, PreferredAuthentications=publickey, PasswordAuthentication=no and a pseudo-terminal to run sudo -v followed by hostname. Operator entered the private-key passphrase and node sudo password locally; output was control-1 and connection closed normally. No SSH account-password fallback occurred under the supplied publickey-only preference. Exit code was not separately supplied. Key-only access plus password-authenticated sudo checkpoint PASSED on user evidence; no agent connection or secret collection.

Server policy completion follows script syntax/effective operator/root checks requiring publickey, disabling password/keyboard-interactive/root SSH and preserving PAM before reload. No claim of broader RHEL/RKE2 readiness. Parent instructed workstation pilot.sh shutdown; recap/resource verification remain pending. Updated physical handoff to current installed/access state and preserved unresolved console socket-guard issue, prerequisite gap and shutdown limits. No extra user commands, live agent changes, commit or push.

## 2026-10-31 02:14:52 UTC — Operator reports successful pilot shutdown; tonight's checkpoint closed

Operator reports pilot.sh shutdown "successful" at02:14:52. Exact Ansible recap and separate native unit/listener/table probes were not supplied; record this as user-reported successful shutdown, not independent inspection of every resource. No further user commands requested tonight.

Closed checkpoint: RHEL10.2 installed and disk-first booted; personal console login, key-only SSH and password-authenticated sudo verified; effective key-only SSH policy validated/reloaded; temporary password-SSH setup window ended; temporary PXE shutdown reported successful. Workers, RKE2/Rancher/Flux and further host preparation remain unperformed. Preserve media, ignored private inputs, public delivery files and protected/held evidence until reviewed cleanup.

Next work must reduce operator burden: prepare and test consolidated provisioning with few commands before workers, rather than repeat the extended manual console sequence. Resolve host prerequisites including RHEL10 kernel-modules-extra/nf_conntrack and verify actual Ansible/Python/repository/time/network/firewall/RKE2 compatibility under separately scoped approval. Earlier console enrollment route remains unsuccessful with exact native socket trigger unresolved; do not reuse or call it validated. Documentation-only consolidation and local checks; no live action, commit or push.

## 2026-10-31 — Retrospective and simplified provisioning proposal prepared offline

Operator requests a candid retrospective and provisioning rethink: network boot, install, done, rather than prolonged manual command transcription. Reviewed actual pilot/menu/lifecycle/SSH/host-preparation source and journal failure evidence. Prepared infrastructure/PROVISIONING-RETRO-2026-10-31.md and PROVISIONING-REDESIGN.md with a standard RHEL10 Kickstart path, small Ansible-owned operator contract, explicit hardware/data-loss and credential decisions, service lifetime/resume/cleanup acceptance criteria and USB fallback. Proposal only: no Kickstart, playbook or new provisioning implementation added.

Official RHEL10 references checked for automated inst.ks boot, sshkey, stable disk targeting, script timing/error handling, local-volume/OEMDRV delivery and validator limits. The redesign refuses HTTP password/hash material and makes protected bootstrap sudo choice explicit rather than hiding a new privilege grant. It distinguishes vendor-loader acceptance from authenticated boot/config transport and requires actual install/reboot/key/sudo evidence before workers. Retrospective preserves exact confirmed bugs, unconfirmed socket/connection causes and mocked-test limitations; it does not attribute all reported eight hours to installer runtime.

Updated source entry docs to remove stale first-node-boot-pending claims and link current handoff/proposal. Node power-off was suggested but not confirmed; no current power assertion. Local Markdown/link/diff/privacy checks recorded in the accompanying report. No node access, services/network/firewall/credentials/disk operations, package installation, disposable VM run, commit or push performed for this work.

## 2026-10-31 — Additional offline preparation for tomorrow completed

Operator authorizes preparation/testing for tomorrow, not live actions. Added infrastructure/TOMORROW-READINESS.md, a non-deployable pxe/kickstart/rhel10.ks.j2 design specimen and README/static tests. Specimen has required inventory placeholders, unconditional pre-install exit1 and no active storage mutation commands, credential hash or sudo bootstrap grant; no renderer/GRUB/publication integration added. Missing disk/credential choices cannot silently produce an installer. Never use this candidate on a real node.

Expanded offline verification: full rearm task-body fixture executes real Ansible with native commands mocked and root/served paths adapted to temp files; active, expired-absent and expired-failed paths recreate only the two expected units, validate identities/lifetime, retain prior evidence and preserve guard; mismatched guard prevents recreation. Initial new test-adapter run failed because a templated argv expression was incorrectly expanded as characters; corrected the test adapter, not production lifecycle code, and reran successfully. Outer rescue/native systemd races remain outside that fixture. Added already-stopped shutdown case. Retry original/reviewed/unknown menu hashes, PID parsing and prior guard/identity/residual cases remain covered.

Console regressions now explicitly reproduce the legacy empty-filtered-systemctl silent exit and retain corrected empty-match handling plus enabled-socket and description-only false-positive cases. Exact native socket cause remains unresolved; production enrollment script unchanged and HTTP helpers marked historical, not a worker prerequisite. Full mocked success/failure tests do not become native RHEL evidence.

Final executed offline suites:32 PXE tests (91.419s),17 console tests,18 infrastructure tests,10 release-workflow checks:77 total, all passed. PXE count includes3 candidate static tests; rearm test contains4 scenarios. Ten Ansible playbooks passed syntax-check with temporary local state;6 shell scripts passed bash-n;12 Python sources passed AST parsing. Seven updated Markdown documents had balanced fences and33 existing local link targets; readiness/candidate private-identifier scan and git diff --check passed. No real namespace/service/socket/firewall fixture rerun.

Read-only ISO listing confirms openssh-server9.9p1-23.el10_2, sudo1.9.17-4.p2.el10_2, python3-3.12.13-2.el10_2 and kernel-modules-extra6.12.0-211.7.3.el10_2 package files. Presence is not dependency/group/kernel-match or host readiness proof. ksvalidator command and pykickstart Python module unavailable; no install/download attempted. QEMU/qemu-img/virt-install binaries present, but no VM created or existing trial accessed. Real RHEL10 validation/rehearsal needs appropriate tooling and separate isolated disposable-UEFI-test approval after credential/disk decisions. No node connection/power, host service/firewall/credential/disk mutation, commit or push. Additional changes remain local/uncommitted; ignored evidence/private files preserved.

## Overnight handoff — worker intent does not authorize an install

Parent reports the operator is going to sleep and wants a worker tomorrow. The parent's1–2hour allowance is explicitly unmeasured and limited to first-worker OS/access, not RKE2 or a promised duration. Updated readiness with an explicit NOT READY for unattended worker installation verdict until tooling, credential/disk decisions and complete authorized rehearsal are satisfied. No operator-driven debugging to substitute for readiness, no additional overnight user commands or live authorization. Offline preparation is complete within current scope; further real rehearsal is pending approval, not denied or attempted.

## 2026-10-31 — Current Red Hat guidance integrated as provisioning baseline

Operator requests current vendor guidance lead an easy repeatable solution. Reviewed official RHEL10 automated workflow, network repositories/PXE, Kickstart creation/generator/manual-export warning, delivery/start, command reference, script timing/validation limitations and RHEL10.2 release notes. Added infrastructure/RHEL-PROVISIONING-GUIDANCE.md mapping steps to direct sources and separating vendor behavior from Debian/nginx, existing-router proxy DHCP, scoped-LAN exposure, disk-approval and protected-credential policies. No portal login/generator submission or generated anaconda-ks.cfg read.

Concrete offline candidate changes: explicit standard url --url and timesource --ntp-server required inputs, current timezone --utc and existing network --device retained. RHEL10 removed older time/auth/source syntax;10.2 RDP/bootc additions do not justify replacing the selected headless package-mode design. Candidate remains non-deployable: unconditional pre-exit1, no active storage mutation, credential mode/disk inputs unresolved, no rendering/publication/boot integration. No sudo-password hash or private key introduced.

Simplified proposal to prefer standard persistent-disk and network selection; only add minimal pre-checks for a demonstrated gap, in line with vendor caution about unnecessary pre scripts. Replace proposed custom transaction-engine requirements with standard systemd ownership/Ansible idempotence, concise status and tested disarm/resume/stop. No existing production guard or lifecycle code weakened or modified in this integration. Native socket cause remains unknown; broken HTTP enrollment is not made a worker prerequisite.

Validation:4 current Kickstart specimen tests pass, including new source/time/network syntax-shape regression and required-input cases. Five updated Markdown documents have balanced fences and27 existing local link targets; private-identifier and diff checks pass. These are static checks, not ksvalidator or real installation evidence. Prior77-test full-suite checkpoint is retained as historical evidence; no unnecessary native/full-suite rerun. Remaining gates are disk identities, protected credential/trust choice, RHEL10 validator tooling and separately authorized complete rehearsal. No node/native service/firewall/disk/credential/VM/package operation, commit or push. Vendor guidance integration does not authorize unattended installation or select bootstrap privileges.

## 2026-10-31 — Focused PXE refactor: workstation-owned offline preparation implemented

Operator authorizes rewriting PXE source offline around current Red Hat/public guidance and accepts human power/BIOS/network-boot plus trusted physical identity/fingerprint steps. Normal provisioning must otherwise run from the workstation without node command transcription or interactive installer. Considering control-1 again is a future candidate, not disk-erasure approval; its working OS/access and evidence remain intact. No new live authority.

Implemented pxe/ansible/prepare.yml with plain local Ansible modules, nonsecret pxe/inputs.example.yml and a compact plan template. It has no facts/become/native commands/handlers/service/package tasks and no installer/apply flag. It validates basic nonsecret inputs, refuses unsafe/existing output, writes only two mode0600 review files in a new mode0700 temporary directory, and supports no-write check mode. Kickstart output is install.ks.BLOCKED with hardcoded abort/no active disk mutation even when metadata is filled; credential mode remains UNDECIDED. No new Python generator, controller daemon or framework.

Rewrote pxe/README.md as the normal entrypoint/process/boot-server guide; pilot directory is explicitly historical/recovery. Preserved all old pilot script paths, shutdown identity checks and evidence-producing tests; no native runtime/evidence moved or deleted. Broken HTTP console enrollment remains outside the normal path. Updated design/readiness/vendor map/candidate notes to distinguish implemented preparation from future install/status/stop, and manual BIOS from node command transcription.

Verified official Red Hat network overview recommends UEFI HTTP when firmware supports it, while PXE/TFTP is more widely supported. Existing pilot proves TFTP, not UEFI HTTP; no switch performed. Nginx remains appropriate for HTTP installation-source files on Debian; vendor RHEL examples differ in host packages/service commands. Satellite is a larger provisioning product, not required for this small target. Direct sources recorded in infrastructure/RHEL-PROVISIONING-GUIDANCE.md and pxe/README.md.

Executed targeted checks:4 new real-Ansible preparation tests passed (9.656s),4 current Kickstart static tests passed,6 preserved activation/retry/shutdown compatibility tests passed (25.233s), and new Ansible entrypoint syntax passed. Positive tests verify metadata reaches the blocked draft, permissions, check mode and preservation; negative fixtures prevent secret-bearing URL/private-key/newline/privilege-mode inputs from writing output. No network or native service operations occurred. Full prior77-test checkpoint remains separately recorded, not relabeled as a new full run. No node connection/power, service/firewall/disk/credential/VM/package action, commit or push.

## 2026-10-31 — Interactive LikeC4 source and ordered operations added

Operator requests zoom/drill documentation and ordered operational steps for tomorrow, separate from portal work. Added docs/architecture/model.c4 and views.c4, a source runbook HTML, pinned LikeC4 manifest/lockfile, a small explicit seven-file public documentation copier and documentation contract tests. Eight views cover context, workstation/node detail, proposed numbered operations1–7, client-driven DHCP/proxy/TFTP/HTTP sequence, planned install gates, pending credential/trust handoff and observed pilot checkpoint. Numbered steps link to actual local runbook anchors; local source links do not depend on an unpublished GitHub branch. No private network/hardware/key identifiers or secrets are in the model.

No prior LikeC4 project/toolchain found in this repository. Available Node runtime verified v24.22.2; pinned LikeC4v1.60.0 requires Node>=22.22.3. Initial public-registry npm fetch in the restricted environment failed DNS with EAI_AGAIN. A supported permissioned fetch then installed54 workspace-local dev packages with lifecycle scripts disabled; no system package/global install. User/global npm configuration was replaced with empty task-local config files to avoid credential access; cache/log writes were confined to temporary task storage. No server started.

Executed from normalized $REPO_ROOT/docs/architecture: npm run validate (syntax/semantics/layout PASS,2 model files), npm run build (all8 views laid out and static site built), and python3 -m unittest discover -s . -p 'test_*.py' (4 PASS). Initial sequence-layout warning arose from a compound actor in a separate observed view; changed that documentation interaction to the appropriate leaf role and reran cleanly. Model boot flow distinguishes initramfs runtime fetch from later Anaconda package requests; it is a protocol explanation, not a captured packet trace.

Documentation checks cover numbered1–7 operations, real runbook anchors, pinned version/loopback-only viewing command, exact allowlisted current source copies and observed/planned/private-identifier boundaries. Build contains the actual runbook and7 current source files. node_modules, dist and generated public/sources are ignored; models/runbook/tool manifest/lockfile/checks are source deliverables. Browser interaction not manually exercised and viewer remains stopped. No PNG/browser export, deployment or parked portal work.

Linked interactive docs from root/PXE/handoff/readiness entry docs. Prerequisite for viewing is Node>=22.22.3/npm and local dependencies; one repository-root command is npm --prefix docs/architecture start, which would start only a loopback documentation server when the operator chooses. This instruction is not executed or provisioning approval. Prior PXE refactor targeted14 tests and syntax checks remain recorded; unattended worker/control-1 reinstall still blocked by disk/credential/validator/rehearsal gates. No node/power/firmware/service/firewall/credential/disk/VM action, commit or push.

## 2026-10-31 — Ordered LikeC4 walkthrough clarified

Checked operator clarification that C4 must show the ordered flow. The operations dynamic view already has directional arrows numbered1–7 and links to real runbook sections; boot_protocol is a separate client-driven sequence, with installation/security_handoff drilldowns and observed_pilot kept separate. Added explicit Operator, Automation and Evidence / stop detail for every numbered stage in both views.c4 notes and public/runbook.html sections. Preparation remains the only implemented normal stage; unresolved disk/credential/rehearsal gates still stop installation. No new executable install capability or approval implied.

Added a documentation regression requiring all seven stages to carry those three fields. Re-ran pinned LikeC4 validation including layout (2 source files valid), static build (8 views laid out) and5 documentation tests (PASS). Model links resolve to local runbook anchors; viewer/server/browser interaction remains unstarted. Changes are documentation/checks only; no node/live service/credential/disk action, commit or push.

## Feature-branch publication preparation — operator requests phone review

Operator explicitly requests committing/pushing reviewed work to docs/physical-execution-journal for phone review, never main and without a PR or live operations. Reviewed all73 outgoing paths against the main-base snapshot plus working additions; no actual private addresses/MACs/fingerprints/workstation paths/provider credentials found in added content. Private inputs, node_modules, dist, generated public source copies and media remain ignored. No unrelated changes identified; the two obsolete legacy PXE deletions were previously authorized.

Publication validation passed87 offline tests:33 pilot,4 new preparation,17 console,18 infrastructure,10 release and5 documentation. LikeC4 syntax/layout/static build passed. The first staged whitespace check found one trailing space in the retired enrollment source; normalized only repository whitespace and updated its pinned source-checksum assertion, retaining historical journal hashes and untouched live files. Current repository enrollment hash33a7fb21d780a469f0a107690a37393c52465cc11cee96c2d9622b004749f5fb;17 console tests and both affected shell syntax checks passed again. Staged diff check then passed. No credential value or live security policy changed.

Remote read through the supported permissioned Git path found no existing feature ref. Commit/push verification is reported separately after execution; this entry does not presume remote success or installer readiness. No main push, PR, merge, service or node action is authorized by publication.

## 2026-10-31 12:36:21–12:36:23 UTC — Step1: worker-1 offline draft completed

Operator confirms worker-1 as the next target and reports all nodes off. This is user-reported power state, not a network/power probe. Authorized scope is documented step1 only: ignored nonsecret inputs and a fresh private draft; no live changes. Existing physical inventory's selected nonsecret worker reservation matches confirmed input. Selected controller/interface/HTTP-root/port fields in prior nonsecret pilot inputs match known context. Neither original file was modified or dumped, and no credential file was read.

Created a new ignored mode0600 input under $REPO_ROOT/.secrets/provisioning/worker-1-step1-<RUN_ID>.yml and a fresh /tmp/perkforge-pxe-plan-worker-1-<RUN_ID> output. Target hostname/NIC and prior reviewed HTTP source endpoint populate the private draft; source availability was not probed or activated. DHCP reservation/workstation reference values are private input comments, not new live configuration. Boot method and credential mode remain UNDECIDED. Exact disk stable ID/serial/capacity, bootstrap account/public key and unverified time inputs remain UNCONFIGURED; no privileged mode or credential identity selected.

Actual command, normalized from absolute workstation paths:

```sh
ansible-playbook -i localhost, -c local "$REPO_ROOT/pxe/ansible/prepare.yml" -e @"$REPO_ROOT/.secrets/provisioning/worker-1-step1-<RUN_ID>.yml"
```

Controller temporary files used a new private temporary directory and were cleaned automatically. Actual exit0; recap localhost ok10 changed3 unreachable0 failed0 skipped0 rescued0 ignored0. The three changes are only the output directory and two review files, not node changes. Output directory0700; plan.md and install.ks.BLOCKED regular files0600; input0600 and Git-ignore status verified. Exactly those two output files exist. Plan is BLOCKED / NOT DEPLOYABLE; candidate retains unconditional pre-exit1 and has no active storage/erase/reboot commands. This is not ksvalidator or real installation evidence.

Step1 completion gate PASSED: both private review files and their blocked status are available for operator review. Next exact index/C4 heading is "2. Review exact plan; STOP before approval". Missing disk/credential/trust/rehearsal gates block progression, not creation of the draft. No node/network/service/firewall/VM/credential/disk operation, commit or push. Existing input/output/evidence files preserved.

Operator hard stop:09:30CT on2026-10-31 (14:30UTC), with wrap-up14:15UTC. Current clock checked12:36:32UTC; this bounded offline operation finished in approximately2seconds. Do not start later work that cannot finish safely before the stop, and do not use a mid-install service cutoff as a substitute for scheduling.

## 2026-10-31 12:43:38 UTC — Step1 local working-directory review copy

Operator asks for the plan to be discoverable in the local working directory. Created a new ignored .secrets/provisioning/worker-1-review directory in this feature worktree; preserved the original input and canonical /tmp outputs. Copied plan.md and install.ks.BLOCKED byte-for-byte and added a private README recording source run, canonical output path, copy time and SHA256 values. Directory0700, all3files0600, regular/non-symlink and Git-ignore checks passed; both source/copy byte comparisons passed. No existing review directory or file overwritten.

Canonical generated output remains /tmp/perkforge-pxe-plan-worker-1-<RUN_ID>; local plan is .secrets/provisioning/worker-1-review/plan.md. This is a static review snapshot, not an automatic refresh or an input/installation path. New inputs require a new render and reviewed snapshot with provenance; do not confuse an old copy with a newer run. Updated preparation documentation to explain that distinction without changing renderer/deployment semantics or adding a helper framework.

Step1 remains BLOCKED / NOT DEPLOYABLE, with original candidate abort and unknown decisions intact. No node/network/service/firewall/VM/credential/disk operation, commit or push. Hard-stop timing remains unchanged.

## 2026-10-31 12:46:00 UTC — Review discoverability corrected to pxe/local

Operator wants generated PXE review files beside the PXE work, without jumping to a folder named secrets. Checked pxe/local and pxe/local/worker-1 absent, then added /pxe/local/ ignore rule before copying. Created protected pxe/local/worker-1/plan.md and install.ks.BLOCKED from the original canonical run, plus a provenance README with source run/path/time/hashes and separate private-input pointer. Plan/candidate byte comparisons passed; directories0700, files0600, regular/non-symlink and all Git-ignored. Original /tmp outputs, private input and earlier review copies remain untouched.

The current preferred review path is pxe/local/worker-1/plan.md; the previous .secrets review location is historical, not the user workflow. Updated preparation docs to use only the preferred local path and explain canonical render versus static review snapshot, with no renderer or deployment change. Status remains BLOCKED / NOT DEPLOYABLE. No node/network/service/firewall/VM/credential/disk action, commit or push. Existing timing/approval boundaries remain in force.

## 2026-10-31 12:51:56 UTC — Redundant review folder moved to recoverable Trash; recovery gap recorded

Scoped cleanup only: verified .secrets/provisioning/worker-1-review contained exactly plan.md, install.ks.BLOCKED and README.md, all regular/non-symlink. Its plan/candidate matched preferred pxe/local/worker-1 byte-for-byte. Preserved the exact earlier README as preferred-location earlier-review-provenance.md, mode0600/Git-ignored, retaining the original copy timestamp as well as run/path/hashes.

Used supported native gio trash for that exact duplicate directory only. Exit0; old path absent. Matching desktop Trash origin metadata and retained payload were verified; plan/candidate in Trash match the preferred copies. No permanent deletion, broad cleanup, private-input move or unrelated secret-value inspection. Every other .secrets content remains untouched; the per-run input remains needed for regeneration and existing private controller inputs/evidence were not removed. Preferred review path stays pxe/local/worker-1/plan.md.

Operator asks how regeneration works without committing generated plans. Existing tracked artifacts are pxe/ansible/prepare.yml, pxe/inputs.example.yml and pxe/kickstart/rhel10.ks.j2; actual per-run inputs are private, while current local provenance records output hashes/run/path. LikeC4 has a package lock, not a full provisioning-toolchain pin. Explicitly recorded unverified backup of the new worker input, incomplete revision/tool/input manifest capture and missing restore/regeneration exercise as readiness/recovery follow-ups. Earlier SSH-key backup must not be extrapolated to this new input. No backup/upload, restore, regeneration test or credential action performed; no deterministic-reproduction claim. No live provisioning, commit or push; hard stop remains09:30CT.

## 2026-10-31 — Step 2 bootstrap design and canonical local workspace

Operator accepted draft content and approved temporary key-only bootstrap DESIGN
for offline implementation/rehearsal planning only. This is not installation,
erasure, actual credential creation or root privilege execution approval. Design
explicitly proposes root-equivalent NOPASSWD sudo during handoff, fresh verified
human key login/password-sudo before revocation, and outstanding-access reporting
on failure. No grant/key/account created. Installed-host transition remains
unimplemented and untested; planner selection is not a security implementation.

Operator requested working files under pxe/local, not .secrets. Canonical current
nonsecret worker input is pxe/local/worker-1/inputs.yml; new run output goes to
runs/<RUN_ID>/ with protected plan/candidate snapshots at the node directory top.
Shared nonsecret work belongs under pxe/local/. All ignored, directories0700,
files0600. Earlier snapshots/input preserved byte-for-byte in initial-run evidence;
original /tmp outputs preserved. Only the now-obsolete task-created .secrets worker
input was moved using supported gio trash after exact historical preservation and
unchanged metadata comparison. Existing pilot inputs and hash-review record stay
in .secrets for reviewed recovery/shutdown; no credentials migrated or deleted.

Actual offline render at13:00:02UTC used:

```sh
ansible-playbook -i localhost, -c local pxe/ansible/prepare.yml -e @pxe/local/worker-1/inputs.yml
```

Exit0; ok11 changed3 unreachable0 failed0 skipped0 rescued0 ignored0. Changes were
new run directory and two inert files. Plan now records selected bootstrap design;
disk/identity/credential material unresolved, candidate always exits1, no active
storage directives. Local run evidence records tool versions and dirty-source
checksums plus input/output hashes; snapshots match. Earlier metadata version query
attempted default home Ansible temp and failed read-only after successful render;
completed metadata with protected local temp without repeating that render.

Added bounded isolated installer rehearsal proposal:4vCPU/8GiB,64GiB target plus
1GiB canary, no uplink or preserved trial, disposable test credentials requiring
separate approval, complete handoff/revocation/failure/cleanup proof. Not executable
or rehearsed yet;2–3hour allowance unmeasured and unsuitable before today's hard
stop. No VM, service, socket, firewall, node or actual security action occurred.
New input backup/restore-regeneration remains unverified.

## 2026-10-31 13:16 UTC — Bootstrap Ansible component checkpoint

Operator reviewed bootstrap README/rehearsal proposal and accepted their content;
no VM/credential/security execution approval inferred. Continued offline code work
under prior authorization. Added standard Ansible role defaults, SSH/sudo templates
and setup/handoff/fresh-controller-verification/revocation task components under
pxe/bootstrap/. No deploy playbook/installer adapter invokes them; apply defaults
false. The physical Kickstart remains unconditionally blocked.

Setup requires stopped exact SSH service/socket, rejects enabled exact socket,
existing account/home/policy and existing setup ledger; validates public key,
visudo fragment, SSH syntax/effective account+root context and SELinux labeling.
Handoff configures separate human key/password-sudo using protected runtime inputs.
Revoke requires human administration channel and fresh human key/password-sudo
proof before removing only matching key/grant, expiring account and checking its
remaining processes. Negative bootstrap authentication plus positive retained
human access are required before revoked state. Generic timeout never proves
revocation. Intent ledger precedes privileges; failures/interruption remain
outstanding/unknown. No password/hash written into served artifacts or plans.

Executed actual Ansible task bodies in temporary fixtures only; account/getent,
service/SSH/syntax/SELinux/process tools mocked.11 tests passed in160.089seconds.
Includes full positive sequence and failures for policy/sudo/public key, existing
account, active/enabled SSH, unavailable/passwordless human access, modified grant,
timeout, residual process, controller interruption and final access failure.
Tests exposed/corrected a residual-process failure-condition bug: explicit final
assertion now prevents falsely marking cleanup complete. Remote sudo shell command
also executed against a fixture sudo for quoting/password-required behavior.
No real credentials/accounts, SSH/network/service/firewall or VM actions occurred.
Role syntax/YAML,6 documentation tests, link/privacy checks and diff checks passed.

Updated LikeC4 security_handoff and ordered-operation notes with actual task links,
controller versus target locations, order/verification/revocation and integration
limits. Model and static build validated without starting viewer. Shared local
readiness report is pxe/local/readiness.md (ignored0600). Canonical worker inputs,
plan and preserved runs remain under pxe/local/worker-1; no credential migration.

Ready-to-start verdict remains NO. Initial Kickstart policy adapter, disk/install/
service lifecycle, runtime secret/controller handoff, RHEL validator and native
rehearsal are missing. Role setup is not a working Anaconda chroot hook; do not
send it to a node console. No honest promise of complete rehearsal readiness in
one hour.2–3hour rehearsal allowance is unmeasured and follows implementation and
separate approval.14:15UTC wrap/14:30UTC stop unchanged; no commit/push performed.

## 2026-10-31 13:50 UTC — Initial adapters and workstation access caller

Continued authorized offline engineering. Added Ansible-owned standard Kickstart
bootstrap-post.ks.j2 and storage.ks.j2, rendered behind unchanged unconditional
physical pre-abort. Post adapter checks standard user/sshkey results, shared SSH/
sudo policy, intent ledger, public key, labels and SSH/sudo syntax/effective
policy. Default sshd disabled; successful final enable uses systemctl --root=/
offline unit links only. Host-key creation exists as future target code, mocked
in tests; no real keys generated. Error path attempts disable, halts installer
and retains outstanding/unknown state, never assumes rollback succeeded.

Storage adapter uses one exact disk/by-id selector plus read-only disk type,
serial and exact byte-capacity checks, then standard scoped Anaconda directives.
Unresolved identity/layout instead emits abort/no storage directives. Synthetic
file tests leave target/canary hashes unchanged; not real block-device proof.
Physical erasure remains unapproved and impossible through current pre-abort.

Added default-off pxe/bootstrap/handoff.yml workstation caller and nonsecret
access.example.yml. It stops before prompt/lookups/node contact without explicit
reviewed access flag. Future execution prompts privately on workstation, uses
bootstrap SSH then a separate human SSH/become alias; target PAM chpasswd gets
password via protected stdin/no_log rather than controller hash/dependency or
HTTP/CLI values. Known-host trust is independently supplied, never auto-accepted.
Nothing contacted nodes or read real credential values during this engineering.

23 component/adapter/storage/controller fixture tests passed in179.086seconds,
including actual post-adapter output bridged into human handoff/revocation and
complete controller connection-transition flow. Accounts/security tools/SSH/PAM/
unit links/host keys are mocked; temp files only. Subsequent adapter simplification
removed external cmp dependency in favor of Bash comparison;5 adapter tests and
full controller-caller positive test passed again.6 preparation tests and4 base
candidate tests passed, plus Ansible syntax/YAML/Python,6 architecture checks and
LikeC4 model/build. Viewing/network servers were not started.

Actual current private render at13:49:40UTC: ok12 changed3 unreachable0 failed0
skipped0 rescued0 ignored0, exit0, new directory plus two inert files only:

```sh
ansible-playbook -i localhost, -c local pxe/ansible/prepare.yml -e @pxe/local/worker-1/inputs.yml
```

Current plan snapshots match preserved pxe/local/worker-1/runs/<RUN_ID>; exact
inputs and8recipe source/input/output hashes are protected beside the run. Added
known source-controller address from existing reviewed nonsecret input; storage
layout/disk/credential material remain unresolved. Older runs/inputs preserved;
new input backup and restore/regeneration remain unverified.

User removed the earlier hard stop and reiterated worker OS+SSH/sudo only, with
RKE2/Rancher separate. No live permission inferred. User declined optional activity
log; no separate activity log added. This remains the standing execution journal.
Next pending tooling authorization: hash-pinned upstream pykickstart3.78 source
under pxe/local/tools (RHEL10 handler verified upstream; requests already present),
no system package/global changes needed. No archive download/setup/tool execution
attempted. Install/session/reboot/disarm/resume/cleanup runner and real isolated
rehearsal remain engineering/validation blockers; worker disk/erasure/trust and
actual test credentials/VM/network execution require separate approval. No commit
or push. Existing control node, pilot state/evidence and unrelated files preserved.

## 2026-10-31 — Simplified worker pilot and focused directory consolidation

Operator agreed controlled physical worker-1 pilot instead of mandatory full VM
rehearsal, then explicitly requested focused cleanup/status updates. No live node,
network service, credential generation or disk action authorized. Keep standard
Kickstart, proven PXE and short access handoff with physical host-fingerprint/private
workstation-password checkpoint. Broad provisioning refactor is deferred until
worker-1 RHEL/access succeeds; RKE2/Rancher remain separate.

Active entry is pxe/README.md and current private folder pxe/local/worker-1/.
Moved superseded staging/activation/packet proposals, retired console helper/test
directory and unfinished custom VM runner into tracked pxe/pilot/history/.
Public archived code contains no private inputs or credentials. Proven pilot
activation/shutdown/rearm/packet executable code stayed in place and is unchanged
against HEAD; retired console shell scripts remain byte-for-byte identical.
Relative documentation links and staging-test source reference were updated.
Original command paths in historical records were retained as execution provenance.
The failed runner fixture is explicitly parked/skipped, not a passed rehearsal.
Its original failure was memory-parsing before resource creation; no resources ran.

Private old worker runs, synthetic validator artifacts and controller temporary
folders moved only into ignored pxe/local/history/. One current run remains in
worker-1/runs/ with the canonical input/current plan/candidate at the folder top.
No private file moved into tracked history. No permanent evidence deletion,
credential migration, .secrets recovery-snapshot deletion, commit or push.
Local directories0700/files0600 and Git-ignore checks passed.

Current worker render at14:38:15UTC: exit0, ok12 changed3 unreachable0 failed0,
skipped0 rescued0 ignored0. Only new run directory and two inert review files
were generated; snapshots match that preserved run. Exact disk/layout, initial
account/public key and time/boot fields remain unresolved. Actual target-specific
install file/service scope still needs review; default candidate always aborts.

Validation:6 preparation,33 proven pilot and17 retained console tests passed;
23 bootstrap/adapter/access tests passed in181.603seconds. Current fully populated
synthetic candidate again passed the approved local pykickstart RHEL10 validator,
exit0.6 architecture checks, model/build, active links, source identity and diff
checks passed. These are offline/parser/fixture results, not native worker install
or VM success. All physical nodes remain off per prior operator report.

Next gate is approved read-only worker disk discovery and remaining metadata,
then actual file checks and one exact worker service/install/access approval.
No install-duration promise is made before that evidence. Cleanup/check work is
complete; avoid inventing further framework prerequisites.

Focused cleanup completion:5 ignored, regenerable Python cache directories under
PXE source/tests were verified to contain only owned .pyc files, then moved with
supported gio trash to recoverable desktop Trash (exit0; source absence verified).
No source, credentials or unique execution evidence were trashed. No live action.

## Worker-1 firmware observation — user report, timestamp not captured

The operator reports the Primary Boot Sequence lists the local drive first and
Automatic Boot Sequence lists network first. The instruction was to leave both
unchanged. No firmware settings were changed by the assistant. Which sequence
will govern the next boot is unverified; no firmware semantics are inferred.
Before installation, review disk-first boot and disarm installation delivery
before reboot so either boot path cannot silently repeat installation. This is
an observation, not worker boot, service, installation or wipe approval.
Worker-only discovery activation and proposed manual-stop lifetime remain pending.

## Worker-1 discovery activation authorized — execution result pending

The operator explicitly approved worker-only discovery services with no runtime
limit, followed by explicit manual shutdown. The parent supplied this command to
run from the worktree:

```bash
bash pxe/local/worker-1/discovery/start.sh approved
```

This is authorization and a supplied command, not an execution record. Native
output is pending. The assistant did not execute a second copy. Scope is the
reviewed worker-only temporary PXE/file services and evidence preservation;
installer selection, installation and disk erasure are not approved by this
activation. The indefinite interactive menu has no Kickstart. Existing control-1
and worker-2 are excluded. Approval timestamp was not independently captured.

## Discovery output lookup — partial filesystem evidence only

Read-only inspection found both exact held-worker-discovery runtime/log directories
present and original runtime/log paths absent. No Ansible process was visible in
the execution environment. These observations show retained roots were moved, but
do not establish native activation success, failure cause or complete resource
state. The launcher had no output-file capture; no current transcript was found
in its private working directory. Terminal history and credentials were not read.

A prospective launcher change now sets a unique mode0600 private Ansible log
under the ignored discovery directory. It was syntax checked, not executed. This
cannot recover the previous terminal output and does not authorize a retry.
Native terminal output still needs a bounded export to an accessible private file
for the assistant to inspect; no activation rerun is appropriate merely for logs.

## Worker discovery attempt stopped at media read-only preflight

Operator supplied one final terminal excerpt: media_checks found the old public
console directory writable; recap ok35 changed1 unreachable0 failed1 rescued0.
The failure is before activation placement/guard/start tasks, not a failed node
installation. Read-only inspection confirms the directory mode0755, two regular
mode0444 files setup.sh and key.pub, and no other writable entry in the serving
tree. File hashes match known public delivery artifacts. Projected ownership is
nobody:nogroup; native owner identity must be checked by the launcher, not inferred.
Original runtime/log roots are absent; exact held-worker-discovery roots exist.

Prepared, not executed: an explicit opt-in correction of only that directory to
0555, preserving file bytes/owners and the read-only assertion. Retry recognizes
only the fully fresh or fully already-held state; partial/mixed states stop.
Future runs automatically save private Ansible output and an exit-status summary;
password input is not recorded. Permission correction/retry approval remains
pending. Offline syntax,16 state combinations and a temporary-directory Ansible
permission fixture passed. No native chmod, service start, firewall or node action.

## Approved console mode correction and discovery retry — failed, rollback passed

Operator approved only the known public console directory0755 to0555 correction
and the previously reviewed worker-only discovery retry, with manual-stop service
lifetime. Assistant read the automatically saved private Ansible log and summary;
no second activation was executed or terminal output requested.

Captured summary exit2; recap ok115 changed14 unreachable0 failed1 skipped6
rescued1 ignored0. Read-only media checks passed after correction. Both transient
units were launched with RuntimeMaxSec=0, then reported failed/MainPID0 and SIGTERM
at their start times; the active-state assertion failed. The intended unlimited
lifetime was not achieved. This differs from the existing rearm's explicit
infinity value; investigate this launch-argument defect before retry.

Rollback completed its assertions: pilot units/processes/listeners gone, recorded
guard absent, original system/libvirt/default nginx preserved within those checks.
Runtime/log records remain. This is captured native playbook evidence, not an
independent current-state probe or proof of all host state. No worker boot,
installer selection or disk write occurred through this command. No retry made.

## Unlimited launch correction prepared — no native retry executed

Corrected activation argv to use explicit RuntimeMaxSec=infinity for the approved
manual-stop choice; the default1800-second path remains unchanged and unlimited
still requires explicit approval. Activation now captures and checks the actual
RuntimeMaxUSec property. A regression renders both actual systemd-run argv arrays
for bounded/unlimited inputs and exercises the approval matrix.

Prepared next retry preserves the exact failed transaction only after protected
record config-path/unit/hash verification, stopped-unit/listener/guard checks,
non-symlink root ownership and non-mountpoint checks. New held destinations use
an attempt2 suffix and must not exist. Previous held roots and private output
logs are not overwritten. Native protected transaction inspection was denied to
the assistant; verification is performed by the approved native Ansible launcher,
not bypassed. No native retry occurred during preparation.

## 2026-10-31 15:41:44 UTC completion — worker discovery recovery and activation

Operator confirmed resumption after relaunch. Scope: exact failed workstation
PXE discovery recovery and worker-only discovery activation, unlimited until
explicit shutdown; no worker boot, installation, disk or credential change.

The native launcher ran the local discovery start wrapper with `approved` in a
visible terminal; the operator supplied sudo input directly. Protected transaction
path/unit/hash/lifetime checks and both exact failed invocation identities with
PID0 passed before resetting only those two failed unit states. Both transient
units verified unloaded/stopped. Prior runtime/log roots were preserved under
fresh attempt2 held names without overwriting earlier evidence. Read-only media,
reviewed configuration, guard, listener and existing-service checks passed.

Native Ansible result: exit0, ok107 changed14 unreachable0 failed0 skipped7
rescued0 ignored0. Automatic private log and bounded summary remain in the ignored
worker discovery workspace. A separate approved native systemctl query confirmed
both dedicated services active with RuntimeMaxUSec=infinity. This is workstation
discovery availability, not evidence of worker PXE acceptance or installation.
Explicit reviewed shutdown remains required before leaving the discovery session.

Offline validation: eight existing activation tests and five local recovery
scenarios passed (success, invocation mismatch, running PID, transaction mismatch,
and unload failure); Ansible/shell syntax and diff whitespace checks passed.
The local recovery is deliberately specific to the retained failed transaction;
do not rerun the wrapper against the active session. Worker disk identity and
installation/data-loss approval remain outstanding. Control-1 and platform
provisioning were untouched.

## 2026-10-31 — worker-1 PXE menu acceptance (operator report)

Operator approved network boot to the menu only. The prior one-time interrupt
route had been unreliable; the approved alternative used Startup / Primary Boot
Sequence temporarily network-first, with disk-first restoration required when
discovery ends. Operator then reported media-presence checking followed by GRUB
with the RHEL10.2 interactive installer entry available. This establishes reported
worker PXE menu acceptance, not installer execution, disk identity or installation.
No installer selection is approved. Exact worker disk identity and installation/
data-loss approval remain outstanding. C4/runbook now reflect this boot route,
observed checkpoint and restoration obligation. Event time was not captured.

## 2026-10-31 — worker interactive inspection and specific data-loss approval

After separate approval to start the interactive installer for inspection,
operator reached the welcome/summary/storage screens and reported one internal
WDC SN520 of238.47GiB at nvme0n1. Serial/persistent ID/exact bytes were not
obtained; console shortcut attempts were unsuccessful. Operator then explicitly
confirmed this sole worker drive's existing data is disposable for RHEL. This is
worker-specific approval; the historical control-1 approval was not reused.
No disk changes, Begin Installation or completed worker install are reported.
Next review the proposed interactive layout; do not weaken automated persistent-
disk guards or claim unattended validation. Preserve control-1. Temporary BIOS
network-first selection must be restored to disk-first before normal local boot.
Event time was not captured. Evidence is operator report, not a native disk probe.

## 2026-10-31 — worker-1 interactive layout/account review ready

Operator reports deleting prior Windows partitions in the pending custom layout,
adding600MiB standard EFI,2GiB standard XFS /boot and remaining XFS LVM root, then
confirms the change summary affects only nvme0n1. No separate home/swap or disk
encryption was proposed. Operator accepted the same account approach as control-1,
left root disabled, and entered their user/password locally. The subsequent check
of administrator/password requirement, Minimal Install and hostname worker-1 with
wired networking was acknowledged done. No passwords were requested or collected.
Begin Installation is the next authorized worker-only step; start/completion and
actual resulting disk layout remain unobserved. Preserve PXE/source availability
while installation is active; restore disk-first before normal local boot.

## 2026-10-31 — worker-1 installation underway (operator report)

After the scoped Begin Installation instruction, operator reports installation
underway. This is reported installation start, not observed completion or verified
resulting storage/access. Keep workstation source/PXE available throughout install.
Pause before reboot to restore disk-first boot; no service shutdown is implied.
Event time was not captured.

## 2026-10-31 — worker-1 local login and hostname (operator report)

Operator reported installation ready to reboot, restored disk above network in
Primary Boot Sequence and restarted, but PXE was attempted again. Automatic Boot
Sequence was left unchanged. After disconnecting Ethernet and rebooting, operator
reached installed RHEL login, then logged in and reported `hostname` = `worker-1`.
Ethernet reconnection was instructed but actual link/address is not yet verified.
This establishes reported local OS boot/login, not persistent connected disk-first
behavior, resulting layout, sudo, SSH/key-only access or cluster readiness. Boot
selection remains unresolved; do not silently disable or change another sequence.
Workstation services remain active pending explicit shutdown. Event time uncaptured.

## 2026-10-31 16:21:56 UTC completion — worker-1 SSH/key-only/sudo handoff

Operator confirmed the expected LAN address and password-sudo from console, then
explicitly approved worker-only host-trust/public-key/key-only/sudo handoff for
corey. Native scan was not trusted until operator confirmed the complete Ed25519
fingerprint against the physical console. The same existing public key used for
control-1 was enrolled through standard ssh-copy-id in a visible local terminal.
A separate fresh public-key-only connection confirmed hostname/user and captured
private read-only storage/mount evidence: expected600MiB EFI,2GiB XFS /boot and
remaining XFS LVM root. No serial/private key/password value was collected.

The retained tested policy helper was transferred and SHA256 checked before
sudo execution. It validated SSH syntax/effective policy then reloaded SSH.
Final separate key-only login succeeded; invalidated sudo credentials rejected
noninteractive privilege before local password authentication succeeded and the
privileged hostname matched worker-1. Root/password/keyboard-interactive SSH are
disabled by the checked policy; PAM/password-authenticated sudo retained.

Native local wrapper summary: exit0, final stage complete. Private step-result
logs and inspection files are retained in the ignored worker access workspace;
terminal/password input was not recorded. Repeated existing-key passphrase prompts
came from distinct non-multiplexed connections. Four existing policy fixtures and
five local handoff orchestration scenarios passed; fixtures are not native proof.
Operator separately reported successful completion. Persistent connected disk-first
boot remains unresolved. Workstation PXE services remain running; exact logged
shutdown wrapper prepared/syntax-checked, awaiting explicit shutdown authorization.
No cluster/other-node changes or commit/push occurred.

## 2026-10-31 16:24:13 UTC — workstation PXE shutdown verified

Operator explicitly requested stopping the worker-1 workstation PXE session.
The prepared local stop wrapper invoked existing shutdown.yml in a visible local
terminal with direct workstation sudo input and automatic private Ansible logging.
Native result: exit0, ok33 changed2 unreachable0 failed0 skipped0 rescued0 ignored0.
Transaction/config and recorded unit invocation identities were checked before
stopping dedicated units; dedicated processes/listeners were verified gone,
original system/libvirt/default nginx preserved, and the unchanged recorded guard
removed and verified absent. Runtime/log records, staged media, indefinite menu
and held failed-run evidence were retained. No node shutdown or unrelated-service
change was performed. Private log/summary remain in the ignored worker discovery
workspace. Worker-2 requires its own reviewed client identity/configuration and
activation approval; this shutdown does not retarget services.

Timestamp note: this shutdown's native Ansible log11:24:13 is America/Chicago
(CDT, UTC−05), hence16:24:13UTC. The earlier activation log10:41:44 was likewise
local time, converted to15:41:44UTC in the activation entry. Shell access logs
used explicit UTC timestamps and are unaffected.

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
