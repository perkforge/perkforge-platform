# Offline Ansible preparation

`prepare.yml` is the new normal starting point, not an installer. It runs locally,
without facts/become/commands/handlers, writes only a new private temporary plan
and blocked Kickstart candidate, and cannot start services or connect to a node.

Copy [example nonsecret inputs](../inputs.example.yml) to an ignored private input
file, set a new output directory `/tmp/perkforge-pxe-plan-NAME`, and review inputs.
Unknown disk/credential fields stay explicit; all outputs remain blocked even if
metadata is filled. No secret-bearing inventory belongs in this preparation.

Command shape (replace the labeled input path; this does not authorize install):

```sh
ansible-playbook -i localhost, -c local pxe/ansible/prepare.yml -e @<PRIVATE_NONSECRET_INPUTS>
```

`--check` validates inputs without creating output. Existing output is never
replaced. The report names unresolved work instead of fabricating ready state.
Files are mode0600 inside a mode0700 directory, outside serving/runtime roots.
The template's source and time inputs follow current RHEL10 syntax, but a rendered
specimen is not a ksvalidator pass or a real rehearsal.

The future install workflow is [a design](../../infrastructure/PROVISIONING-REDESIGN.md),
not a hidden apply flag here. [Vendor mapping](../../infrastructure/RHEL-PROVISIONING-GUIDANCE.md)
explains the Debian/router adaptations. [Readiness](../../infrastructure/TOMORROW-READINESS.md)
retains the current blocked verdict. Existing [pilot recovery/shutdown](../pilot/HANDOFF.md)
paths stay intact while their manual installation route is superseded.
