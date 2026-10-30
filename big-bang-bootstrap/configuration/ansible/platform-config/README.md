# Platform application API configuration

Big Bang/Flux owns installation and Kubernetes resources. This small local Ansible
playbook owns only the mutable app settings which chart values do not configure:
Keycloak's dedicated OpenBao client/direct groups mapper, and OpenBao's KV mounts,
ACL policies, OIDC/Kubernetes auth configuration and three explicit roles.

Uses only `ansible.builtin.uri` from pinned `ansible-core==2.19.11`; no Galaxy
collections, custom modules, Python configurators or framework. The maintained
community.general Keycloak integration was considered, but a few explicit
GET/POST/PUT calls avoid another collection while retaining readable native JSON
and HCL desired state. Historical Python configurators remain archived and are not the active configuration path.

The user approved this API-configuration approach and bounded lab setup. Do not
run it before reviewing/merging the configuration and completing TLS, private
initialization/unseal and root-token handling. Never use it to issue GitHub
credentials, initialize/unseal automatically, import application secrets, manage
users/memberships, or change other clients. It does not rotate an existing
Keycloak client secret. Existing unowned clients or incompatible mounts fail.

```sh
python3 -m pip install -r big-bang-bootstrap/configuration/ansible/platform-config/requirements.txt
ANSIBLE_LOCAL_TEMP=/tmp/perkforge-ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/perkforge-ansible-remote \
ansible-playbook -i localhost, big-bang-bootstrap/configuration/ansible/platform-config/configure.yaml --syntax-check
# Static validation only, intentionally no auth or network requests:
ANSIBLE_LOCAL_TEMP=/tmp/perkforge-ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/perkforge-ansible-remote \
ansible-playbook -i localhost, big-bang-bootstrap/configuration/ansible/platform-config/configure.yaml --check
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

`tests/integration/test_openbao_api.py` executes the actual playbook against isolated synthetic
HTTPS APIs, checks create/second-run idempotence, conflict refusal, no membership
writes and log redaction. Python is used only for tests/evidence. This fixture
is not proof that live Keycloak/OpenBao responses match every normalization;
run live read-after-write and a second idempotence pass during approved setup.

References: [Ansible URI](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/uri_module.html),
[no_log limitations](https://docs.ansible.com/projects/ansible/latest/reference_appendices/logging.html),
[maintained Keycloak module considered](https://docs.ansible.com/projects/ansible/latest/collections/community/general/keycloak_client_module.html).

## Platform group contract

The accepted desired hierarchy is in `group-definitions.yaml`: `/platform` with
children `/platform/admins` and `/platform/developers`. Definitions are not
consumed by the live configuration playbook yet: no groups, memberships or new
privilege mappings are created implicitly. A named enrollment decision and
reviewed group lifecycle action are required before creation/grants.

The dedicated OpenBao client maps Keycloak membership into a `groups` claim with
full paths, in ID tokens and userinfo. Each app authorizes exact child paths:

| Group | Current/proposed app authorization |
|---|---|
| `/platform` | Organizational parent only; no broad privileges |
| `/platform/admins` | Existing reviewed OpenBao `platform` role, with platform and initially tenant-secret policies; effective only after explicitly approved membership |
| `/platform/developers` | No OpenBao secret privilege or other app role assigned |

Rancher, Harbor, Trivy-related interfaces and future apps require separate
explicit mappings. These groups do not imply Kubernetes cluster-admin,
Keycloak realm-admin or Fleet deployment authority. Do not introduce a blanket
realm role or map all descendants of `/platform` to admin. Existing tenant paths
such as `/tenants/home/admins` remain separate from platform groups.

## Explicit platform-admin test enrollment

The separately invoked `enroll-platform-admin.yaml` implements the user's exact
request for **new** `platform-admin-test-user` membership in `/platform/admins`.
It is not included by `configure.yaml`. Review and merge this code before the
approved live enrollment. It creates only a missing owned `/platform` parent,
its `/platform/admins` child and this one test user; `/platform/developers`
remains without a grant or membership change.

It first rejects username collisions unless a matching local created-user-ID
record proves an earlier successful enrollment. It never resets a password,
adopts an unrelated user, re-enables a disabled user or repairs profile changes
silently. It refuses default-group inheritance, unexpected realm/account default
roles or composite children, and any parent/admin-group role mapping. The only
accepted default roles are the observed built-in offline/UMA and account
self-service roles. No Keycloak administrative, Rancher, Kubernetes, Fleet or
other app role mapping is written. The intended OpenBao permission comes solely
from its already-reviewed exact `/platform/admins` claim binding and initially
includes platform plus tenant-secret paths.

After merge and the explicit account approval, use the same protected Ansible
configuration/environment as the main playbook, then invoke:

```sh
ansible-playbook -i localhost, big-bang-bootstrap/configuration/ansible/platform-config/enroll-platform-admin.yaml
```

`--check` performs static validation with no API/password actions. New credentials
are generated by the built-in Ansible password lookup directly into
`/path/to/platform-checkout/.secrets/platform-admin-test-user-password`,
mode 0600, beneath the existing owner-only ignored directory. The record at
`.secrets/openbao/recovery/platform-admin-test-user.record.json` stores only the
created UUID/username, never the password. Sensitive tasks use `no_log` and no
secret value belongs in arguments, chat, Git or logs. Repeat runs preserve the
password and make no membership or configuration writes. If creation succeeds
but recording ownership fails, stop for explicit recovery; do not generate a
replacement or reset an existing account.

The synthetic HTTPS tests prove first enrollment, stable repetition without
password reset, credential redaction, collision refusal and inherited-privilege
refusal. Actual OIDC and effective OpenBao access checks follow live enrollment;
no success is claimed merely from account creation.
