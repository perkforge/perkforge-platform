# Velero local baseline and configurable AWS example

A small default-off local usage/testing deployment: pinned Velero, a dedicated
Garage instance on an ordinary Longhorn PVC, configurable scheduled backups and
an isolated copied-data restore exercise. It is **not independent disaster
recovery**: source volumes and the local backup store share Longhorn and its
failure domains. The separate planned Toshiba/Longhorn backup strategy remains
separate and needs its own acceptance. No live protection is claimed by this MR.

## What is configured

- Big Bang 3.35.1, wrapper chart 12.2.1-bb.0 (upstream 12.2.1), Velero 1.18.4,
  AWS plugin 1.14.4. See [pin evidence](compatibility.yaml). Kubernetes 1.36.5
  compatibility still needs actual cluster acceptance.
- Garage 2.5.0/SQLite, synced metadata/data, native metadata snapshots, one replica,
  a separate bucket/key and repository password. Never reuse GitLab Garage.
- An ordinary `longhorn` PVC, with **5Gi as the configurable small-test default**.
  This is not a 48-hour capacity guarantee for arbitrary tenant data. No host
  directory, static local PV, XFS project quota, mount or reservation changes.
  Garage's configured object capacity must leave room in this PVC for SQLite,
  WAL, transient metadata snapshots and growth. Measure usage before expanding.
- Platform-operated scoped access. No tenant Velero credential or broad namespace
  grants. Explicit scheduled namespaces get read access plus CSI snapshot actions.
  The native schedule uses an explicit core/app resource list, not arbitrary
  operator CRDs or RBAC. No pods/exec grant is needed for this baseline. Restore
  write grants exist only in the disposable exercise's target namespace.
- Local retention defaults to 48h; [AWS defaults](profiles/aws.yaml) use 336h.
  Retention is not cadence or RPO. Cron, namespaces, retention and capacity remain
  configurable. A blank cron emits no Schedule. A configured Schedule is paused
  by default and requires explicit approval to unpause.

## Private transport and trust boundary

The store is a ClusterIP Service on HTTPS 443, targeting a non-root, read-only
Nginx 1.31.6 TLS sidecar on Pod port 8443. Its official linux/amd64 image is digest
pinned. It preserves the signed S3 Host/URI, streams requests without body-size
limits or proxy buffering, and forwards only across the same Pod's loopback to
Garage at `127.0.0.1:3900`. Garage's RPC/admin endpoints also remain loopback-only.
There is no Service or Pod-IP listener for cleartext S3. TLS protects the network
path; the final same-Pod loopback hop is HTTP, not encryption inside the Pod.

Reciprocal NetworkPolicies permit the store's Pod port 8443 from the **platform-only
velero namespace** and allow Velero egress only to the store's labelled Pods,
cluster DNS and the explicitly selected API addresses. The namespace selector
and Pod selector are in the same peer, so both must match. All Pods in the trusted
Velero namespace can connect, including dynamically named movers and maintenance
Jobs; tenant namespaces cannot gain access by copying a Pod label. Do not grant
tenants Pod creation, exec or policy management in `velero` or `velero-store`.
Cluster/node administrators remain trusted; NetworkPolicy is not a boundary against
them. Actual CNI enforcement and tenant denial still need live acceptance.

## One normal GitOps rollout

1. Review/merge/release this source normally. Use a clean immutable release checkout.
   The `local-velero` root inherits **local-grafana-sso**, preserving Harbor and
   Grafana OAuth. Review the current composition before selecting the new root;
   a root change is not permission to disable or downgrade other apps.
2. Copy [deployment.example.yaml](deployment.example.yaml) outside Git with mode
   0600; supply exact cluster/context, released commit, existing protected files,
   approved worker list and exact API addresses. The fixed store endpoint is
   `https://velero-store.velero-store.svc.cluster.local`. Supply a server certificate
   whose DNS SAN covers that name, its private key and trusted CA. The installer
   checks the chain, hostname, expiry and matching key; `insecureSkipTLSVerify`
   stays false. Cluster DNS resolves this Service; no lab DNS entry, ingress IP,
   Traefik route or host/source-IP allowlist is needed. The existing protected
   certificate/credential procedure still requires its explicit approval.
3. With explicit foundation/credential/RBAC approval, run `install.yaml` with
   `velero_install_apply=true` and `velero_install_scope=velero-foundation-v1`.
   It installs pinned CRDs, scoped foundation, the ordinary PVC, supplied immutable
   credentials and source-rendered runtime values. Default/check modes are inert.
   No root/tag promotion or host changes are performed. Existing foreign objects,
   credentials and foundation drift are refused rather than silently adopted.
4. Through the standard reviewed GitOps source/root selection, select the released
   `local-velero` root. Flux starts Garage and Velero from the configured values.
   Velero's BSL may remain unavailable until the new bucket is initialized.
5. Establish an explicitly approved `kubectl port-forward --address=127.0.0.1` to
   the new Garage Pod's admin port 3903. Run `bootstrap-store.yaml` with explicit
   init scope, native node ID, object capacity, one bucket and supplied key files.
   It never creates the forward, rotates keys, repairs data or adopts another
   store. Ambiguous writes leave a private pending receipt; inspect before retry.
   A normal repeat is zero-change. Wait for Garage, Velero/node-agent and BSL Ready.
6. Run the explicitly approved synthetic exercise below. Only after acceptance,
   approve the desired cron/namespaces and unpause. Re-run `install.yaml` with
   reviewed inputs to change runtime values: it checks ownership and uses a
   resourceVersion-guarded update, leaving Flux to reconcile the workloads/Schedule.
   No manual live-only values patch is needed. Changing the PVC or immutable
   credentials is a separate reviewed operation; this installer will not resize
   or rotate them. Removing a namespace from a schedule stops its selection, but
   does not revoke its previously approved RBAC grant; revoke that explicitly.

The installer does not quiesce application databases or promise consistent
real-world app backups. Start with disposable data. Before scheduling an actual
app, review native consistency hooks and isolated application/DB validation.
This baseline intentionally has no generalized application rollback framework.

## Isolated synthetic restore

`exercise.yaml` remains default-off. Explicitly approve its two new namespaces,
two 1Gi PVCs, temporary CSI/mover storage and one graceful restart of the new
Garage Pod. It checks native copied-data upload/download identities and byte
counts, restores onto new PVC/PV identities and compares SHA256 after reopening
the repository. Wrong or incomplete transfers fail; evidence is retained on
failure and cleanup is explicit. All schedules must be paused for this exercise.
This proves the tested copy/restore path, not independent DR, power-loss safety,
application consistency, retention cleanup timing or recovery of a real tenant.

## AWS and real-world configuration

[Partial AWS values example](profiles/aws-values.example.yaml) shows configurable
336h TTL, bucket/prefix/region/KMS and a paused schedule with operator-supplied
cron/namespaces. It is **non-runnable until a reviewed AWS foundation is supplied**;
merging it with `deployment/install-values.yaml` alone is not sufficient. It is
not selected locally and does not provision AWS.

Before using it, the AWS configuration must:
- Replace inherited server/node-agent `storage.perkforge.io/worker` selectors and
  hostname affinity with reviewed AWS worker placement.
- Supply authorized registry credentials or replace inherited `private-registry`
  image-pull references. Do not reuse local credentials.
- Supply or replace `velero-node-agent` and `velero-maintenance` ConfigMaps and
  their argument references, including AWS placement and resource settings.
- Replace the local postrenderer that deletes `csi-volumesnapshotclass` with
  reviewed EBS CSI VolumeSnapshotClass ownership, zone mapping and encryption.
- Supply scoped RBAC, CRDs and service accounts. Annotate the existing Velero
  service account for workload identity in that foundation; values alone cannot
  update it while `serviceAccount.create=false`.
- Fill every empty setting and review IAM/KMS permissions, network egress,
  capacity, retention/cadence, and application-consistent restore acceptance.

Do not deploy local Garage/Longhorn foundation in AWS. No public example contains
credentials or physical target identifiers.

## Evidence and limits

Existing exact-client Garage 2.5 tests covered S3 multipart operations, encrypted
Kopia upload, graceful restart, fresh-cache restore, full maintenance, and TLS/key/
bucket denial with disposable data. These do not prove cluster data movement or
power-loss recovery. Current offline regressions cover default/check refusal,
scoped RBAC, pinned chart rendering, preservation of existing app composition,
synthetic bootstrap and isolated restore. See MR #255 for current results.
CI pause and all live approval boundaries remain unchanged.

Native private-TLS evidence is retained in
[`private_tls_evidence.json`](../../../tests/fixtures/velero_native/private_tls_evidence.json).
The exact rendered proxy config/image passed signed multipart S3 and encrypted
Kopia restart/fresh-cache restore tests with synthetic loopback data, including
wrong-CA/hostname/key/bucket denials. This does not replace live service-DNS, CNI
tenant-denial or Kubernetes data-movement acceptance.
