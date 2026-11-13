# ntfy native candidate (#39)

Unselected deployment template, not an installation. No root includes this path.
Render with Ansible/Jinja only after reviewing these required inputs:
`ntfy_namespace`, `ntfy_base_url` (HTTPS public origin), `ntfy_tls_secret`,
`ntfy_storage_class`, `ntfy_storage_size`, `ntfy_cache_duration`.
No production endpoint, capacity, retention policy or recipient is selected here.

The pinned official v2.37.2 image runs as UID/GID 1000, read-only root, without
capabilities or a Kubernetes token. One replica owns SQLite auth/cache files on a
retained RWO PVC; this is not an HA design. Native TLS listens on 8443; HTTP is
disabled. TLS is a separately delivered Secret with tls.crt/tls.key, not data in
Git. Existing runtime credential custody remains OpenBao/ESO. No accounts,
tokens, ACL grants, RBAC bindings, ingress or notification policy are created.
Anonymous topic access is deny-all, signup/web UI/attachments/upstream push are
disabled. Native CLI account/ACL management remains a separate protected step.

Activation still requires namespace and network policy review, storage/backup and
cache-retention decisions, trusted TLS delivery, exact-topic write-only publisher
and read-only subscribers, and external routing. Do not render/enable this as a
substitute for that review. Viewers have Mattermost-only notifications: do not
create ntfy subscriptions for them. A health probe only proves a listening socket,
not trusted TLS, authorization or successful notification delivery.

The shared-team Mattermost decision does not affect this server candidate. Grafana
remains the single grouping/silence/repeat owner. No public push relay is enabled;
mobile background-delivery behavior must be tested before claiming push works.

Offline verification: `PYTHONPATH=big-bang-bootstrap/tests python3 -m unittest
configuration.test_ntfy_deployment -v`. Candidate is not yet cluster-validated.

Optional native smoke (Podman, OpenSSL, pre-pulled pinned image): set
`RUN_NTFY_DEPLOYMENT_NATIVE=1` with the same unittest command. It passed using the
official image in a network-none disposable container: nonroot/read-only startup,
synthetic trusted HTTPS health, anonymous subscribe and publish denied (403).
The synthetic key/data modes permit host-container UID mapping; this does not
validate Kubernetes fsGroup, Secret mode or PVC ownership. Cluster acceptance is
still required. Cleanup is attempted in `finally`; no real credential is read.

Source: [official ntfy configuration](https://docs.ntfy.sh/config/) and the
existing native v2.37.2 TLS/ACL tests in `tests/integration/test_ntfy_native_webhook.py`.

## Trusted ingress candidate

`routing.yaml.j2` follows the existing Harbor HTTPS backend pattern. It defines a
named Traefik ServersTransport with explicit certificate server name and CA
Secret, websecure-only ingress, and a pod policy admitting only the named ingress
controller on 8443. The namespace and pod selectors are in the same peer (AND).
This policy allows no egress; Kubernetes policies are additive, so inspect all
matching policies before claiming effective denial. No external push provider or
attachments is enabled.
This permits responses on established connections but not ntfy-originated network
connections. Actual CNI, ingress and mobile streaming behavior still need testing.

Additional reviewed inputs: `ntfy_hostname`, `ntfy_ingress_tls_secret`,
`ntfy_backend_server_name`, `ntfy_backend_ca_secret`, `ntfy_ingress_namespace`,
`ntfy_ingress_app`. The backend CA Secret contains the public trust certificate in
`ca.crt`; the backend TLS certificate SAN must match `ntfy_backend_server_name`.
`ntfy_base_url` must equal `https://` plus `ntfy_hostname`. Protect the frontend and
backend private keys through the existing approved secret-delivery process. Do
not disable verification or enable plaintext to bypass a routing failure.

The routing Service is an annotated replacement of the deployment Service, not
an additional resource. A future owner must compose/merge these before submission
rather than give two reconcilers the same Service. Neither template is selected or
installed by this source change. Grafana uses the same trusted HTTPS hostname;
its outbound CNI path must be checked separately rather than opening broad egress.

Minimal activation approval batch: selected namespace/PVC and TLS delivery;
ntfy ingress plus pod NetworkPolicy and exact HTTPS backend trust; exact-topic
publisher/subscriber identities and protected runtime custody; then approved
Grafana contact-point/route binding and synthetic firing/resolved acceptance.
No user membership, cross-tenant read, platform administration, public internet
exposure or controller-wide change is implied. Choose local hostname/storage
values in the home-lab configuration, not in this reusable platform template.

Before activation verify the installed Traefik CRD supports `rootCAs` and the
controller resolves the named ServersTransport reference. The existing Harbor
source uses this form; source similarity is not live controller evidence.
