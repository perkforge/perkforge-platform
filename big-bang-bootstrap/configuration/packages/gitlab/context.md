# GitLab project context prerequisite

Portal is the first integrated PaaS pilot (#334); this does not migrate its
GitHub repositories or independently activate Portal. Its source, tenant config,
and enrollment repositories are not evidence of existing GitLab group/project IDs.

`inspect-context.yaml` is a read-only prerequisite. Copy
`context-inputs.example.yaml` to an owner-private operator file and supply the
reviewed native group/project IDs and exact full paths, trusted origin/public CA,
and an existing owner-only `read_api` token file. Set `gitlab_context_run: true`
and `gitlab_context_scope: gitlab-context-inspect-v1` only for the selected
inspection. No token generation or credential retrieval is part of this playbook.

```sh
ansible-playbook -i localhost, \
  big-bang-bootstrap/configuration/packages/gitlab/inspect-context.yaml \
  -e @/absolute/private/operator-inputs.yaml
```

Default and check mode make no API contact. An explicit invocation performs only
GETs for the pinned version, exact group (without listing projects) and exact
project. It refuses non-private resources, archived projects, user-owned projects,
ID/path drift or a project outside the exact selected group. No project search,
member enumeration, description, webhook secret or raw API response is emitted.
TLS verification is required, redirects/proxies/netrc are disabled, and the bearer
header is not forwarded. Repetition is read-only. There is no rollback mutation.

The operator must bind these reviewed IDs to the Portal context owned by #16/#43;
matching names alone do not authorize a binding. This inspector does not prove
membership, effective inherited permissions, identity claim mapping or offboarding.
Subgroups are not implicitly admitted: supply the exact owning namespace as the
selected group. Existing `reconcile-membership.yaml` remains a separately gated
native membership operation; it does not automatically map Keycloak group claims.

## Next integration boundary

Keycloak roles assigned to groups are the shared identity input. Corey approved
tenant-admin → GitLab Owner, tenant-developer → Developer, and tenant-viewer →
Reporter for their tenant group/projects. Group Owner is not instance-admin.
These are the intended native grants, not grants performed by this inspector.
Platform-engineer visibility is cross-tenant; OpenBao is outside this workstream.
The initial event set and actual native identities remain activation inputs.
Use the shared context mapping for independently enforced destinations. Tenant
viewers receive alert delivery through Mattermost only, not direct ntfy:

- an exact ntfy topic with topic-scoped publisher/subscriber ACLs;
- an exact Mattermost private channel ID with a channel-locked webhook.

Webhook URLs/tokens are protected runtime inputs. GitLab payloads must not select
channels/topics, supply credentials, or override the reviewed source project.
GitLab CI/deployment events are distinct from Grafana metric alerts: select one
producer for each event class and verify deduplication/recovery semantics before
activation. Do not send raw commit messages, variables, job traces, arbitrary
labels or security finding details by default. Links require GitLab authorization.

Remaining #334 work: inventory actual approved IDs; agree native memberships and
event scope; configure supported pinned-version destinations; prove intended
receipt, cross-context denial, failed credentials and effective membership removal.
No live membership, integration, pipeline or test message was performed by this
source change. Fixture evidence is not real project or notification acceptance.

API references: [project](https://docs.gitlab.com/api/projects/#get-a-single-project),
[group](https://docs.gitlab.com/api/groups/#details-of-a-group).

## Offline check

```sh
KUBECONFIG=/dev/null python3 -m unittest discover \
  -s big-bang-bootstrap/tests/security -p test_gitlab_context.py -v
```

The test executes the real Ansible playbook against an isolated TLS fixture,
including no-contact/check behavior, repeat, malformed inputs, wrong IDs/paths,
non-private/wrong-owner contexts, pinned-version mismatch, rejected credentials,
redirect/server failures and redaction. It never contacts the installed GitLab.

See [scoped GitLab events](events/README.md) for the inactive Portal event policy and native webhook input template.
