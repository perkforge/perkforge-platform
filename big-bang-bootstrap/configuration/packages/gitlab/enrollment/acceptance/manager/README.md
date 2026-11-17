# Separate tenant runner candidate, unselected

`render.sh --render INPUTS.json` writes only a fresh private output directory.
Strict literal JSON: `context`, `gitlab_origin`, `output_directory`. No secrets,
raw resource overrides or target selection. Default and check mode are inert.
Canonical reserved contexts (including `platform`) are rejected. Names isolate tenants: `gitlab-tenant-<context>-runner` and
`gitlab-tenant-<context>-ci`. Existing Big Bang addon/runner1 is untouched.

This reuses the existing native Big Bang runner chart0.91.2-bb.3 and runner/job
configuration, not a new image/controller. A separate suspended HelmRelease is
owned by a separately scoped installer. Nothing includes it in a live root.
No native Helm render or runtime compatibility is claimed by YAML fixture tests.

Authority to review before activation:
- Foundation operator creates two namespaces, manager/job/installer SAs and scoped
  Roles/Bindings. Manager needs pods/exec/attach, transient Secrets and Services in
  ONLY the tenant job namespace; this is real workload/credential authority.
- Installer manages Deployments/ConfigMaps/Secrets and reads Pods/ReplicaSets ONLY
  in its manager namespace. No ClusterRole, cluster-wide access or self-RBAC grant.
- Manager API token is needed; job API-token mount is false. Dedicated OpenBao/ESO
  runner-token custody, public CA and registry pulls remain missing, not fabricated.
- Job namespace enforces restricted policy and budgets. Manager and jobs start
  default-denied. Only job DNS is permitted by this source. Reviewed target-specific
  manager API/GitLab and job clone/artifact/registry paths are REQUIRED before resume.
  Do not treat a network-denied candidate as a runnable manager.
- Native chart/image pull, scheduling/I/O, rendered RBAC, secret names and bounded
  egress must pass before the separately approved root change/resume/CI enable.

The tenant job image is the previously locally verified maintained Ansible14.6
digest3308322cc09f20a813c00e9087c166a3d97dbb7789c059f1020f3c0b092fdf02,
matching the fixed seed Python smoke ABI; old platform UBI configuration is untouched.
The fixed job image/helper allowlist and no SA/namespace/bearer/label overwrite
preserve the existing confinement model. Tenant runner tag/binding is established
by the separate paused native preparation receipt, not manager registration.
No auto-register, unregister, source migration, runtime token value or event send.

## Optional runtime proposal (render only)

Add a `runtime` object with exactly `bao_server` (HTTPS), `route_hosts` (1–8
unique single-host /32 or /128 CIDRs), `api_host` (single-host CIDR), `api_port`
and `traefik_port` (integer ports). It emits additional `runtime.yaml` and
`runner-policy.hcl`; nothing selects or applies them. Default-deny remains.

The proposed Bao role `tenant-<context>-acceptance-runner` must separately bind
ONLY `eso-tenant-runner` in the manager namespace, audience `openbao-eso`, to the
one-record read policy. No role or secret value is created by this renderer.
Precreate the target without Git-owned data, preserving ESO SSA ownership;
Merge/Retain populates both required chart keys. Auth never enters the job
namespace. The shared ESO controller is still a trust boundary, not a dedicated
controller isolation guarantee.

Public Bao CA ConfigMap, GitLab CA Secret, registry pulls in both namespaces and
approved custody import remain separate prerequisites. Do not reuse the platform
runner delivery helper unchanged. Endpoint rules describe both pre/post-DNAT
paths; validate the selected CNI and Traefik route before activation. An ingress
IP permits its other virtual hosts too: this is network endpoint confinement,
not hostname filtering. API access is manager-only. Image pulls are node-runtime
traffic, not a reason to open job internet egress. Job control-plane exclusion
and all existing security/resource constraints remain unchanged.
