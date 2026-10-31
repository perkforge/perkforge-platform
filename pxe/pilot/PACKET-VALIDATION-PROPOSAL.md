# Bounded isolated packet check — native evidence recorded

Purpose: test the installed dnsmasq2.91 proxy behavior and rendered ingress/HTTP
controls without attaching any fixture interface to the household LAN. This is
workstation-only temporary network setup and packet generation, not node boot.
Operator native run completed all four PASS phases and namespace cleanup ABSENT.
See the execution journal for provenance. Future runs still require approval.

## Installed tools and exact bounded scope

Available: `/usr/bin/ip`, `/usr/sbin/dnsmasq`, `/usr/sbin/nginx`, `/usr/sbin/nft`,
Python3 standard library, curl, timeout and BusyBox udhcpc/tftp. Scapy, tcpdump,
tshark and dhclient are absent from the inspected execution view. No package
installation is required: a small Python **verification-only** helper can encode
DHCP/PXE messages and capture matching replies with AF_PACKET. Ansible/YAML owns
fixture configuration/lifecycle. Packet helper must be reviewed/offline-tested
before native execution. The prepared files and completed operator-run limits are described below.

Reviewed operation in the Ansible entrypoint; future execution requires approval:

1. Require both namespace names `pfpxe-s` and `pfpxe-c` absent. Create only those
   two namespaces and a veth pair, move BOTH ends into them, name server end
   `fixture0`, client end `client0`. No bridge, physical NIC, host IP, host route,
   forwarding/sysctl or household interface changes. No link remains in the host
   namespace. Configure documentation subnet192.0.2.0/24 only inside namespaces:
   server.10, pilot.11, negative HTTP/TFTP source.12, synthetic MACs only.
2. Create a unique root-protected temp directory containing reviewed fixture
   configs and a harmless `public-fixture.txt`; use no ISO, real config, secrets
   or node identifiers. Render through the existing Jinja templates with synthetic
   vars. Template configuration remains Ansible-owned; Python does not generate it.
3. Start foreground dnsmasq and nginx only inside `pfpxe-s`, bounded by one supervised
   invocation. Record exact child PID/argv; no persistent units or default service
   changes. PhaseA has NO nft guards, so the daemon's own MAC/architecture filters
   are actually tested rather than hidden behind firewall drops.
4. Use client-side raw frames to send DHCPDISCOVER from0.0.0.0:68 to broadcast:67
   with synthetic pilot MAC, PXEClient class, option93=7 and unique transaction ID.
   Capture matching replies and assert proxy offer contains boot information but
   yiaddr=0 (does not allocate a lease). Separately send protocol-correct PXE
   boot-service DHCPREQUEST to UDP4011, including PXE vendor boot-item option and
   matching service type; assert the expected bootfile/server response. Derive
   fields from the pinned2.91 implementation, not a guessed generic DHCP request.
5. Repeat with synthetic unknown MAC, then wrong architecture. Require no matching
   proxy/4011 reply. Each negative is bounded to2 attempts x1second, bracketed by
   positive controls; capture confirms the test requests actually left client and
   reached server. A generic timeout alone is not a passing denial test. No router
   allocator is started; yiaddr assertions detect accidental allocation. No claim
   about real router interoperability follows from this isolated fixture.
6. PhaseB: install the rendered `inet perkforge_pxe_pilot` table **inside pfpxe-s
   only**; check before apply, compare after. Nginx already runs inside that namespace with its own protected/source
   allowlist, serving only the harmless fixture.
   Test pilot HTTP/TFTP read success; synthetic wrong-MAC/source failures;
   missing-file failures distinct from forbidden traffic; wrong-interface test
   via namespace loopback (never a host NIC). Repeat pilot/unknown DHCP and4011
   checks to verify combined controls. Use bounded curl and BusyBox tftp, writing
   only to fixture temp paths. No address/MAC impersonation on real interfaces.
7. Always stop only recorded fixture children, wait/reap and verify no namespace
   processes remain BEFORE deleting links/namespaces. Verify both namespace names
   absent and no host fixture link. Namespace firewall vanishes with namespace;
   never apply/delete a host table. Retain sanitized result/capture summaries and
   hashes; clean only known fixture temp files after verification. If interrupted,
   inspect exact named namespaces and recorded PIDs before retry/cleanup. Never
   killall, flush host ruleset or delete an unrecognized namespace.

Finite outcome: positive and negative assertions for initial proxy,4011,TFTP,
HTTP; no lease allocation; no namespace/process/link residue. Any mismatch stops
progress to LAN activation. No real control-1 boot, firmware changes or disk action.

## Next specific approval

Approve creating the two named temporary namespaces/veth pair, namespace-local
addresses/firewall and foreground dnsmasq/nginx, and synthetic packet exchange
as above, with bounded cleanup. The implementation has passed local syntax/codec/mocked cleanup checks;
review the complete native command below before separately authorizing execution.
Do not substitute an unreviewed shell one-liner or install dependencies. Native
root/network-namespace capability is required; the agent sandbox cannot execute
it and must not bypass restrictions. This approval is separate from future LAN
service activation and node boot.

## Native implementation — completed once, future runs separately gated

`packet-fixture.yml` is now the local Ansible entrypoint. `packet-namespace.yml`
records namespace inode ownership; `packet-cleanup.yml` verifies dedicated unit
argv/unique-run paths and recorded invocation IDs before stop, rejects namespace
inode mismatches or remaining processes, and reports residuals instead of broad
cleanup. `probe_packets.py` is the standard-library verifier; it refuses packet
sockets unless inside the expected fixture namespace. Root-controlled synthetic
files and summaries are retained under a unique `/tmp/perkforge-pxe-packets-*`
path printed by the run, not deleted automatically. Services have150second maximum
runtime. No global service start/stop or host nft table is involved.

The shared dnsmasq template now names a dedicated lease file, avoiding any read
or write of default system/libvirt lease databases. Nginx's lock file is likewise
under dedicated state. This changes shared candidates: prior native validations
do not certify these revised paths. The fixture consumes current shared templates,
not the old rendered private files and not a permissive replacement configuration.

Implemented assertions: correlated DHCPDISCOVER/DHCPOFFER with yiaddr0, option54
server; DHCPREQUEST to4011 with vendor43/suboption71 service32768/layer0 and ACK
boot filename/server/echoed boot item; unknown MAC denial in both phases bracketed
by pilot positives; wrong architecture0 has no boot menu/file (a proxy offer may
still exist). HTTP200/content, daemon403 versus guarded drop, HTTP404, TFTPcontent/
ACK and missing-file error1; daemon-only other-source TFTP success explicitly shows
why nft guards matter; guarded other-source and wrong-MAC TFTP denial with positive
controls. Server AF_PACKET observations prove DHCP/PXE negatives arrived before
filtering, not merely a client timeout. Final server-loopback HTTP/TFTP negatives
check combined wrong-interface/source denial, bracketed by client positives; they
do not independently prove each individual nft rule. Control client addresses are
static fixture setup; no real router/DHCP allocation exchange is emulated.

The pinned2.91 boot-item handler uses service type rather than repeating the
architecture menu match; architecture is not an authentication boundary. This is
protocol regression testing, not complete UEFI firmware/UNDI, retry behavior,
router interoperability, Secure Boot or end-to-end installation certification.
Operator native execution and cleanup succeeded; this does not establish LAN,
router or physical firmware acceptance.

After separate execution confirmation, the complete invocation is:

```text
ansible-playbook -i localhost, -c local --ask-become-pass "$REPO_ROOT/pxe/pilot/packet-fixture.yml" -e fixture_execution_approved=true
```

Do not run it merely because it is documented. If interrupted or failed, preserve
output/run path and inspect named resources; do not blindly rerun. Existing names
cause a preflight stop. Failed cleanup remains a failure even if packet tests pass.
