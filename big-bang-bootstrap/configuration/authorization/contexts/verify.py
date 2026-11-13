#!/usr/bin/env python3
"""Offline context verification only: never generates configuration or grants."""
import argparse
from pathlib import Path
import re
import sys
import yaml


class ContractError(ValueError):
    pass


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ContractError('mapping keys must be unique strings')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def require(condition, message):
    if not condition:
        raise ContractError(message)


def keys(value, expected, where):
    require(isinstance(value, dict) and set(value) == set(expected.split()),
            f'{where}: unknown or missing fields')


def names(value, where, nonempty=True):
    require(isinstance(value, list) and (value or not nonempty), f'{where}: expected list')
    require(all(isinstance(v, str) and re.fullmatch(r'[a-z][a-z0-9-]{0,62}', v) for v in value),
            f'{where}: invalid literal name')
    require(len(value) == len(set(value)), f'{where}: duplicate name')


def validate(document):
    keys(document, 'paas_context', 'document')
    c = document['paas_context']
    keys(c, 'schema_version id activation keycloak kubernetes applications targets', 'context')
    require(type(c['schema_version']) is int and c['schema_version'] == 1, 'unsupported schema')
    require(c['activation'] is False, 'contract does not authorize activation')
    require(isinstance(c['id'], str) and re.fullmatch(r'[a-z][a-z0-9-]{0,30}', c['id']), 'invalid context id')
    require(c['id'] not in {'system', 'platform', 'default', 'kube-system'}, 'reserved context id')
    tenant = c['id']
    k = c['keycloak']
    keys(k, 'realm groups', 'keycloak')
    require(k['realm'] == 'perkforge', 'unexpected realm')
    require(k['groups'] == {
        'tenant-admin': f'/tenants/{tenant}/admins',
        'tenant-developer': f'/tenants/{tenant}/developers',
        'tenant-viewer': f'/tenants/{tenant}/viewers',
    }, 'groups must be exact tenant-qualified role paths')
    n = c['kubernetes']
    keys(n, 'runtime_namespaces control_namespaces', 'kubernetes')
    for field in n:
        names(n[field], field)
        require(all(v == f'tenant-{tenant}' or v.startswith(f'tenant-{tenant}-') for v in n[field]),
                'namespace outside named context')
    require(not set(n['runtime_namespaces']) & set(n['control_namespaces']), 'runtime/control namespaces overlap')
    require(all(not v.endswith(('-config', '-release')) for v in n['runtime_namespaces']),
            'control namespace cannot be exposed as application runtime')
    names(c['applications'], 'applications')
    t = c['targets']
    keys(t, 'grafana ntfy mattermost gitlab', 'targets')
    keys(t['grafana'], 'access role_mappings', 'grafana')
    require(t['grafana']['role_mappings'] == {'tenant-admin': 'Admin', 'tenant-developer': 'Editor', 'tenant-viewer': 'Viewer'},
            'unexpected Grafana org roles')
    require(t['grafana']['access'] == 'blocked_until_query_isolation', 'shared Grafana access is not authorized')
    keys(t['ntfy'], 'topic', 'ntfy')
    require(t['ntfy']['topic'] == f'tenant-{tenant}-alerts', 'ntfy topic must be exact and context qualified')
    keys(t['mattermost'], 'team_name channel_name channel_type', 'mattermost')
    require(t['mattermost'] == {'team_name': None, 'channel_name': 'alerts', 'channel_type': 'P'},
            'Mattermost requires the dedicated private alert channel')
    keys(t['gitlab'], 'group_id project_ids role_mappings', 'gitlab')
    require(t['gitlab']['role_mappings'] == {'tenant-admin': 'Owner', 'tenant-developer': 'Developer', 'tenant-viewer': 'Reporter'},
            'unexpected GitLab tenant roles')
    require(t['gitlab']['group_id'] is None and t['gitlab']['project_ids'] == [],
            'GitLab IDs await reviewed native resolution; contract grants no membership')
    return c


def load(path):
    return validate(yaml.load(Path(path).read_text(), Loader=UniqueLoader))


def validate_all(paths):
    contexts = [load(path) for path in paths]
    for field, values in {
        'id': [c['id'] for c in contexts],
        'namespace': [n for c in contexts for names_ in c['kubernetes'].values() for n in names_],
        'ntfy topic': [c['targets']['ntfy']['topic'] for c in contexts],
    }.items():
        require(len(values) == len(set(values)), f'duplicate cross-context {field}')
    return contexts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()
    try:
        contexts = validate_all(args.paths)
    except (ContractError, yaml.YAMLError, OSError) as error:
        print(f'Invalid context: {error}', file=sys.stderr)
        return 1
    print(f'Validated {len(contexts)} inactive context contract(s); no APIs or grants.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
