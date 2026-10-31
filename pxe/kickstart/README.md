# RHEL10 Kickstart design candidate

`rhel10.ks.j2` is a **non-deployable review specimen**, not a replacement installer.
The [offline preparation entrypoint](../ansible/README.md) can render it privately
as install.ks.BLOCKED. There is no boot integration, published file or apply command.
Its unconditional `%pre --erroronfail` abort has no enabling flag, and draft storage commands remain unreachable behind that abort. Never use the working control node to try it.

Start with the [current Red Hat guidance map](../../infrastructure/RHEL-PROVISIONING-GUIDANCE.md).
The source/time additions use standard url/timesource and explicit network device
selection; they do not resolve a deployment source or NTP choice for a real host.
RHEL10 syntax differs from older examples; the map records the reviewed changes.

The candidate records standard RHEL directives for the intended minimal package,
DHCP/MAC/hostname/time, locked-root and public-key enrollment shape. It does not
claim a locked bootstrap account can log in or use sudo: native PAM/SSH/sudo behavior remains untested for the controlled physical pilot. No private key, password/hash, token or subscription
material belongs in this template or HTTP output. Metadata is private inventory;
only synthetic values are used in offline tests.

Before implementation: complete private disk metadata and standard persistent-ID
selection; add only a minimal pre-check if necessary to enforce the approved disk,
approved credential mode and bootstrap removal, installation-time key-only SSH,
source/partition/reboot policy, host-fingerprint trust and service lifecycle.
See [the design](../../infrastructure/PROVISIONING-REDESIGN.md) and
[tomorrow readiness](../../infrastructure/TOMORROW-READINESS.md).

Offline tests cover missing inputs, unconditional abort, scoped disk guards,
initial policy and short access handoff. Approved local pykickstart3.78 is now
available and a fully populated synthetic candidate passed RHEL10 syntax checking.
Validate the actual worker-specific file after its missing inputs are supplied.
A parser pass does not validate packages/scripts or real storage/PAM behavior.
The agreed controlled physical pilot accepts that risk; full VM rehearsal is
optional and its unfinished custom runner is parked, not required.

Sources: [Kickstart reference](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/kickstart-commands-and-options-reference),
[validation limitations](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/creating-kickstart-files).


Actual adapters now rendered by Ansible into the BLOCKED candidate:

- [Initial policy](bootstrap-post.ks.j2): standard installed-root post script,
  shared SSH/sudo templates, conservative ledger and final offline SSH enable.
- [Storage](storage.ks.j2): exact persistent single-disk directives plus read-only
  serial/capacity/type checks. Missing identity/layout emits an abort instead.

No commands are run while rendering. In particular host-key creation, unit-link
changes and disk commands exist only as unreachable future install code. The
unconditional physical pre-abort is retained without an enabling flag. Mocked
adapter success/failure is not a RHEL parser, installation or real-disk result.
