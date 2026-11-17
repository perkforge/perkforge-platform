# Inactive declaration staging, not workload acceptance

The separately bootstrapped portal-runner-staging Kustomization owns only two
suspended child declarations. wait=false means their absent health conditions do
not block this declaration-only stage. No workload/resource child is reconciled.
The normal cluster-root remains on local-identity-onboarding with wait=true.
Never add workloads to this wait-free staging inventory. Tests enforce the exact
two Kustomizations, suspend=true, prune=false and force=false. Source/manager
reconciliation and eventual runner/CI activation remain separate authorized stages.
No Ready condition from this staging root establishes runner or pipeline health.
