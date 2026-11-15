# Foundation-only adoption checkpoint

This optional intermediate root inherits all current application resources and
selects enrollment stage A `0732cff9aff9815d1bedec4b94ff2883ce75b577`.
It adds only `identity-portal-foundation-root`, which reconciles the reviewed
admission and controls stages. It does **not** create `identity-portal`, any
phase Kustomization, initializer or Job. Membership remains held in stage A.

Use only after separate root-owned guard/grant consent and native adoption
preflights. Confirm the existing application consumer output is unchanged by
the enrollment ref update; preserving its path alone is not sufficient.
Verify admission, controls and actual SSA ownership before proceeding. Stop on
unexplained defaulting/field conflicts; this overlay does not authorize force.

This is an initial-adoption checkpoint, not a way to stop already-selected
phases. With prune disabled, selecting it after a phase root exists does not
remove or suspend that root. Require that no identity phase root/Jobs are active
before first selection; otherwise stop for an explicitly approved shutdown plan.

After adoption and private-volume prerequisites pass, notify the owner before
separately selecting the reviewed stage-A onboarding root. That later source
selection, and subsequent membership release B, remain distinct actions. No
bootstrap permissions, credential material, provider changes or workload retry
are authorized by this source addition.
