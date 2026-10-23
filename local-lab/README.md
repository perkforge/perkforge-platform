# Local VM RKE2 exercise

This is the reproducible setup for the two disposable libvirt VMs. It is intentionally separate from the physical homelab configuration under [`../ansible/`](../ansible/README.md). See the repository [HANDOFF](../HANDOFF.md) for current live state and resume notes.

See [APPLICATIONS.md](APPLICATIONS.md) for the PerkForge Platform app catalog,
component alternatives, and staged local build plan. The disposable VM harness
remains useful for development while the physical homelab hardware is being
shipped. It is separate from the physical deployment configuration under
`ansible/`.

The provisioning script creates the VMs and installs RHEL 10.2 unattended with Kickstart. Ansible then configures RHEL and installs RKE2.

## What this automates

- Configures the attached RHEL DVD as persistent local BaseOS and AppStream repositories.
- Checks RHEL 10 and SELinux enforcing mode, installs `kernel-modules-extra`, excludes Canal interfaces from NetworkManager, and disables firewalld for this isolated NAT exercise.
- Installs the pinned RKE2 server and agent RPMs, configures the server and joins the worker, and keeps the join token out of Ansible output.
- Retrieves the cluster kubeconfig and bundled `kubectl` into the ignored `.secrets/` directory.
- Installs Rancher and cert-manager on the local RKE2 cluster, exposing the UI through RKE2's built-in Traefik ingress.

The script expects a Linux host with libvirt's `default` NAT network (`192.168.122.0/24`) and the RHEL 10.2 x86_64 DVD ISO at `images/rhel-10.2-x86_64-dvd.iso`. It checks the ISO checksum and volume label, creates DHCP reservations for `.201` and `.202`, and creates two 2-vCPU, 4-GiB, 30-GiB VMs in the libvirt `images` pool. The ISO stays in `images/`, and VM disks are ignored by Git. The script creates a lab SSH key and console password in ignored `.secrets/`, injects the public key into the RHEL install, and records the new SSH host keys there. It uses direct libvirt access when available and asks for sudo only when needed. RHEL remains unregistered, so it will not receive Red Hat CDN updates.

The provisioner never deletes or overwrites an existing VM or disk. Existing VMs are started and left intact. If a VM definition is missing while its disk remains, the script stops for manual review. If both laptop and VMs are lost, download the ISO again from Red Hat; it is not stored in Git.

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

## One-command local lab rebuild

To tear down and recreate the complete local lab without intermediate prompts, run this from the repository root:

```sh
local-lab/scripts/rebuild-local-lab.sh --confirm-destroy
```

This removes both VM disks and the data on them, provisions RHEL, completes Ansible host configuration, installs RKE2, waits for both nodes to become Ready, installs Rancher, then deploys the conservative Fleet profile: Keycloak and the GitLab database/Valkey dependencies. The GitLab application, Harbor Fleet bundle, and Mattermost remain opt-in because the two 4-GiB VMs have limited memory. The ISO and `.secrets/` are preserved. Before teardown, the script checks direct libvirt access, the ISO checksum, required tools, and that the Fleet configuration on `origin/main` matches the local files. It never asks for a sudo password: if direct libvirt access is unavailable, it stops before teardown. Ansible uses the private VM password file. A failed command stops the run and saves the full output in `.secrets/local-lab-rebuild-*.log`.

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
.secrets/kubectl --kubeconfig .secrets/rke2.yaml get nodes -o wide
```

If `k9s` is installed, open the direct RKE2 context without changing the default kubeconfig with `k9s --kubeconfig .secrets/rke2.yaml`.

The default `~/.kube/config` currently uses context `rancher-local`, which proxies kubectl traffic through Rancher. The direct RKE2 kubeconfig remains in `.secrets/rke2.yaml`; its context is `default`. Rancher can generate a fresh kubeconfig from its cluster page if the Rancher token expires. See [Rancher access-cluster documentation](https://ranchermanager.docs.ranchermanager.com/how-to-guides/new-user-guides/manage-clusters/access-clusters/) and [Rancher kubeconfig token settings](https://ranchermanager.docs.ranchermanager.com/api/api-tokens).

The local Rancher UI is at <https://rancher.local-lab.test>. Mattermost is at <http://mattermost.local-lab.test>. These `.test` names resolve through local hosts-file entries to the control VM:

```text
192.168.122.201 rancher.local-lab.test keycloak.local-lab.test mattermost.local-lab.test
```

## Deploy local platform applications with Fleet

`local-lab/fleet/` contains separate Fleet GitRepos for the disposable lab foundation and platform applications. The `local-lab` GitRepo manages storage, tenant foundations, and the CloudNativePG operator. The conservative `platform-apps` profile manages Keycloak and GitLab's PostgreSQL/Valkey dependencies. The GitLab application, Harbor, and Mattermost paths remain available but disabled until node memory is reviewed. Add or remove paths in `fleet/gitrepos/platform-apps.yaml` to select a profile. The GitLab database and Valkey are separate Fleet bundles under `gitlab-dependencies/`, so Fleet can process the database manifest and Helm chart independently.

The platform baseline can be installed directly from the checked-out configuration with:

```sh
local-lab/scripts/deploy-platform-baseline.sh
```

It creates local credentials in ignored `.secrets/`, installs the Keycloak and GitLab databases, then installs Keycloak, Harbor, and GitLab. Password files are owner-only: `keycloak-admin-password`, `harbor-admin-password`, and `gitlab-root-password` (the last appears once GitLab initializes). Keycloak admin username is `admin`; Harbor username is `admin`; GitLab username is `root`. It does not print passwords. The script uses Helm directly so it can run before Fleet sees local unpushed changes; the Fleet GitRepo continues to track `origin/main` and will reconcile these app bundle paths after they are pushed and the GitRepo is refreshed.

This initial GitLab profile disables GitLab Runner to keep the first deployment smaller. GitLab can host groups and projects, but CI pipelines will remain pending until a Runner is configured. GitLab object storage is also disabled for this local profile, so uploads and artifacts use local storage. Harbor uses a self-signed generated ingress certificate. These are deliberate local-only settings to revisit when sizing the lab; they are not suitable for production. GitLab's own minimum example disables Runner and targets a single-user test deployment; its chart's standard target is much larger than these two 4-GiB VMs ([minimum profile](https://gitlab.com/gitlab-org/charts/gitlab/-/raw/master/examples/values-gke-minimum.yaml), [resource guidance](https://docs.gitlab.com/charts/installation/cloud/)).

The local VMs currently run Keycloak, Harbor, and GitLab's database/Valkey dependencies. A prior Harbor upgrade OOM-killed its PostgreSQL pod while memory was high, and the GitLab application has not been installed. The one-command rebuild therefore applies only the conservative Fleet profile. Enable GitLab, Harbor, or Mattermost bundles after reviewing node headroom or increasing VM memory. Harbor's documented minimum is 4 GB by itself ([Harbor prerequisites](https://goharbor.io/docs/main/install-config/installation-prereqs/)).

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
