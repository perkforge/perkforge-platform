# Local VM RKE2 exercise

This is the reproducible setup for the two disposable libvirt VMs. It is intentionally separate from the physical homelab configuration under [`../ansible/`](../ansible/README.md). See the repository [HANDOFF](../HANDOFF.md) for current live state and resume notes.

See [APPLICATIONS.md](APPLICATIONS.md) for the PerkForge Platform app catalog,
component alternatives, and staged local build plan. The disposable VM harness
remains useful for development while the physical homelab hardware is being
shipped. It is separate from the physical deployment configuration under
`ansible/`.

The provisioning script creates the VMs and installs RHEL 10.2 unattended with Kickstart. Ansible then configures RHEL and installs RKE2.

## Current reduced-resource profile

Nextcloud is the active protected reference tenant. Keycloak's application is
paused at zero replicas, with its database retained; GitLab's PostgreSQL/Valkey
dependencies remain active. Prometheus/Grafana and OpenCost paths are disabled.
Review capacity before resuming Keycloak or enabling additional workloads.

The deployment/rebuild procedures below still assume running Keycloak and are
not health checks for this profile. A rebuild deletes both VM disks, including
protected Nextcloud data, and requires action-specific authorization and the
applicable backup/recovery decision. See the current [handoff](../HANDOFF.md).

## What this automates

- Configures the attached RHEL DVD as persistent local BaseOS and AppStream repositories.
- Checks RHEL 10 and SELinux enforcing mode, installs `kernel-modules-extra`, excludes Canal interfaces from NetworkManager, and disables firewalld for this isolated NAT exercise.
- Installs the pinned RKE2 server and agent RPMs, configures the server and joins the worker, and keeps the join token out of Ansible output.
- Retrieves the cluster kubeconfig and bundled `kubectl` into the ignored `.secrets/` directory.
- Installs Rancher and cert-manager on the local RKE2 cluster, exposing the UI through RKE2's built-in Traefik ingress.

The script expects a Linux host with libvirt's `default` NAT network (`192.168.122.0/24`) and the RHEL 10.2 x86_64 DVD ISO at `images/rhel-10.2-x86_64-dvd.iso`. It checks the ISO checksum and volume label, creates DHCP reservations for `.201` and `.202`, and creates two 2-vCPU, 4-GiB VMs with a 30-GiB control disk and a 100-GiB worker disk in the libvirt `images` pool. The ISO stays in `images/`, and VM disks are ignored by Git. The script creates a lab SSH key and console password in ignored `.secrets/`, injects the public key into the RHEL install, and records the new SSH host keys there. It uses direct libvirt access when available and asks for sudo only when needed. RHEL remains unregistered, so it will not receive Red Hat CDN updates.

Existing VMs and disks are left intact. For a VM created during the current provisioning run, the provisioner monitors DVD and root-disk I/O while waiting for SSH. If both remain idle for six minutes, it automatically discards that incomplete new VM and retries the unattended install once. It never applies this retry to a pre-existing VM. If a VM definition is missing while its disk remains, the script stops for manual review. If both laptop and VMs are lost, download the ISO again from Red Hat; it is not stored in Git.

## Prepare the Ansible controller

On Debian or Ubuntu, install libvirt, the VM tools, Ansible, and the SSH client:

```sh
sudo apt update
sudo apt install libvirt-daemon-system libvirt-clients virtinst qemu-utils ansible-core openssh-client openssl util-linux
```

Download the RHEL 10.2 x86_64 DVD ISO from Red Hat, put it at `images/rhel-10.2-x86_64-dvd.iso`, then provision the VMs from the repository root:

```sh
local-lab/scripts/provision-vms.sh
```

The script asks for sudo when it needs access to system libvirt and waits for both RHEL installs to accept SSH. It keeps the DVD attached to both VMs for their local package repositories. It generates a lab-only SSH key and console password if they do not already exist; that password is also used for Ansible privilege escalation and is stored in `.secrets/rhel-lab-console-password`. Keep `.secrets/` private; it is ignored by Git.

The worker uses an explicit Kickstart LVM layout: 2-GiB `/boot`, 3-GiB swap,
and a root XFS logical volume that grows into the remaining capacity (about
95 GiB). This keeps space available to `/opt/local-path-provisioner` rather than
a separate `/home`. The provisioning script leaves existing VM disks untouched;
its 100-GiB setting applies to newly created workers, including a future approved
full rebuild. On 2026-10-26 the existing worker was separately expanded online
from 30 to 100 GiB with its partition, PV, root LV and XFS filesystem grown.
No VM reboot, disk formatting or physical-disk partition changes were required.

## Tenant foundation

The synthetic tenant foundation is managed by the existing Fleet bundle at
`local-lab/fleet/bundles/tenant-foundation/`. Its input is
`local-lab/tenant-config/tenants.yaml`, a small index containing cluster settings
and explicit `tenantFiles` references. Edit the individual tenant files under
`local-lab/tenant-config/tenants/`; validate or render before changing the
applied manifests. The renderer and tests use the pinned dependency in
`local-lab/requirements.txt` (PyYAML 6.0.2), plus Helm 3.19 for offline rendering.
Shared declarative resources live in `local-lab/templates/tenant-foundation/`;
Python retains validation and safe file writing. No Helm install is performed.

```sh
python3 local-lab/scripts/render-tenant-foundation.py --check
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s local-lab/tests -v
```

Use `--write` to regenerate the bundle files after editing the catalog.
That command only changes local generated files; it does not contact or
modify the cluster. Shared roles and per-tenant output are organized as:

```text
tenant-config/
  tenants.yaml                  # cluster settings and explicit file index
  tenants/
    tenant-alpha.yaml
    tenant-bravo.yaml
    home.yaml
fleet/bundles/tenant-foundation/
  fleet.yaml                    # existing Fleet bundle identity
  shared/roletemplates.yaml
  tenants/<tenant-id>/
    project.yaml
    namespaces.yaml
    quotas.yaml
    limits.yaml
    networkpolicies.yaml
```

These subdirectories remain part of the same Fleet bundle; there are no nested
`fleet.yaml` files or resource-ownership transfers. Home's application bundles
remain in the separate Nextcloud repository. The loader resolves only explicitly
listed tenant YAML files, so stray files cannot silently create tenants. The
renderer validates all tenants together, including duplicate IDs, namespaces,
Projects and aggregate budget limits. Existing scripts share this loader.
Legacy inline catalogs and an explicit `--output /path/to/combined.yaml` remain
supported. `--check` checks the entire generated tree and rejects stale output.
Removing a tenant from the index removes its generated YAML on `--write`, which
can cause live resource deletion after publication. Protected tenant removal
still requires separate approval and a verified backup. Tenant budgets are aggregate ceilings, and the renderer
rejects environment allocations that exceed them. The renderer emits stable
Rancher Project IDs with project-wide budget ceilings, custom tenant
administrator/developer/viewer RoleTemplates, namespace associations, and
namespace-scoped controls. The existing namespaces and
identifiers are preserved. Keycloak groups are represented by explicit
full-path role groups (`/tenants/<tenant>/<role>`). For each namespace, the
renderer sets Rancher's `field.cattle.io/resourceQuota` annotation to the
environment's catalog allocation. [Rancher's project quota guide](https://rancher.github.io/product-docs-playbook/rancher-manager/v2.15/en/cluster-admin/project-admin/project-resource-quotas/resource-quotas-in-projects.html)
documents that Kubernetes-created project namespaces use this annotation to
reserve a specific share of the project-wide quota pool. Preview the Keycloak-side realm,
client, and group configuration with:

For each namespace, the renderer sets Rancher's `field.cattle.io/resourceQuota`
annotation to the environment's catalog allocation. Rancher's project quota
guide documents that Kubernetes-created project namespaces use this annotation
to reserve a specific share of the project-wide quota pool.

```sh
python3 local-lab/scripts/configure-keycloak-tenants.py
```

After Keycloak is healthy, `--apply` reconciles the dedicated `perkforge` realm,
confidential Rancher OIDC client, full-path `groups` token mapper, and catalog
groups and six role-scoped synthetic accounts. It uses a loopback-only kubectl
port-forward and stores the client secret and synthetic account passwords
under ignored `.secrets/`; it does not print credential values or enable
Rancher authentication. The Keycloak chart fixes its
public issuer URL and enables dynamically resolved backchannel URLs so Rancher
can use the in-cluster Keycloak service while users reach the public ingress.
The current lab uses HTTP for Keycloak and self-signed TLS for Rancher; this is
specific to the isolated lab and must be replaced with trusted TLS for a real
deployment. Rancher provider activation and a successful browser login remain
separate steps.

Once Fleet has created the Rancher Projects, preview project role bindings
using:

```sh
python3 local-lab/scripts/reconcile-tenant-rancher-bindings.py
```

The reconciler reads each project's actual `status.backingNamespace`, verifies
catalog ownership, and plans one Rancher ProjectRoleTemplateBinding per
Keycloak group and role. It refuses to adopt a conflicting project or binding.
It is plan-only by default. `--apply` is intentionally separate and refuses to
run unless Rancher Keycloak OIDC reports enabled; it then applies only the
catalog-owned group bindings. A live Playwright run using the synthetic
`tenant-alpha-viewers` account passed 10/10 checks for Keycloak login, Alpha
project visibility, denied Bravo project/workload access, and denied secret
listing. It used the local-only TLS bypass described below. Membership
revocation, session expiry, and CAC authentication remain unverified. The
Kubernetes API suites separately passed RBAC (94/94), Pod Security Admission
(9/9), quota (4/4), and network (7/7). See
[the security boundary](../docs/TENANT-SECURITY-BOUNDARY.md) for evidence scope.

### Browser SSO and Rancher tenant access

Install the separate, pinned browser-test dependency and Chromium in a Python
virtual environment:

```sh
python3 -m venv .venv-e2e
. .venv-e2e/bin/activate
python -m pip install -r local-lab/requirements-e2e.txt
python -m playwright install chromium
```

The read-only test uses a synthetic user's password file under `.secrets/`,
creates an ephemeral browser context, and does not save screenshots, traces,
cookies, tokens, or browser state:

```sh
python local-lab/scripts/verify-rancher-tenant-ui.py --allow-local-tls-bypass
```

The flag is only for the self-signed certificate in this disposable `local-lab`
and disables Chromium's TLS verification for that run. Use a normally trusted
certificate without the flag in other environments. The test does not simulate
CAC/PIV middleware or card/PIN prompts; those require a separate approved,
attended identity test. It also does not verify Keycloak membership revocation
or session expiry.

After OIDC, Projects, RoleTemplates, and PRTBs are active, verify the resulting
Kubernetes authorization and write JSON/Markdown evidence with:

```sh
python3 local-lab/scripts/verify-tenant-rbac.py
```

The runner preflights that Rancher OIDC and the catalog-owned bindings exist,
then checks expected allowed and denied operations for each synthetic role,
including secret access, role and RoleBinding edits, service-account token
creation and impersonation, Pod exec, namespace creation, cluster-scoped
resources, and cross-tenant operations across every catalog environment. It
records the run under
`local-lab/evidence/tenant-rbac/`. The evidence explicitly scopes this to
Kubernetes authorization; it does not claim to prove browser login, group
issuance, dashboard behavior, admission, quota admission, or network isolation.

After the tenant foundation policies are installed, preview network checks with:

```sh
python3 local-lab/scripts/verify-tenant-network.py
```

The default is plan-only. `--apply` creates short-lived, restricted BusyBox
probe Pods, Services, and ConfigMaps in the first two catalog tenant
namespaces; verifies same-tenant HTTP connectivity and cross-tenant HTTP
denial in both directions, tenant egress to Keycloak's OIDC discovery endpoint,
DNS access from each tenant, and removes only resources labeled with that run's
unique ID. It writes timestamped JSON and Markdown evidence under
`local-lab/evidence/tenant-network/`. The probe image must be available from
the node cache or a reachable registry. The script needs sufficient namespace
quota and a working image pull path. Cross-tenant denial shows that the
combined boundary blocked traffic; it does not isolate whether source egress
or destination ingress policy caused the block. These checks do not cover
external egress, ingress-controller behavior, host networking, or node-local
traffic.

To validate the namespace Pod Security Admission baseline without persisting
Pods, preview its server-side dry-run matrix with:

```sh
python3 local-lab/scripts/verify-tenant-admission.py
```

`--apply` sends API server-side dry-run create requests for one compliant Pod
and eight expected violations (privilege, host access, root, privilege
escalation, seccomp, and capabilities). The API server must report a
PodSecurity violation for each negative case; authorization or unrelated API
errors do not count as a passing denial. No resources are persisted, although
the request requires API access and admission evaluation. JSON and Markdown
evidence are written under `local-lab/evidence/tenant-admission/`. This
verifies Pod Security Admission only; it does not prove runtime behavior or
other admission policies.

The namespace quota and defaulting probe is also plan-only by default:

```sh
python3 local-lab/scripts/verify-tenant-quota.py
```

`--apply` server-side dry-runs a Pod relying on LimitRange defaults, an in-budget
Pod, and Pods whose CPU or memory requests exceed the namespace ResourceQuota.
Quota denials count only when the API reports a ResourceQuota violation; other
API errors are failures. Evidence is stored under
`local-lab/evidence/tenant-quota/`. Before testing admission, the verifier checks
the Rancher project ceiling, catalog ownership, each namespace's project
association and reserved project-quota allocation, and all catalog
ResourceQuota keys. The dry-run requests do not prove aggregate quota
consumption across multiple namespaces, PVC storage admission, runtime CPU
throttling, or live scheduling.

After the optional Prometheus/Grafana profile is enabled and ready, the
observability verifier can check tenant attribution and network boundaries:

```sh
python3 local-lab/scripts/verify-tenant-observability.py
```

The default is plan-only. `--apply` checks that Prometheus exposes the catalog
tenant/environment/isolation labels, that tenant NetworkPolicies permit the
Prometheus scrape path without granting tenant egress to observability, and
that Prometheus/Grafana/OpenCost services have no Ingress or non-ClusterIP
exposure. It creates a restricted short-lived Pod per catalog namespace and
checks DNS plus denied HTTP access to Prometheus and Grafana. The verifier
removes only probe Pods labeled with its unique run ID and writes sanitized
evidence under `local-lab/evidence/tenant-observability/`. Live mode requires
the optional services to be ready and enough namespace quota for one small Pod
per namespace. It does not validate Grafana data-source query isolation or
tenant dashboard authorization. The dashboard in the Fleet bundle is
platform-operator-only. The observability paths are currently disabled in
`fleet/gitrepos/platform-apps.yaml`. Live verification requires a separately
reviewed capacity decision, profile activation and ready services.


## Run the tenant security suite

The suite runner provides one entry point for the current shared-cluster checks.
It is plan-only by default and makes no Kubernetes API requests:

```sh
python3 local-lab/scripts/run-tenant-security-suite.py
```

To run the checks and generate an overall timestamped summary, each verifier's
detailed JSON/Markdown evidence, and candidate findings from failed checks:

```sh
python3 local-lab/scripts/run-tenant-security-suite.py --apply
```

The default live suite runs RBAC authorization checks, Pod Security Admission
and quota server-side dry-runs, and network-isolation probes. The network
verifier creates temporary Pods, Services, and ConfigMaps, then removes only
resources labeled with its unique run ID. Review its prerequisites above before
running. Each suite continues even if an earlier suite fails, so one run gives
an overall picture. Exit status is `0` when all pass, `1` for test failures,
and `2` when a verifier could not execute or clean up. The suite-level
`summary.json` and `summary.md` live under
`local-lab/evidence/tenant-suite/tenant-suite-<UTC timestamp>/`.
The same directory contains `candidate-findings.json` and
`candidate-findings.md`. They record failed checks that produced an actual
expected/actual mismatch, with evidence links and potential control mappings.
Verifier execution errors are not treated as security findings. Each candidate
is marked untriaged with risk unassessed and owner/remediation unassigned; the
runner does not decide severity, accept risk, or close findings.

The optional observability verifier is excluded by default because it requires
the optional monitoring profile to be installed:

```sh
python3 local-lab/scripts/run-tenant-security-suite.py --apply --include-observability
```

Use `--context`, `--kubeconfig`, and `--kubectl` to select the target explicitly.
Do not treat the dashboard summary as a substitute for the detailed per-run
evidence or human review of findings.

## One-command local lab rebuild

To tear down and recreate the complete local lab without intermediate prompts, run this from the repository root:

```sh
local-lab/scripts/rebuild-local-lab.sh --confirm-destroy
```

This removes both VM disks and the data on them, provisions RHEL, completes Ansible host configuration, installs RKE2, waits for both nodes to become Ready, installs Rancher, then deploys the conservative Fleet profile: Keycloak and the GitLab database/Valkey dependencies. The profile also reconciles the dedicated Keycloak tenant realm, Rancher OIDC client, group claim mapper, and synthetic tenant groups; it does not enable Rancher OIDC. The GitLab application, Harbor Fleet bundle, and Mattermost remain opt-in because the two 4-GiB VMs have limited memory. The ISO and `.secrets/` are preserved. Before teardown, the script checks direct libvirt access, the ISO checksum, required tools, and that the Fleet configuration on `origin/main` matches the local files. It never asks for a sudo password: if direct libvirt access is unavailable, it stops before teardown. Ansible uses the private VM password file. A failed command stops the run and saves the full output in `.secrets/local-lab-rebuild-*.log`.

After deployment, the script verifies the expected Fleet revision and bundle readiness, waits for all Keycloak and GitLab dependency pods, sends a Valkey `PING`, checks the Keycloak ingress over HTTP, and checks Rancher's `/ping` endpoint. A successful exit therefore means those checks passed, not just that Fleet accepted the bundles. The script records progress in `.secrets/local-lab-rebuild-state`. If a stage fails after teardown completed, rerun with `local-lab/scripts/rebuild-local-lab.sh --resume`; this preserves VM disks and reruns the idempotent provisioning and deployment stages. If a failure occurred during teardown, the checkpoint prevents resume so the VM and disk state can be reviewed before another destructive run. The full rebuild uses `--confirm-destroy`; when Codex runs it, one approval at launch covers the entire command and no intermediate prompts are requested.

When you want to remove the VMs, preview the teardown first:

```sh
local-lab/scripts/teardown-vms.sh
```

To proceed, add `--apply` and type the requested confirmation phrase:

```sh
local-lab/scripts/teardown-vms.sh --apply
```

It shuts down and undefines only `cks-control` and `cks-worker`, then removes only same-named qcow2 disks referenced by those VM definitions. It never force-powers-off a VM. DHCP reservations, ISO files, and `.secrets/` are preserved. If the guests do not shut down cleanly or have snapshots, it stops for manual review.

## Manual staged setup

Use these commands only when intentionally running the setup stage by stage. Do not run them again after the one-command rebuild completes:

```sh
ANSIBLE_CONFIG=local-lab/ansible/ansible.cfg ansible-playbook --become-password-file .secrets/rhel-lab-console-password local-lab/ansible/playbooks/configure-hosts.yml
ANSIBLE_CONFIG=local-lab/ansible/ansible.cfg ansible-playbook local-lab/ansible/playbooks/install-rke2.yml
ANSIBLE_CONFIG=local-lab/ansible/ansible.cfg ansible-playbook local-lab/ansible/playbooks/install-rancher.yml
```

Then inspect the cluster:

```sh
.secrets/kubectl --kubeconfig .secrets/rke2.yaml --context default get nodes -o wide
```

If `k9s` is installed, open the direct RKE2 context without changing the default kubeconfig with `k9s --kubeconfig .secrets/rke2.yaml`.

The repository kubeconfig `.secrets/rke2.yaml` uses context `default`. The workstation file `~/.kube/config` currently contains only the direct `rke2-lab` context, copied from the repository configuration after the Rancher-proxy context failed CA verification. Context names are local to each file: use `--context default` with `.secrets/rke2.yaml`, or `--context rke2-lab` with `~/.kube/config`. Inspect names safely with `kubectl --kubeconfig <file> config get-contexts`. The private repository kubeconfig remains the source for lab scripts. Rancher can generate a fresh kubeconfig from its cluster page if Rancher-proxy access is needed. See [Rancher access-cluster documentation](https://ranchermanager.docs.ranchermanager.com/how-to-guides/new-user-guides/manage-clusters/access-clusters/) and [Rancher kubeconfig token settings](https://ranchermanager.docs.ranchermanager.com/api/api-tokens).

The local Rancher UI is at <https://rancher.local-lab.test>. Mattermost is at <http://mattermost.local-lab.test>. These `.test` names resolve through local hosts-file entries to the control VM:

```text
192.168.122.201 rancher.local-lab.test keycloak.local-lab.test mattermost.local-lab.test
```

## Deploy local platform applications with Fleet

`local-lab/fleet/` contains separate Fleet GitRepos for the disposable lab foundation and platform applications. The `local-lab` GitRepo manages storage, tenant foundations, and the CloudNativePG operator. The current `platform-apps` profile retains Keycloak at zero application replicas, its database, and GitLab's PostgreSQL/Valkey dependencies. The GitLab application, Harbor, and Mattermost paths remain available but disabled until node memory is reviewed. Add or remove paths in `fleet/gitrepos/platform-apps.yaml` to select a profile. The GitLab database and Valkey are separate Fleet bundles under `gitlab-dependencies/`, so Fleet can process the database manifest and Helm chart independently.

The platform baseline can be installed directly from the checked-out configuration with:

```sh
local-lab/scripts/deploy-platform-baseline.sh
```

It creates local credentials in ignored `.secrets/`, installs the Keycloak and GitLab databases, then installs Keycloak, Harbor, and GitLab. Password files are owner-only: `keycloak-admin-password`, `harbor-admin-password`, and `gitlab-root-password` (the last appears once GitLab initializes). Keycloak admin username is `admin`; Harbor username is `admin`; GitLab username is `root`. It does not print passwords. The script uses Helm directly so it can run before Fleet sees local unpushed changes; the Fleet GitRepo continues to track `origin/main` and will reconcile these app bundle paths after they are pushed and the GitRepo is refreshed.

This initial GitLab profile disables GitLab Runner to keep the first deployment smaller. GitLab can host groups and projects, but CI pipelines will remain pending until a Runner is configured. GitLab object storage is also disabled for this local profile, so uploads and artifacts use local storage. Harbor uses a self-signed generated ingress certificate. These are deliberate local-only settings to revisit when sizing the lab; they are not suitable for production. GitLab's own minimum example disables Runner and targets a single-user test deployment; its chart's standard target is much larger than these two 4-GiB VMs ([minimum profile](https://gitlab.com/gitlab-org/charts/gitlab/-/raw/master/examples/values-gke-minimum.yaml), [resource guidance](https://docs.gitlab.com/charts/installation/cloud/)).

Keycloak is paused at zero application replicas to reserve memory for Nextcloud; its database and GitLab's database/Valkey dependencies remain active. The GitLab application has not been installed. Keycloak retains its `cks-worker` placement configuration for a future reviewed resumption. Prometheus/Grafana and OpenCost were briefly reconciled during a rollout that coincided with a control-node OOM that killed `kube-apiserver`; the OpenCost pod also crash-looped on the control node because its chart node selector was at the wrong value path. The value path is corrected, but both observability Fleet paths are disabled. Keep them disabled on the two 4-GiB VMs until the cluster has adequate memory. GitLab, Harbor, and Mattermost remain opt-in. Harbor's documented minimum is 4 GB by itself ([Harbor prerequisites](https://goharbor.io/docs/main/install-config/installation-prereqs/)).

The optional Prometheus/Grafana and OpenCost profile is documented in
[`../docs/OBSERVABILITY-AND-COST.md`](../docs/OBSERVABILITY-AND-COST.md). It is
paused in the active Fleet profile after a control-node OOM. When enabling both paths in
`fleet/gitrepos/platform-apps.yaml`, `deploy-platform-profile.sh` prepares the
Grafana admin secret and waits for both Fleet bundles and their workloads.
Access remains platform-operator-only; tenant-safe Grafana access is not yet
implemented.

Before applying any profile with Prometheus/Grafana enabled,
`deploy-platform-profile.sh` runs `check-profile-capacity.py`. It requires at
least 1 GiB estimated headroom on the control node and 2 GiB on the worker; when
OpenCost is enabled, the worker minimum is 2.5 GiB. It compares node
allocatable memory to Metrics API working-set usage and fails closed if metrics
are unavailable. This is an early guard, not a capacity guarantee or a
replacement for watching actual memory and OOM events.

After adding these host entries on the laptop, open the app URLs:

```text
192.168.122.201 harbor.local-lab.test gitlab.local-lab.test
```

Keycloak: <http://keycloak.local-lab.test/auth/>. Harbor: <https://harbor.local-lab.test>. GitLab: <http://gitlab.local-lab.test>. Harbor's certificate is self-signed, so the browser will warn until the local CA/certificate is trusted.

This is a learning setup: the local-path provisioner stores each volume on one VM, so it does not provide node-failure recovery or backups. Mattermost file storage and PostgreSQL data will be lost if their VM disk is deleted. The configuration is single replica and has no TLS; do not expose it outside the lab.

After these changes are available on the repository's `main` branch, bootstrap the GitRepo and its local-only database credentials with:

```sh
local-lab/scripts/deploy-mattermost.sh
```

The script prepares the platform chart credentials, creates the Mattermost namespace and randomly generated PostgreSQL credentials on the cluster, stores the Mattermost password in ignored `.secrets/mattermost-db-password`, then applies the `local-lab` and `platform-apps` GitRepos in Fleet's `fleet-local` namespace. Fleet watches the configured bundle paths on `main`; changes pushed to those paths are reconciled automatically. The script is for an explicitly enabled full application profile. It checks that Keycloak, both GitLab dependency bundles, GitLab, Harbor, and Mattermost paths are active before creating credentials, then waits for the full Fleet bundle set and Mattermost pods. The default rebuild uses `deploy-platform-profile.sh` instead. To inspect progress:

```sh
.secrets/kubectl --kubeconfig .secrets/rke2.yaml -n fleet-local get gitrepo,bundles
.secrets/kubectl --kubeconfig .secrets/rke2.yaml -n mattermost get pods,pvc
.secrets/kubectl --kubeconfig .secrets/rke2.yaml -n gitlab get pods,ingress,pvc
```

The generated database password is local to this VM exercise and is not stored in Git. Keep `.secrets/` private. These Fleet files are separate from the physical homelab Ansible configuration. Mattermost has no seeded admin account or password. Create the first account through the UI; Mattermost assigns that first user the System Admin role. See [Mattermost roles](https://docs.mattermost.com/end-user-guide/collaborate/learn-about-roles).

For Rancher, the initial username is `admin`; the bootstrap password is in `.secrets/rancher-bootstrap-password`. This is separate from any updated password stored in `.secrets/rancher-admin-password`. Rancher uses a self-signed certificate for this disposable lab, so the browser will show a certificate warning. This one-replica install is for learning on the small two-VM cluster, not for a highly available management server.

After changing the admin password at first login, store the new password in the ignored local secrets directory with `local-lab/scripts/store-rancher-password.sh`. It prompts without displaying the password and saves it as `.secrets/rancher-admin-password` with owner-only permissions.

The inventory, RHEL DVD label, RKE2 version, network ranges, and firewalld behavior are in `local-lab/ansible/`. Change them there when intentionally changing this local VM exercise. Do not copy these VM addresses or variables into the physical homelab inventory.

### Household application catalog

Home's disabled portal is an `applications.portal` entry in its existing tenant
record, rendered through the same foundation command. See
[`PORTAL-INTEGRATION.md`](../docs/PORTAL-INTEGRATION.md) for identity wiring,
offline previews, preservation-oriented lifecycle and activation gates. No new
portal objects enter the active bundle while the application is disabled.
