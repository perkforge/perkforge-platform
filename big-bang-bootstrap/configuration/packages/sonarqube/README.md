# SonarQube Community Build — blocked inactive candidate (#110)

Big Bang 3.35.1 pins chart 2026.4.1-bb.4, native SonarQube chart 2026.4.1 and
Community Build 26.9.0.129388 image. Package declares Kubernetes >=1.32; rendering at
1.36.5 passes that constraint, not a complete vendor support/integration test.
Root does not include the disabled/paused profile; no apply entrypoint or live ops.

The pinned package explicitly supports Community Build. No commercial license is
required by this candidate or accepted/purchased. Community supports main-branch
analysis and GitLab CI integration, but **not multi-branch/pull-request analysis**;
no paid MR decoration promise. Quality-gate CI wiring, technical-account/PAT and
scanner tokens remain future reviewed configuration, not values or credentials
invented here. Keycloak/SAML/SSO stays off; local admin first.

`candidate-values.yaml` uses protected references for external JDBC password,
monitoring passcode and native `setAdminPassword.passwordSecretName`. That Secret
requires password/currentPassword keys; it must be provisioned privately under
separate approval and conflict-checked against actual store state. Do not treat
the stock initial password or reset hook as an enduring recovery mechanism. No
plaintext password, monitoring define_it, database sonarPass or generated key is
rendered. The one proxy Secret contains empty public proxy settings only.

The separately approved Ansible actor would apply versioned namespace installer
CRUD; helm-controller delegates to sonarqube-installer. Nine selected objects,
no chart runtime RBAC/bindings/lookups/CRDs, no cluster/bind/escalate grants.
Helm history and Secret access remain trusted namespace infrastructure permissions.
Native hook Job changes the application admin password later; this draft does not
execute it. Initial/upgrade rendered behavior does not prove existing DB migration.

## Deployment gates

- External supported PostgreSQL, size/credentials, consistent backups and JDBC
  verify-full/current physical CA trust remain UNCONFIGURED. No bundled database
  or fake demo service. A real trust mount is still required before selection.
- Native privileged initSysctl and root/CHOWN initFs stay **off**, matching Big Bang.
  Required host vm.max_map_count/file/process limits and CSI fsGroup behavior must
  be verified, then separately approved Ansible host changes if needed. Do not
  add privileged init containers or disable Elasticsearch checks as a shortcut.
- Preserved JVM workload requests/limits include about2GB requested/6GB maximum
  memory and500m/1CPU plus external PostgreSQL, init/hook jobs and scan workload.
  Vendor ephemeral-storage maximum512000M is **not reserved space**; review a
  realistic bound and request before deployment. No shrink-to-fit claim.
- 20Gi Longhorn PVC schedules40Gi across two replicas, excluding DB, snapshots,
  backups and headroom. Together with earlier monitoring/app proposals, GitLab
  and Harbor, cumulative storage can exceed the earlier80–100Gi logical budget.
  Select a subset or resize/review capacity; do not enable the entire queue.
- No Ingress/Istio/Gateway API route. Actual trusted HTTPS/backend TLS, network
  isolation and controlled first admin login require review before exposure.

Verify application status UP (not merely migration-needed readiness), trusted admin,
small analysis/quality gate, auth denial, persistence and isolated restore before
claiming acceptance. No scanner token, GitLab integration, app login or reset ran.
No obsolete direct SonarQube installer found; reusable configuration retained.

[Exact package](https://repo1.dso.mil/big-bang/product/packages/sonarqube/-/tree/2026.4.1-bb.4),
[Community GitLab integration and limits](https://docs.sonarsource.com/sonarqube-community-build/devops-platform-integration/gitlab-integration/introduction),
[native chart](https://github.com/SonarSource/helm-chart-sonarqube).
