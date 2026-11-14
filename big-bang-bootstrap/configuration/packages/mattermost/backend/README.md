# Dedicated Mattermost lab backends (inactive)

The pinned Big Bang 3.35.1 Mattermost 11.11.0-bb.0/operator 1.25.9-bb.1
remain the version authority. These files do not enable packages, select a root,
create credentials or grant network access. Preserve the integrated Portal/Grafana
root when preparing a later rollout.

## Files without a new S3 service

The native operator CRD supports `spec.fileStore.externalVolume.volumeClaimName`.
`files-values.yaml` uses Big Bang's native Flux post-renderer to replace the chart's
S3-only `fileStore` member with that supported setting. Compose this with the
candidate values and the separately provisioned `files-pvc.yaml`. No MinIO
operator, bucket, S3 account or shared application volume is needed. Do not merge
this list over another Mattermost post-renderer without preserving its entries.

The dedicated 10Gi RWO PVC uses the target default storage class unless explicitly
overridden. The local target should select its existing two-replica dedicated
Longhorn class through target configuration, not change the StorageClass. One
Mattermost replica is required. This is a non-HA lab profile, not a production
filestore recommendation; preserve retained data and verify backup/restore before
claiming recovery readiness. Updates may require releasing the old RWO attachment.

## Database and custody contract

`database-values.yaml` selects the pinned bundled PostgreSQL chart with a separate
8Gi volume. No image substitution, new database operator or shared application
state. Actual Registry1 PostgreSQL 18.6 inspection confirmed the official
`docker-entrypoint.sh`, UID/GID 1001 and `POSTGRES_DB`. Native chart values adapt
those inputs and replace Bitnami-only initialized-file readiness with pg_isready.
Native initdb SQL creates a non-superuser application role, separate from postgres
administration. The SQL runs on initial empty storage only; changing a Secret is
not a password rotation procedure. Existing CNPG is not used for this profile.
Never reuse Nextcloud, Harbor, GitLab or Velero data or credentials.

Runtime secrets belong in a dedicated OpenBao record and namespace-scoped ESO
consumer, not Helm plaintext values or Git. The eventual database consumer Secret
`mattermost-database` needs `DB_CONNECTION_STRING` and `DB_CONNECTION_CHECK_URL`;
the separate `mattermost-postgresql-auth` Secret needs `postgres-password`
(administrator) and `password` (app role). Both must describe the same dedicated database
and password. Do not use the chart's example password or auto-generated URL from
Helm password values. No filestore credential is needed in PVC mode. Creating the
record, auth identity, policies, ESO delivery and network routes requires the
coordinated approved rollout, not this document.

## Resource and placement inputs

`lab-resources-values.yaml` is an explicit smaller lab request (500m/1Gi), not a
change to generic candidate defaults. Before activation, budget PostgreSQL and
operator separately, inspect scheduler requests rather than CPU usage alone,
and select permitted target placement. Existing workloads must not be evicted or
resized to fit this app. No physical node name/address is embedded here.

The repeatable native check is
`big-bang-bootstrap/tests/configuration/check_mattermost_backend_native.py` with
explicit `--helm` and `--chart` paths. It renders the selected cached chart and
uses the already-cached official image (`--pull=never`). It derives every
container environment value and mounted directory from that StatefulSet,
substitutes synthetic data for Secret references, and verifies the exact
`POSTGRES_PASSWORD_FILE=/opt/bitnami/postgresql/secrets/postgres-password` path.
Kubernetes Secret/ConfigMap projections are modeled read-only (including when the
chart omits a redundant mount flag); socket, temporary and data directories are
writable under UID/GID1001 with a read-only container root. Both rendered probes
and the initdb/app-role/schema checks passed. No real Secret or cluster API is
read by this check; temporary container and files are removed on exit.
