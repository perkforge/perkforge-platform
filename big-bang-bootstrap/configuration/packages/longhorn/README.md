# Longhorn storage package

Selected in clusters/local for the initial storage stage; the approved physical
v0.11.3 installation and first disposable storage test passed (see below). For a new target,
the outer Big Bang release and this package author active Helm desired state,
while a new target’s release-pinned seed remains paused until explicit activation approval.
Big Bang 3.35.1 generates the single child release/source from the official charts
Git tag longhorn-1.13.0 (charts/longhorn). The checksummed official chart artifact
is a test fixture, never vendored deployment source. Git sourcing avoids the shared
helmRepositories list replacement problem when other custom packages are selected.

The authored V1 configuration has two replicas with hard node/disk anti-affinity,
Retain, expansion and WaitForFirstConsumer; it does not make Longhorn the default
StorageClass. V2 is off (no raw disk/hugepage changes). Components select only nodes
labeled storage.perkforge.io/worker=true. Only the two reviewed workers may get that
label and node.longhorn.io/create-default-disk=true; leave control-1 unlabeled and
without a Longhorn data disk. Host prerequisites and label changes require separate
infrastructure approval. Worker directories, host prerequisites and both reviewed selection labels are prepared.

The data path /var/lib/longhorn initially shares each worker's OS filesystem.
Reserve 30% for the default disk, keep 25% minimum available, and use 100% scheduling
without overprovisioning. These scheduling settings are not filesystem quotas.
Budget 80–100Gi total logical claims initially, measured against actual photo import;
replicas, snapshots and rebuilds consume additional space. Keep bounded snapshots,
Harbor image retention and independent application backups. A worker outage leaves
one surviving copy until the second worker returns/rebuilds. The control plane is
still single-server. Add dedicated worker SSDs as actual growth requires.

## Before later activation

1. Run a read-only RHEL/Longhorn preflight: pinned RKE2/Longhorn compatibility,
   SELinux policy, iSCSI package/version/module/service, mount propagation, free
   disk/RAM, networking and worker selection. Worker packages/service/module and directory preparation completed;
   the first scoped runtime storage test has since passed. Do not install open-iscsi 2.1.12; check upstream guidance.
2. Separately approve host prerequisites and directory/label preparation. Longhorn
   needs privileged root/host access; prerequisites/ contains a privileged namespace,
   installer RBAC and named bind/escalate permissions derived from the pinned chart.
   Kubernetes create permissions cannot be resource-name scoped. Review actual
   rendered upstream runtime RBAC as well as the installer before granting it.
3. Select ../../configuration/packages/longhorn in the authoritative local root,
   review source/version/values and prerequisites, and explicitly clear the child
   suspension state only through reviewed source; the active child remains behind the paused seed. No standalone Helm
   install, Rancher Marketplace or competing Longhorn release is permitted.
4. Separately approved longhorn-prerequisites.yaml applies common Big Bang then
   this package's namespace/RBAC from a clean published release, with expected
   kubeconfig/context/UID. It never unpauses bootstrap or installs Longhorn itself.
5. Once bootstrapped, readiness.yaml phase storage observes the release, manager
   and CSI DaemonSets. Then test a small PVC: write/checksum data, recreate its pod,
   reattach on the other worker and verify persistence plus two healthy replicas.
   Failover/rebuild, backup/restore and real data import remain separate tests.
6. Keycloak's package dependency waits for Longhorn. Its default prerequisite
   backend is now longhorn; the alternate keycloak/prerequisites-longhorn overlay
   removes the static PV/class and replaces the claim's class without prebinding.
   The old base is not a migration mechanism. Never patch a bound PVC to switch
   backends; existing data would need a separately approved backup/migration.

A replica is not a backup. Personal Nextcloud data must have an independent,
protected copy and tested restore before becoming its only home.

Sources: https://longhorn.io/docs/1.13.0/deploy/install/ and
https://longhorn.io/docs/1.13.0/best-practices/.

## Repeat the read-only host audit

From the repository root, using the private inventory and protected output directory:

```sh
ansible-playbook -i infrastructure/ansible/inventory/.topology.yml \
  infrastructure/ansible/tests/longhorn-preflight.yml \
  -e longhorn_preflight_verify=true \
  -e longhorn_preflight_output_parent=/ABSOLUTE/PATH/TO/inventory/.rke2-state
```

The output parent must already be operator-owned, mode0700 and not a symlink.
Default/check mode contacts no hosts. Explicit verification reads worker state over
SSH without sudo and writes a fresh local mode0600 summary; it never prepares hosts.
Missing probes are recorded rather than treated as installation readiness.

The post-preparation audit found matching worker hostnames, XFS/shared mount
propagation, six CPUs, about 15GiB RAM and approximately 227GiB free per worker.
Both now have the reviewed iSCSI package, active/enabled iscsid, loaded iscsi_tcp,
NFS/encryption/inspection tools and the root-owned storage directory. All named
host probes completed successfully. SELinux remains enforcing; read-only queries
confirmed iscsid_t dac_override and container_t-to-spc_t socket connectto allow
rules. No direct iscsid_t-to-container_file_t directory rule was returned; this
alone does not establish a missing runtime permission. Runtime process contexts,
AVC behavior and PVC I/O were not validated by that host audit. The first scoped PVC test has now passed; a comprehensive runtime SELinux audit remains separate. The two reviewed worker selection labels are applied; control-1 remains excluded. Chart network policies explicitly select RKE2; the chart has since been applied through separately approved release promotion. Host readiness alone does not authorize deployment.

When reviewing cluster metadata, compare node names, hostname labels and RKE2
hostname annotations with the inventory. Investigate unexpected test values;
controller-owned annotations require understanding before removal. Keep full
metadata and physical identifiers out of tracked evidence.

## Worker prerequisite preparation

`infrastructure/ansible/playbooks/prepare-longhorn-hosts.yml` is a separate,
default-off maintenance operation for worker-1 and worker-2, sequentially. It
requires matching host identity, RHEL 10.2, enforcing SELinux, active RKE2 agent,
XFS/shared kubelet propagation and safe root-owned managed paths before writes.
The reviewed cached RHEL package is
`iscsi-initiator-utils-6.2.1.11-1.git4b3e853.el10_2.2.x86_64` on both workers.
It is pinned to avoid silently selecting the known problematic upstream 2.1.12.
Recheck available versions before using this procedure on a later OS/repository.

The operation installs that iSCSI package plus nfs-utils, cryptsetup and
setools-console (inspection only); persists/loads iscsi_tcp, enables/starts iscsid,
and creates root-owned mode0700 /var/lib/longhorn. This directory shares the root
filesystem and is not a quota. It does not change SELinux policy or labeling,
restart RKE2, modify control-1, label nodes, create claims or deploy Longhorn.
NFS/encryption tools make those features available; neither is enabled here.

After action-specific approval, use the private inventory and password sudo:

```sh
ansible-playbook -i infrastructure/ansible/inventory/.topology.yml \
  infrastructure/ansible/playbooks/prepare-longhorn-hosts.yml --ask-become-pass \
  -e longhorn_host_prepare_apply=true -e longhorn_host_prepare_reviewed=true
```

Omitting apply or using check mode contacts no hosts. Afterward rerun the read-only
audit and inspect active SELinux allow rules with sesearch, including iscsid_t
capability/directory access. Do not install a policy workaround without evidence.
Later runtime contexts, AVC denials and actual PVC I/O still require validation.
Review and approve worker labels separately after host verification.

## Worker selection labels

After host preparation and verification, separately approve
`infrastructure/ansible/playbooks/label-longhorn-workers.yml`. It adds exactly
`storage.perkforge.io/worker=true` (our storage scheduling selector) and
`node.longhorn.io/create-default-disk=true` (Longhorn's upstream default-disk
opt-in) to worker-1 and worker-2. Control-1 remains unlabeled for both keys.
These are operational labels, not illustrative metadata. They match the pinned
chart's component selectors and default-disk creation gate.

Supply explicit absolute `longhorn_labels_kubeconfig`, `longhorn_labels_kubectl`
and `longhorn_labels_expected_cluster_uid` through an ignored protected vars file.
After separate approval, invoke the playbook with that file and both
`longhorn_worker_labels_apply=true` and `longhorn_worker_labels_reviewed=true`.
Defaults/check mode contact no cluster. It checks cluster UID, the exact three
node names, matching hostname labels, Ready status, worker roles and label conflicts
before writing. JSON patches test each node UID/resourceVersion, preserve unrelated
metadata and do not overwrite conflicting values. Reruns skip matching labels;
concurrent changes cause failure for review rather than a blind overwrite. A failed
second-worker patch may leave the first worker labeled; inspect before retrying.
The operation does not install Longhorn, create disks/claims or unpause Flux.

The local root now authors active outer/Longhorn releases behind a paused,
release-pinned seed. Use the [release/seed procedure](../../ansible/README.md#longhorn-only-release-and-seed-activation); v0.10.0 is the suspended staging input.
Do not manually resume a child while its selected Git release still suspends it.

## Installer chart lookup permission

The pinned1.13.0 chart's `templates/validate-psp-install.yaml` executes an unnamed
ClusterRole `lookup` before checking `enablePSP` (already false). Helm evaluates
that lookup even though the template lines begin with YAML comments. The existing
named-role list/write permissions cannot authorize this collection request.
The installer ClusterRole therefore adds only `list` on
`rbac.authorization.k8s.io/clusterroles` without `resourceNames`, bound only to the
existing `bigbang:longhorn-installer`. This exposes cluster role definitions to
that installer; it adds no unrestricted get/watch, writes, bind/escalate or Secret
access. Existing named mutation permissions are unchanged.

A named list would require a name field selector, which this chart does not send
([Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#referring-to-resources)).
Disabling PSP does not avoid the lookup; patching/forking or changing the pinned
upstream chart would introduce a separate source/version change. Retain the
minimal read-only permission rather than broadening installer writes or bypassing
Helm server rendering.

The regression uses real Helm server-side rendering of the pinned chart against
an isolated loopback authorization model: the old role and a name-restricted list
fail, while this exact list-only addition passes. It is not live Kubernetes
acceptance. Publication alone changes no running source ref: old release tags stay immutable.
A future released checkout, installer-RBAC apply and failed-release retry need
separate review/approval; do not imperatively patch permissions or delete volumes.
UI ingress remains disabled and Rancher/identity/tenant selection is unchanged.

## Lab trust decision: upstream diagnostic RBAC

The operator accepts upstream Longhorn 1.13.0 as trusted cluster infrastructure in
this physical lab. The chart unconditionally binds its dedicated
`longhorn-support-bundle` account to `cluster-admin` for on-demand diagnostic
collection. Its separate manager `longhorn-role` also already grants wildcard
verbs on ClusterRoles/ClusterRoleBindings, including bind/escalate. Neither the
runtime deployment nor its delegated installer is a least-privileged security
boundary. Disabling UI ingress does not remove these privileges.

The installer therefore adds exactly `bind` on the named ClusterRole
`cluster-admin`. It does not bind the installer itself to cluster-admin, add
wildcard installer rules, or broaden the existing named binding-object mutation
list. Kubernetes still checks both binding-object permissions and authority over
its roleRef; named object access alone was insufficient. This grant permits
cluster-admin delegation through the installer's existing binding creation rights;
RBAC cannot restrict create by object name or subject. Treat compromise of this
installer as a cluster-wide security risk.

Retain the upstream chart without a local support-bundle patch/fork. UI ingress
stays disabled; Rancher, identity and tenants remain deferred. Revisit runtime
RBAC hardening separately before extending the lab trust model.

At the failed v0.11.2 attempt (2026-11-01 01:16:52 UTC), Longhorn was
partially installed and stalled on this diagnostic binding. The separately
approved v0.11.3 grant and single child/umbrella resets subsequently passed
readiness; the first scoped PVC test below also passed. Publishing this fix does not change the
active release-pinned source. A new release, live prerequisite grant, promotion
and failed-release retry require separate action-specific approval. No live grant
or retry is authorized by this document.

The regression renders all pinned child resources, checks every role's escalation
and every binding's roleRef authority, and proves removal of this new grant leaves
only the support-bundle binding unauthorized. This is an offline policy check,
not API-server or storage acceptance.

Sources: [Longhorn support bundles](https://longhorn.io/docs/1.13.0/troubleshoot/support-bundle/),
[pinned chart RBAC](https://github.com/longhorn/charts/blob/longhorn-1.13.0/charts/longhorn/templates/clusterrolebinding.yaml),
and [Kubernetes binding restrictions](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#restrictions-on-role-binding-creation-or-update).

## Disposable storage acceptance

The first approved physical test passed on 2026-11-01 at v0.11.3: initial sample
write on worker-1, same-worker pod recreation, then normal detach/reattachment on
worker-2 all produced the same checksum. The volume was healthy with two running
replicas on distinct workers and both engine replica modes RW. Three distinct pod
UIDs used the same claim/PV. Manager/CSI, umbrella/root readiness and exact release
revision had already passed. This is small-sample acceptance, not performance,
node-loss/rebuild, backup/restore or HA validation.

`configuration/ansible/longhorn-storage-smoke.yaml` owns the disposable test through
Ansible/YAML. Its read-only Python verifier checks the selected release/target,
worker disks/capacity and final volume/replica/engine state. It creates one unique
restricted namespace and one 1Gi `sample` PVC using `longhorn`, then creates one
non-root pod at a time. Node selectors preserve WaitForFirstConsumer scheduling;
it never assigns nodeName directly. The official BusyBox 1.37.0 multiarchitecture
image is digest-pinned; the pod has no service-account token, host access or added
RBAC. Only the first pod writes nonsecret sample data. Later pods only read it.

Defaults and check mode contact no API. A repeat requires separate approval and a
fresh mode0700 canonical output directory plus protected mode0600 vars:

```yaml
# Protected operator inputs, never a credential-bearing tracked file.
target_kubeconfig: /ABSOLUTE/PROTECTED/kubeconfig
target_context: REVIEWED_CONTEXT
expected_cluster_uid: REVIEWED_KUBE_SYSTEM_UID
storage_test_namespace: pf-longhorn-smoke-FRESHLOWERCASEID
storage_test_output: /ABSOLUTE/PROTECTED/FRESH_OUTPUT
```

The scoped verifier currently expects the recorded v0.11.3 release, two named
workers and a nondefault retained two-replica class. Review/update that contract
before using another release/topology; do not disable its checks. After approval:

```sh
umask 077
ANSIBLE_LOG_PATH=/ABSOLUTE/PROTECTED/FRESH_OUTPUT/ansible.log \
ANSIBLE_LOCAL_TEMP=/ABSOLUTE/PROTECTED/FRESH_OUTPUT/ansible-tmp \
ansible-playbook -i big-bang-bootstrap/configuration/ansible/inventory.yaml \
  big-bang-bootstrap/configuration/ansible/longhorn-storage-smoke.yaml --limit local \
  -e @/ABSOLUTE/PROTECTED/INPUTS.yml -e storage_test_apply=true
```

Save the command's actual exit status as well as its log; an incomplete run is not
PASS. Evidence includes namespace/pod/PVC/PV UIDs, all three checksums and Longhorn
replica/engine snapshots. The first run's protected `retained-resources.json` also
records exact cleanup targets. No terminal/password-input capture is needed.

The playbook gracefully deletes only its prior test pod after checking its UID,
waits for normal detach, and stops on errors/timeouts. It does not resume partial
runs or repair storage. Inspect retained evidence before deciding any retry.
It never deletes the claim, PV, volume or namespace. The final pod sleeps for at
most one hour; the retained claim/data outlive it. Approve cleanup separately,
including the effect of Retain, rather than assuming namespace deletion erases
Longhorn data. No forced detach, node reboot or existing workload change is part
of this test. The observed missing dm_crypt modules did not block this unencrypted
volume; encrypted storage remains unvalidated and needs separate preparation.
