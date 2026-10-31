# Historical console enrollment and successful SSH recovery

**Do not use the HTTP enroll/publish/update helpers as a normal provisioning path.**
Their attempt did not complete on the pilot; exact native socket trigger remains
unknown and the broad text guard is demonstrably overbroad. Preserve these files
and tests as evidence until the replacement is proven. Do not bypass the guard.
The successful pilot used standard ssh-copy-id and harden-ssh.sh over verified SSH.
Publication cleanup normalized trailing whitespace in the repository enrollment
copy and updated its source-checksum assertion. Journal hashes describe the
bytes actually transferred during the historical attempts; live files were not
modified and these retired helpers are not a new install path.
For tomorrow use the [readiness report](../../../infrastructure/TOMORROW-READINESS.md)
and [redesign](../../../infrastructure/PROVISIONING-REDESIGN.md), not the historical
procedure below. Neither replacement nor unattended install is approved by this note.

This narrowly scoped console bootstrap is for the approved physical pilot. Host
configuration after enrollment belongs in Ansible. Do not execute the script until
the operator approves its reviewed contents and independently verifies both
transferred files. No private key, password or backup drive participates.

Keep the installed console available. While Ethernet is disconnected, stop SSH
and inspect service/socket state and TCP22 listeners. The script also refuses an
active service, an active or enabled SSH-related socket, or an existing TCP22 listener.
Do not reconnect until those checks pass. Inspect download-tool availability at
the console; Minimal Install is not assumed to include curl.

The existing HTTP configuration permits GET/HEAD beneath `/rhel-10.2/` for the
pilot only. A root-owned `console/` subdirectory can hold `setup.sh` and `key.pub`
without changing listeners, nginx configuration or firewall rules. Copy only the
reviewed script and approved existing public key as root-owned mode0444 files;
use mode0755 for the dedicated directory. Do not alter existing media files.
The reviewed `publish-console.sh` helper performs only this native publication
when explicitly invoked with the existing public-key path. It requires root-owned,
non-symlink serving parents and a previously absent delivery directory, validates
the public key, compares both copies and displays hashes/fingerprint. On failure,
inspect retained partial files before retry; it does not delete evidence.
Publication is not performed by offline checks. Do not restart the entire pilot to publish two static files.

Record SHA-256 of the exact published script and public key through the trusted
operator conversation. Download each to a local file with curl failure checking,
never pipe HTTP into a shell. Display both downloaded hashes and compare all64
hexadecimal digits against the independently supplied values. A checksum fetched
from the same HTTP server does not establish integrity. Also compare
`ssh-keygen -lf key.pub` with the workstation's already known public fingerprint.
Stop on any mismatch. IP/MAC restrictions are spoofable; HTTP is unauthenticated.

After verification and explicit execution approval, the short invocation is:

```bash
sudo bash setup.sh key.pub <WORKSTATION_IPV4>
```

The placeholder is intentional; use the reviewed workstation address. Run through
sudo from the intended named administrator console. The script supports a normal
`/home/<operator>` account only and rejects symlinks, unsafe existing authorization
files and an existing managed drop-in. It retains all existing authorized keys;
it does not revoke unknown keys or claim the approved key is the only identity.

It enrolls the public key with0700/0600 permissions and SELinux labels, installs
`/etc/ssh/sshd_config.d/00-perkforge-console-key.conf`, validates syntax and effective
user/client-address policy, and starts SSH only after requiring public-key
authentication, disabling password/keyboard-interactive/root login and preserving
PAM. Existing earlier directives or Match rules can cause a fail-closed stop.
Host keys must already exist; none are generated. Review hostname-based Match
rules separately: the check uses the client address for host and addr.

Failure preserves the console and any partial files for inspection and attempts
to leave SSH stopped. Do not blindly rerun or delete an existing drop-in. Retain
console access until the separately approved, host-key-pinned SSH login and
password-authenticated sudo test pass. Read public host-key fingerprints at the
console; never bypass host-key checking. Remove the two public delivery files
only in a later communicated cleanup step.

Offline checks: `bash -n enroll-key.sh` and
`python3 -m unittest discover -s . -p 'test_*.py'` from this directory. Rejection
tests use dummy malformed public data only. They do not prove successful RHEL
policy integration; effective-policy validation occurs on the node before SSH
starts. No node/network/service tests run from this directory.
