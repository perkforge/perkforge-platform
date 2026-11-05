# PostgreSQL public CA delivery and rotation

The Cluster intentionally uses CNPG operator-managed certificates, not the
workstation lab CA. Keep application `PGSSLMODE=verify-full`; never enable the
chart helper that hardcodes verify-ca. No signing key belongs in application
mounts or a workstation export. See the [CNPG 1.30 certificate contract](https://cloudnative-pg.io/docs/1.30/certificates/).

## Initial delivery after database readiness

1. Use the reviewed release and explicit kubeconfig/context/API/cluster UID.
   Require the owned `gitlab/gitlab-postgres` Cluster to be Ready. Record its UID
   and read `status.certificates.serverCASecret`; do not guess a secret name.
2. Require that Secret to be in `gitlab`, labeled
   `app.kubernetes.io/managed-by: cloudnative-pg`, and have a controller owner
   reference to the exact Cluster UID, name `gitlab-postgres`, and API kind. Do not require
   a `cnpg.io/cluster` label: the observed operator-generated CA does not have it. Export only `ca.crt` with JSONPath, never dump the
   Secret YAML/JSON or export `ca.key`. Use a new owner-only file in a private
   directory; refuse to overwrite an existing different public certificate.
3. Verify CA:TRUE, certificate validity, public fingerprint/file SHA256, the live
   server chain and hostname `gitlab-postgres-rw.gitlab.svc.cluster.local` using
   verify-full. CNPG's internal CA-only checks are not application hostname proof.
   Record the CA and leaf expiry from the live Cluster status.
4. Review that public CA/hash as the PostgreSQL trust input. Run the existing
   default-off `deliver-public-ca.yaml` with `gitlab_ca_stage: postgres`,
   `gitlab_ca_scope: gitlab-ca-postgres-v1`, the exact `gitlab_ca_file_sha256`,
   explicit cluster guards and the actual absolute `gitlab_kubectl` executable.
   This creates only immutable ConfigMap `gitlab/gitlab-postgres-public-ca` with
   key `ca.crt`. Existing foreign/different objects fail closed, not rotate.
5. Verify exact readback and a zero-change repeat. Only the public ConfigMap is
   mounted in webservice, Sidekiq, migrations and Toolbox. Database credentials
   remain the separately approved existing `gitlab-database` Secret.

The live database and actual GitLab connection tests are separate gates. A local
copy of the CA, an offline CNG fixture, or a Ready database does not establish
application integration. Do not deliver the workstation CA under the postgres
profile merely because it works for the HTTPS ingress or Valkey.

## Expiry and a separately approved trust refresh

CNPG's default is a 90-day certificate period with renewal 7 days before expiry.
Its automatic renewal does not update an immutable application ConfigMap copy.
Record and check the actual CA/leaf dates; plan the trust refresh before the
earliest expiry. There is no automatic client trust rotation in this helper.

If the operator's public CA certificate changes, stop on a different existing
ConfigMap. Review the new public CA against the same owned Cluster and live
server. Prepare a separately approved maintenance batch: preserve the old public
certificate/hash, drain or stop only affected GitLab consumers, then guard any
client ConfigMap replacement by its exact UID/resourceVersion/content. The
create-only helper can recreate the approved fixed-name public ConfigMap only
after that separately authorized removal. Restart/recreate its consumer Pods;
immutable ConfigMap mounts must not be assumed to refresh after same-name
replacement. Verify live verify-full, fresh application connections and wrong
CA/hostname denials, then confirm unaffected cluster health.

Do not delete/rotate the operator's CA Secret, copy its signing key, disable
verification, widen app permissions, or restart the control plane for client
trust maintenance. Never silently merge unrelated roots into the trust input.
Rollback to the old public trust is permissible only if the current server still
validates against it; otherwise preserve state, keep consumers stopped and
resolve explicitly. This documents the required reviewed operation, not an
automatic destructive rotation or authorization to perform it.
