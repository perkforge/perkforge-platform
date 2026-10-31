# RHEL10 Kickstart design candidate

`rhel10.ks.j2` is a **non-deployable review specimen**, not a replacement installer.
The [offline preparation entrypoint](../ansible/README.md) can render it privately
as install.ks.BLOCKED. There is no boot integration, published file or apply command.
Its unconditional `%pre --erroronfail` abort has no enabling flag, and storage
commands remain comments. Never use the working control node to try it.

Start with the [current Red Hat guidance map](../../infrastructure/RHEL-PROVISIONING-GUIDANCE.md).
The source/time additions use standard url/timesource and explicit network device
selection; they do not resolve a deployment source or NTP choice for a real host.
RHEL10 syntax differs from older examples; the map records the reviewed changes.

The candidate records standard RHEL directives for the intended minimal package,
DHCP/MAC/hostname/time, locked-root and public-key enrollment shape. It does not
claim a locked bootstrap account can log in or use sudo: that credential/PAM
choice remains unresolved. No private key, password/hash, token or subscription
material belongs in this template or HTTP output. Metadata is private inventory;
only synthetic values are used in offline tests.

Before implementation: complete private disk metadata and standard persistent-ID
selection; add only a minimal pre-check if necessary to enforce the approved disk,
approved credential mode and bootstrap removal, installation-time key-only SSH,
source/partition/reboot policy, host-fingerprint trust and service lifecycle.
See [the design](../../infrastructure/PROVISIONING-REDESIGN.md) and
[tomorrow readiness](../../infrastructure/TOMORROW-READINESS.md).

Available offline tests check required placeholders, unconditional abort, absence
of active disk mutations/secrets and package intent. They are not RHEL validation.
`ksvalidator`/`pykickstart` are unavailable in the current environment; no package
installation is authorized or attempted. Even a validator pass would not validate
scripts/packages or real disk/SSH behavior. Real rehearsal requires separately
approved disposable UEFI media/disks (optionally an isolated VM installer fixture,
not a VM cluster) and appropriate RHEL10 validation tooling.

Sources: [Kickstart reference](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/kickstart-commands-and-options-reference),
[validation limitations](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/creating-kickstart-files).
