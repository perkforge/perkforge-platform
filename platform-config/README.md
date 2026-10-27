# Platform application API configuration

Fleet owns installation and Kubernetes resources. This small local Ansible
playbook owns only the mutable app settings which chart values do not configure:
Keycloak's dedicated OpenBao client/direct groups mapper, and OpenBao's KV mounts,
ACL policies, OIDC/Kubernetes auth configuration and three explicit roles.

Uses only `ansible.builtin.uri` from pinned `ansible-core==2.19.11`; no Galaxy
collections, custom modules, Python configurators or framework. The maintained
community.general Keycloak integration was considered, but a few explicit
GET/POST/PUT calls avoid another collection while retaining readable native JSON
and HCL desired state. Legacy Keycloak Python scripts are unchanged by this PR.

The user approved this API-configuration approach and bounded lab setup. Do not
run it before reviewing/merging the configuration and completing TLS, private
initialization/unseal and root-token handling. Never use it to issue GitHub
credentials, initialize/unseal automatically, import application secrets, manage
users/memberships, or change other clients. It does not rotate an existing
Keycloak client secret. Existing unowned clients or incompatible mounts fail.

```sh
python3 -m pip install -r platform-config/requirements.txt
ANSIBLE_LOCAL_TEMP=/tmp/perkforge-ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/perkforge-ansible-remote \
ansible-playbook -i localhost, platform-config/configure.yaml --syntax-check
# Static validation only, intentionally no auth or network requests:
ANSIBLE_LOCAL_TEMP=/tmp/perkforge-ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/perkforge-ansible-remote \
ansible-playbook -i localhost, platform-config/configure.yaml --check
```

After approval, run without `--check` using the explicit defaults in `vars.yaml`,
or a private `-e @/private/paths.yaml` containing only reviewed endpoint/path
overrides. The OpenBao bootstrap URL uses a loopback-only port-forward and a
localhost SAN on the issued leaf; the CA is still verified. Keycloak uses its
existing verified public HTTPS issuer. No TLS bypass, redirects or proxy/netrc
authentication are allowed. Do not put passwords/tokens in extra-vars arguments.

Private file inputs must be owned regular mode-0600 files; validate their parent
paths are protected and not symlinks as part of the initialization procedure.
URI calls and sensitive facts use `no_log`; do not add `debug`, verbosity dumps,
fact caching, callbacks or logging that reveals secrets. Credentials remain
in process memory and the existing protected local files. No secret is copied
into tracked files or a new Kubernetes object by this playbook.

Tasks read before writing. Stable second runs produce zero configuration writes.
OpenBao redacts the OIDC client secret when read, so normal comparisons use only
public settings. A deliberate separately approved client-secret rotation must
set `openbao_refresh_oidc_secret:true`; this resubmits the existing Keycloak
credential without generating one. Public configuration drift also resubmits
it as part of the native API payload. Role TTLs are native integer seconds so
read/write comparison matches the API's normalized representation.

`test_platform_config.py` executes the actual playbook against isolated synthetic
HTTPS APIs, checks create/second-run idempotence, conflict refusal, no membership
writes and log redaction. Python is used only for tests/evidence. This fixture
is not proof that live Keycloak/OpenBao responses match every normalization;
run live read-after-write and a second idempotence pass during approved setup.

References: [Ansible URI](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/uri_module.html),
[no_log limitations](https://docs.ansible.com/projects/ansible/latest/reference_appendices/logging.html),
[maintained Keycloak module considered](https://docs.ansible.com/projects/ansible/latest/collections/community/general/keycloak_client_module.html).
