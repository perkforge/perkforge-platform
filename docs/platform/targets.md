# Add a cluster or environment

`local` means an engineer-owned physical cluster. A cluster name, environment, provider/distribution, hosting location and impact profile are independent. One environment can serve multiple named clusters. Only local/il2 is supplied; IP allocation is not RHEL installation.

## Create a named target such as dev

1. Copy `big-bang-bootstrap/clusters/local/` to `clusters/dev/`. Change the cluster/environment annotations in its kustomization, configure `values.yaml` and `identity.yaml`, and select the appropriate provider and impact profile. No mandatory nested folder per label is needed. Add a shared environment values input only when real reuse warrants it, with an explicit valuesFrom position and precedence tests.
2. Add `dev` to `configuration/ansible/inventory.yaml`: gitops_path `./big-bang-bootstrap/clusters/dev`, deployment_environment `dev`, impact_profile `il2`, protected kubeconfig/context, actual kube-system UID, published tag/evidence and pinned Big Bang checkout. Never commit private inventory or credentials. Infrastructure RHEL/SSH/network/storage preparation is separate.
3. Change node/storage placeholders, hostnames, issuer/audience/callbacks, TLS/CA and Secret references consistently. `identity.yaml` supplies target identity inputs; package values and cross-system identity manifests also contain explicit settings and require coordinated review. They are not automatically parameterized from inventory.
4. Choose tenant enrollment as described below. Preserve paused sources/root/release and default-off operation gates until activation review.

**Current limitation:** operational playbooks explicitly restrict the supported target to local/environment local/profile il2 and load its identity inputs. Copying a folder or adding inventory does not make dev executable. Before adopting another target, review/generalize those target guards and vars-file selection, add no-op/wrong-target tests and context/pin/path checks. Do not bypass the guards with CLI overrides.

## Choose tenant enrollment

The shipped local root selects only suspended Longhorn for initial storage acceptance; Rancher follows through a reviewed source change. Headlamp, Keycloak, OpenBao and tenant enrollment are excluded. Enrollment prerequisite apply refuses this unselected root before external access. Optional enrolled-chain tests explicitly opt in temporary fixtures; they do not enable the operator root.

For a later enrolled target, copy `enrollments/local/` to `enrollments/dev/`, select it in the cluster root, and set its Flux reconciliation path to `./clusters/dev` in the enrollment repository. Prepare matching enrollment/app contexts and publish compatible releases. Dependency order is application → enrollment → platform; advance only to real published tags.

For a new tenant-free management/C2 target, omit `../../enrollments/<name>` from the cluster resources and skip `configuration/ansible/enrollment-prerequisites.yaml`. No enrollment source, reconciler or prerequisite RBAC is then required; platform services remain selected independently. An isolated regression verifies the default root contains no enrollment references and explicit temporary opt-in preserves every other platform object. Cross-repository selection tests retain their opt-in contract fixtures; compatible downstream context/pins still require verification before enabling enrollment.

This is not removal guidance for an already enrolled cluster: prune is false and removing Git references does not revoke existing objects or permissions. Review cleanup separately.

## Validate before activation

```sh
kubectl kustomize big-bang-bootstrap/clusters/dev
ansible-playbook -i big-bang-bootstrap/configuration/ansible/inventory.yaml big-bang-bootstrap/configuration/ansible/bootstrap.yaml --syntax-check
# Safe check of the currently supported local template, without enabling apply:
ansible-playbook -i big-bang-bootstrap/configuration/ansible/inventory.yaml big-bang-bootstrap/configuration/ansible/bootstrap.yaml --limit local --check
```

Inspect ordered Helm values and full child renders with the [offline suite](../../big-bang-bootstrap/tests/README.md), including two clusters sharing an environment, context/pin mismatches and enrollment inclusion/omission. Kustomize does not render child charts. Default bootstrap/check mode is no-write; the documented local default walkthrough is not a live installation command for a new target.

After review/release, follow [operation order and containment](../../big-bang-bootstrap/configuration/ansible/README.md). Infrastructure/node access, secrets, trust, security configuration and deployment each require the concrete activation scope. Physical storage/HA/DNS/TLS/backups and comprehensive live tests remain prerequisites, not guarantees supplied by a new directory.

## Authored metadata

Platform-owned selection annotations use `platform.perkforge.io/cluster`,
`platform.perkforge.io/environment` and `platform.perkforge.io/profile`. The profile
is a configuration selection, not an authorization or compliance claim. Package
namespace identity uses `app.kubernetes.io/component`; vendor-owned metadata keeps
its upstream contract. These selection keys must agree across the platform seed,
release verification and enrollment/application repositories before activation.
Changing the prefix requires compatible downstream releases; existing release
evidence alone does not establish that alignment.

## Local DNS and HTTPS

The selected local suffix is `perkforge.home.arpa`, using the residential
special-use domain defined by [RFC 8375](https://www.rfc-editor.org/rfc/rfc8375.html).
The application names are `headlamp.perkforge.home.arpa`,
`keycloak.perkforge.home.arpa`, `rancher.perkforge.home.arpa` and `openbao.perkforge.home.arpa`. Keycloak retains
its `/auth` base path and `perkforge` realm; Headlamp retains client ID
`headlamp-local`. Names, callback/origin, issuer/JWKS and TLS SANs must agree.

The authored values, routes and identity inputs agree on these names. They do not
create DNS records, choose an ingress address, issue certificates or distribute
trust. Before activation, select the LAN ingress endpoint and local DNS owner;
ensure the workstation, node hosts and cluster workloads all resolve the names.
Private-CA certificates and trust must cover browsers, workloads, API-server OIDC
and Rancher agents as applicable. Existing reviewed TLS Secret names stay intact.
Do not bypass certificate validation. DNS, CA/trust and live API-server changes
remain separate reviewed actions; changing source URLs does not activate them.

Read-only ingress inspection found the RKE2-managed `rke2-traefik` DaemonSet
healthy on all three nodes, with host ports 80/443 and a ClusterIP service. The
existing controller can serve a selected worker address without an additional
load balancer for initial lab use. A single address has a worker availability
dependency; multi-address DNS is not a health-checked failover mechanism. The selected initial ingress endpoint is worker-1. A separate dnsmasq host service
is installed and enabled on control-1; direct LAN resolution/forwarding checks
passed. Workstation split DNS and all three node resolver migrations are complete. The
approved CoreDNS rolling refresh and service-level DNS checks passed; TLS and
workload-specific policies remain outstanding. See the infrastructure DNS procedure. The workstation uses
the router as its resolver; router capabilities must be confirmed before choosing
local records, forwarding or an independent resolver. Keep actual addresses in the
ignored topology, not public procedure files.

Published selection annotations are a versioned cross-repository contract. Advance
portal release → enrollment release → platform evidence/pin when that contract
changes; do not accept missing keys, silently fall back to an older namespace or
rewrite released tags. Historical platform v0.1.0 remains a valid immutable ref but
has an incompatible selection schema. CI verifies that ref, then requires explicit
contract rejection; it does not accept that release as current bootstrap input.
