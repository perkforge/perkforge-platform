# OpenBao lab activation and recovery

Repository preparation only; these commands have not run. The user approved
the bounded lab setup and data-preserving Nextcloud pause, contingent on reviewed
configuration and validation. Use the reviewed commit and preserve private evidence. All tools use ordinary documented OpenBao/Keycloak/Kubernetes
APIs. There is no foundation library or application dependency on this repository.

## Exact proposed live scope

- Apply only `local-lab/fleet/bundles/openbao-support/resources.yaml`: namespaces
  `openbao`/`external-secrets`, Certificate `cattle-system/openbao-lab`, TLS
  passthrough route `openbao/openbao`, and two NetworkPolicies. Both namespaces are expected to be new; verify that before applying and refuse
  unexpected adoption.
- Install the pinned official OpenBao/ESO charts through separately selected
  Fleet paths. OpenBao adds a StatefulSet, ServiceAccount, service-discovery
  Role/RoleBinding, `system:auth-delegator` ClusterRoleBinding, Services and two
  retained PVCs (2+1 GiB). ESO adds its controller ServiceAccount/Deployment,
  Services, namespace-local controller/leader-election RBAC and CRDs. Render
  and review the exact resource list at the approved head before applying.
- Run leaf delivery, private initialization/unseal ceremony, the existing
  Keycloak script's `--openbao-only --apply`, and `configure.sh --apply`.
  These are separate security/credential actions included explicitly in the
  approval. The Keycloak mode creates/reconciles only one owned client and
  groups mapper, preserves its secret and changes no users/memberships.
  Existing membership in `/platform/admins` or `/tenants/home/admins` is required;
  any new human membership is an additional named grant, not implied here.
- Enable only Home portal delivery. This adds `openbao-sync`, its named
  TokenRequest Role/RoleBinding, SecretStore and ExternalSecret in
  `tenant-home-portal`; it updates only `.dockerconfigjson` of mutable
  `portal-ghcr` only after a separate real-credential migration approval. First
  use the synthetic enrollment below. Enter only synthetic values at this stage.
  Do not copy/migrate existing credential values from Kubernetes automatically.
- Verify existing portal/Nextcloud health and the live acceptance matrix in the
  README. Do not change existing namespace grants, quotas, policies, data,
  Nextcloud Secrets, CA private keys, VM sizing or core DNS.

The user explicitly included a bounded data-preserving Nextcloud pause in the
lab approval; see [capacity assessment](CAPACITY.md). Future pauses still need
action-specific approval.

## Ordering and TLS/network checks

1. Record allocatable/request headroom, working sets, CPU and recent pressure/
   OOM events; record app/DB health, PVC UID/volume bindings and Fleet pins.
   Render support, OpenBao, ESO and enabled delivery offline. Keep active
   platform GitRepos unchanged until approval names each path.
2. Apply support to empty new namespaces. Wait for Certificate `openbao-lab`
   Ready in `cattle-system`, then run:

   ```sh
   local-lab/openbao/deliver-tls.sh --apply /path/to/kubectl /private/rke2.yaml
   ```

   It reads only `openbao-lab-issued`, validates issuer/Ready and public/internal
   SANs, refuses unowned destinations, copies its leaf cert/key only to OpenBao,
   and copies only the public CA to OpenBao and Home portal ConfigMaps. No
   Issuer Secret or CA private key is accessed. It does not migrate app secrets.
3. Install OpenBao through Fleet. It is expected to remain sealed/unready until
   the ceremony below; do not reset storage to fix that state. Use an approved
   direct TLS client/port-forward for bootstrap; no external login is needed
   while the pod is sealed. Export **public** CA to an operator file and use
   `BAO_CACERT`, never skip verification. With port-forward, use
   `BAO_ADDR=https://localhost:8200` plus
   `BAO_TLS_SERVER_NAME=openbao.openbao.svc` (CLI-supported hostname override).
4. The TCP route preserves TLS from browser to OpenBao. No Traefik transport
   exception, HTTP fallback or additional leaf key is required. Resolve
   `openbao.local-lab.test` on the approved operator client only after checking
   the existing lab route; do not change host/router/network settings implicitly.
5. OpenBao's `hostAliases` resolves only its Keycloak issuer hostname to the
   observed existing Traefik ClusterIP `10.43.163.193`. This preserves issuer and
   certificate verification without changing cluster DNS. NetworkPolicy permits
   that service's 443 and selected Traefik pods' 8443 for pre/post-DNAT behavior.
   Confirm this IP and labels before applying; change lab values explicitly if
   they differ. Kubernetes API allows are only `10.43.0.1:443` and
   `192.168.122.201:6443`. No public internet egress is permitted. DNS is limited
   to `kube-system` pods labeled `k8s-app=kube-dns`, TCP/UDP 53. Live Canal/DNAT
   tests remain required; rendered policy is not enforcement evidence.

## Initialization, auth and recovery custody

The approved lab model is Corey as single recovery operator, one Shamir share
and threshold one, in a dedicated protected workstation `.secrets/openbao/`
subdirectory. Keep root login token handling distinct from the unseal key share.
The age identity and encrypted backups are colocated on that workstation by
explicit user preference; laptop/disk loss remains an unmitigated shared risk.
The future three-node custody options below are not selected for this trial.

For the approved new lab instance, check initialization status first. With
`umask 077` and a verified mode-0700 private directory, run native
`bao operator init -key-shares=1 -key-threshold=1 -format=json` with stdout
redirected directly to `recovery/initialization.json`, **never a terminal/CI
log**. Extract the single share only into `recovery/unseal-share` (mode 0600).
Never initialize an existing instance. Supply the share using the hidden native
`bao operator unseal` prompt or API stdin over verified TLS, not process
arguments, environment, Kubernetes Secrets or shell history. Keep the temporary
root token in protected local bootstrap storage only; never put it in a workload
or ESO. A sealed `bao status` returns nonzero; distinguish it from connection
failure. Root revocation and recovery verification are required below.

Use the temporary root session privately for the initial auth configuration:

```sh
python3 local-lab/scripts/configure-keycloak-tenants.py --openbao-only --apply \
  --kubectl /path/to/kubectl --kubeconfig /private/rke2.yaml --secrets-dir /private/platform-secrets
local-lab/openbao/configure.sh --apply \
  /private/platform-secrets/openbao-keycloak-client-secret /public/lab-ca.pem
```

`configure.sh` refuses conflicting KV/auth mount types; writes plain reviewed
HCL policies and JSON roles using the native CLI; configures OIDC discovery,
public CA, audience, exact groups/redirects; and sets Kubernetes auth to use the
OpenBao pod's rotating reviewer token/CA. It neither initializes nor issues an
app token. There is no stored reviewer JWT or privileged default OIDC role.
Role inputs use `openid,profile`, since the groups mapper is directly attached
to this client—no nonexistent `groups` client scope is assumed.

Validate Home and platform login with preapproved users, then revoke the
bootstrap root token using `bao token revoke -self` in that temporary session.
Verify its failure privately. Do not grant root policy to human or ESO roles.
Test recovery access before relinquishing the root session; root regeneration
is a separate multi-custodian operation, not a permanent stored root credential.

## Audit, backup and rotation

The chart now includes native declarative `audit "file" "platform-file"` at
`/openbao/audit/audit.json`, mode 0600, with raw logging disabled. OpenBao enables
it on unseal. Verify the audit device and a synthetic request event before any
real user use; do not use `unsafe_allow_api_audit_creation` or enable raw logging.
Audit files may contain sensitive paths/identifiers and require private custody.

Audit owner checks PVC free space daily and before/after testing. For this small
trial, rotate at 100 MiB or daily: rename the file on the audit PVC, send `SIGHUP`
to the OpenBao server process, then verify a synthetic request reaches the new
file before compressing/copying the old file to the approved encrypted off-VM
archive. OpenBao's documented reopen behavior avoids copytruncate loss. Retain
seven daily archives only after backup verification; deletion is an explicit
retention action. Do not disable auditing to recover capacity. An unwritable
sole audit sink can stop requests; restore space/permissions with the owner.
Automating shipping/rotation is deferred until the destination and custody are
chosen; no extra log sidecar is added.

Before changes and daily during trials, a separately approved backup operator
with only `snapshot-reader` plus ordinary token self-service runs:

```sh
# Public recipient and destination; authenticate privately using an approved session.
export OPENBAO_BACKUP_DIR=/approved/off-vm/openbao
export AGE_RECIPIENT=age1PUBLIC_RECIPIENT
local-lab/openbao/backup.sh --apply
```

The directory must already be operator-owned mode 700. The script saves a native
Raft snapshot privately, age-encrypts it for the independent custodian, writes a
checksum and removes its temporary plaintext on exit. It creates no credentials,
does not install a scheduler, prune old copies or restore data. Keep seven verified
daily snapshots; do not delete the last known good copy. Expected RPO is at most
24 hours only while this daily operation actually happens. RTO remains unmeasured.
No unattended backup identity is fabricated before its approval. Encryption is
in addition to OpenBao's barrier; unseal material still remains separate.

Restore rehearsals use an isolated same-version instance, a new empty data
directory/PVC and no route to application namespaces. Decrypt into an owner-only
temporary file; verify the encrypted checksum first. Native
`bao operator raft snapshot restore -force /private/restore.snap` is needed when
the rehearsal instance has different initial keys. This is destructive to that
**isolated target only** and must never point at the live service. It seals the
target; unseal with the **original snapshot's shares**, then verify its audit,
policies and synthetic marker. Do not use the rehearsal's temporary shares or
leave original root tokens enabled. Keep declarative audit device names/options identical to the snapshot, including
`/openbao/audit/audit.json`; OpenBao rejects changed audit options during
post-unseal. The isolated filesystem/PVC may differ while the in-container path
stays the same. Keep the single-member node identity stable in this lab. Record elapsed
recovery time and destroy only approved temporary rehearsal resources afterward.
A successful local synthetic rehearsal does not prove off-VM backup durability.

After leaf renewal, rerun leaf delivery, allow projected-volume propagation,
send the supported `SIGHUP` to OpenBao and verify the served new leaf/issuer
through internal and browser hostnames. No CA key leaves `cattle-system`.
Automatic renewal delivery remains a separate platform concern (issue #18).
Registry-token issuance/revocation stays at GitHub; update its value privately
in OpenBao and verify the same `portal-ghcr` UID with refreshed data plus a new
private-image pull. Retain the old GitHub token until validation and its explicit
revocation approval. Ordinary Secret updates do not restart existing pods.

## Remaining live acceptance

No live result is claimed for these manifests/helpers. Before operational
readiness: verify TLS/issuer, OIDC group denials, Kubernetes wrong-SA/namespace/
audience denials, cross-tenant network/API denial, Fleet deployer denial,
ESO refresh/retention and pull success, audit continuity, and isolated off-VM
restore. Report limits and preserve failed private evidence. The app repositories
consume standard Secret names only; moving platform app chart bundles into a
future `perkforge-platform-apps` repo does not change these API boundaries.

## Custody options requiring Corey's decision

| Environment | Minimal supported option | Tradeoff |
|---|---|---|
| Single-operator disposable lab | Manual Shamir, 1 share / threshold 1, PGP-encrypted to the operator; independent encrypted offline recovery copy | Simple but one person/key controls unseal and root recovery; no separation of duties. Loss of both copies makes snapshots unusable. |
| Lab with independent available custodians | Manual Shamir, 3 shares / threshold 2, separately encrypted/distributed | Any two custodians can recover; requires real availability and independent storage. Three files held by one person provide no organizational separation. |
| Future three-node Raft service | Three voting members on separate hosts plus either of the explicit custody models above | Raft survives one member failure; it does not replace unseal-key custody, snapshots or backups. With Shamir, every restarted node must be unsealed separately. |

The user approved 1-of-1 manual Shamir for this single-operator lab; future
physical-cluster custody remains a separate decision. Do not encode a 1-of-1 choice merely
because the synthetic test uses it. Do not automate manual Shamir unseal by
putting shares into Kubernetes Secrets. If restart automation later warrants
KMS/HSM/transit auto-unseal, approve that external trust/dependency and recovery-
key custody separately; migration must not be slipped into activation. Avoid
adding a second secrets service solely to bootstrap this small lab.

Official guidance: [seal/unseal and per-node Shamir behavior](https://openbao.org/docs/concepts/seal/),
[native Raft snapshots](https://openbao.org/docs/commands/operator/raft/),
[declarative audit](https://openbao.org/docs/configuration/audit/).


## Approved workstation location; live actions not yet executed

Use `/home/corey/src/perkforge-platform/.secrets/openbao/` on the workstation,
inside the existing ignored `.secrets` folder and outside VM disks, with mode
0700 directories and mode 0600 files. Before any write verify Git ignore/tracking,
owner, parent permissions and absence of symlinks. Do not modify unrelated secrets. Verify it is an ordinary
local filesystem path without symlinked parents or cloud-sync configuration.
Proposed layout:

- `recovery/unseal-share` — local Shamir share, under the approved single-operator 1-of-1 lab
  ceremony. This is an unseal key share, not a reusable login token.
- `recovery/initialization.json` — private initial ceremony output until share
  handling and bootstrap root-token revocation are verified. Preserve any
  retained ceremony record as highly sensitive even after root revocation.
- `keys/backup-age.key` — locally generated age identity, never on a VM, in Git,
  or in Kubernetes. Public recipient can be recorded separately; private key is
  mode 0600. Generation is part of the approved protected local setup, not run by `backup.sh`.
- `backups/` — mode 0700 directory for encrypted `.snap.age` and checksum files.
  Export this exact path as `OPENBAO_BACKUP_DIR` after approval.
- `public/lab-ca.pem` — exported public CA for verified CLI HTTPS.

Approved setup uses native `age-keygen -o keys/backup-age.key` within the
private directory, then `age-keygen -y keys/backup-age.key` to obtain the public
recipient. Never print the private identity. Restore decrypts with that identity
into a mode-0600 temporary file on the workstation and removes the plaintext on
exit. The backup is off the VM, **not off the workstation**: losing the laptop
or its disk can destroy snapshots, encryption key and local unseal material
together. This is the user's local trial preference, not machine-disaster
resilience. No external/cloud destination or second key copy is assumed.


## First live ESO rotation acceptance: synthetic only

After reviewed runtime configuration merges, apply only the standalone
`fleet/gitrepos/openbao.yaml` registration (pin `spec.revision` to the reviewed
merged SHA instead of relying on moving main during the trial). It contains only
support, OpenBao and scoped ESO. It does not select the real pull-secret delivery.
The support bundle provisions boundaries before the new service receives real
credentials. Observe that initialization/unseal intentionally gates readiness.

After TLS/auth/audit and encrypted snapshot/isolated restore succeed, create only
`validation/pull-secret.yaml`: `tenant-home-portal/openbao-rotation-probe` with
known synthetic JSON, unreferenced by applications. Load a synthetic value into
`tenants/home/tenant-home-portal/registry/ghcr`, then use the explicit Fleet
`secrets-config/enrollments/synthetic.yaml` options to render/deliver the store,
identity and mapping to **openbao-rotation-probe**, not `portal-ghcr`. Check the
actual rendered target name before applying. Update the synthetic value and
verify probe Secret UID unchanged, resourceVersion/data digest changed and ESO
Ready; never print real Secret contents. Verify wrong SA/namespace/audience,
foreign paths and Fleet permissions are denied. This proves synchronization,
not a valid private GHCR pull. Real GHCR migration and fresh private-image pull
are a later, specifically approved transition to `portal-ghcr` Merge/Retain.
Do not bootstrap the synthetic target with a real token or point a workload at it.
