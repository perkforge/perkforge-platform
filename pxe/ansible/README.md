# Offline Ansible preparation

`prepare.yml` runs locally without facts/become/commands/handlers. It writes only
an inert review plan and blocked Kickstart; no node connection or live actions.

## Local working files

Use one ignored, protected tree, with no actual credential values:

```text
pxe/local/                         shared nonsecret working artifacts if needed
  worker-1/
    inputs.yml                     canonical nonsecret node inputs (0600)
    plan.md                        latest reviewed snapshot (0600)
    install.ks.BLOCKED             matching inert snapshot (0600)
    README.md                      current run/provenance pointer (0600)
    runs/<current-run>/            current immutable render (0700; files0600)
  history/                        older private runs/validation evidence (ignored)
```

Copy [example inputs](../inputs.example.yml) into that node's inputs.yml. Set
`hostname` and absolute `output_dir` to this worktree's
`pxe/local/<hostname>/runs/<new-run-id>`. Unknown values stay UNCONFIGURED.
All directories must be0700; no symlinks. The local tree is Git-ignored, not a
credential store. Keep private keys/passwords in protected external storage;
public-key input or nonsecret references only. Prior `.secrets` and `/tmp` run
history is preserved but is not the new workflow's canonical input/output.

From the worktree root (offline only):

```sh
ansible-playbook -i localhost, -c local pxe/ansible/prepare.yml -e @pxe/local/worker-1/inputs.yml
```

`--check` validates without writing. Existing output is never replaced. The
renderer creates only the new run's plan and blocked candidate; latest plan
snapshots must be refreshed together after review, with hashes/run provenance,
preserving old snapshots in a run first. Snapshot copying is not an install step.
Legacy `/tmp/perkforge-pxe-plan-NAME` output remains accepted for historical offline
fixtures; normal operator work belongs under pxe/local. No apply flag exists.

`TEMPORARY_KEY_ONLY_BOOTSTRAP` records the approved [bootstrap design](../bootstrap/README.md)
only. Bootstrap Ansible components and the initial Kickstart adapter have offline
fixtures; real RHEL behavior and controller lifecycle remain unvalidated. UNDECIDED remains
valid. Every render stays blocked even with selected design and filled metadata.

The template's source and time inputs follow current RHEL10 syntax, but a rendered
specimen is not a ksvalidator pass or a real rehearsal.

## Reproducing a reviewed plan

Keep the versioned `prepare.yml`, example input schema and Kickstart template,
plus the saved private inputs, media identity and recorded source/tool versions.
Generated plans stay local; they are evidence, not the recipe. LikeC4 is pinned
for diagrams, but this does not pin the Ansible/Python/RHEL-validator toolchain.
Record those versions and the source revision/input/output checksums per run.

The new worker input has **no verified encrypted backup or restore/regeneration
test yet**. This renderer performs neither. Under a separately approved recovery
step, restore inputs into a protected location and regenerate into a fresh output
directory, then compare the reviewed result. Do not infer deterministic output or
successful recovery merely from one render. See [the readiness follow-up](../../infrastructure/TOMORROW-READINESS.md#private-input-recovery-follow-up).

The active [controlled worker pilot](../../infrastructure/TOMORROW-READINESS.md)
uses standard Kickstart and proven PXE, not a mandatory VM framework. There is no
hidden apply flag here. The [earlier design](../../infrastructure/PROVISIONING-REDESIGN.md)
is retained history, not extra operating gates. [Vendor mapping](../../infrastructure/RHEL-PROVISIONING-GUIDANCE.md)
explains the Debian/router adaptations. [Readiness](../../infrastructure/TOMORROW-READINESS.md)
retains the current blocked verdict. Existing [pilot recovery/shutdown](../pilot/HANDOFF.md)
paths stay intact while their manual installation route is superseded.

Selected bootstrap design renders the initial standard post-install adapter from
shared SSH/sudo policy templates. Explicit unencrypted storage layout plus exact
persistent ID/serial/capacity renders the draft storage adapter; missing fields
instead render an abort. The unconditional physical pre-abort is NEVER removed.
Rendering executes none of those target commands, generates no host keys and
publishes nothing. Source-address context is nonsecret; no DNS hostname decision
is required because initial key-only policy explicitly uses UseDNS no.
