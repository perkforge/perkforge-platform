"""Offline render helpers for tests; output is never deployment source."""
from pathlib import Path
import os
import subprocess
import tempfile

import yaml


class RenderLoader(yaml.SafeLoader):
    """Kubernetes CRD enum '=' is a string, not YAML 1.1's special value tag."""


RenderLoader.add_constructor('tag:yaml.org,2002:value', lambda loader, node: loader.construct_scalar(node))


def build(path):
    return [obj for obj in yaml.safe_load_all(subprocess.check_output(
        ['kubectl', 'kustomize', str(path)], text=True,
        env={**os.environ, 'KUBECONFIG': '/dev/null'})) if obj]


def helm(chart, release, namespace, values, overrides=()):
    with tempfile.TemporaryDirectory() as directory:
        args = ['helm', 'template', release, str(chart), '--namespace', namespace,
                '--kube-version', '1.36.5']
        for index, value in enumerate(values):
            path = Path(directory) / f'{index}.yaml'
            path.write_text(value)
            args += ['-f', str(path)]
        result = subprocess.run(args + list(overrides), text=True, capture_output=True,
                                env={**os.environ, 'KUBECONFIG': '/dev/null'})
        if result.returncode:
            details = '\n'.join(line for line in result.stderr.splitlines()
                                if not (line.startswith('coalesce.go:') and 'secrets' in line))
            raise RuntimeError('Pinned Helm render failed: ' + details)
        # Helm warns when null removes this package's default credential table.
        # Tests inspect rendered objects for credential leakage; never log that table.
        return [obj for obj in yaml.load_all(result.stdout, Loader=RenderLoader) if obj]


def ordered_values(objects, release):
    maps = {obj['metadata']['name']: obj for obj in objects if obj['kind'] == 'ConfigMap'}
    values = []
    for ref in release['spec']['valuesFrom']:
        if ref['name'] not in maps and ref.get('optional'):
            continue
        values.append(maps[ref['name']]['data'][ref['valuesKey']])
    return values


def child_values(objects, name):
    secret = next(obj for obj in objects if obj['kind'] == 'Secret'
                  and obj['metadata']['name'] in (f'bigbang-{name}-values', f'{name}-values'))
    keys = ('values.yaml',) if name == 'openbao' else ('common', 'defaults', 'overlays')
    return [secret['stringData'][key] for key in keys]


def release_name(release):
    spec = release['spec']
    # Flux's default is [targetNamespace-]name, not Helm's arbitrary CLI name.
    return spec.get('releaseName') or ((spec['targetNamespace'] + '-')
                                      if spec.get('targetNamespace') else '') + release['metadata']['name']


def application_package_fixture(root):
    """Explicit identity-package opt-in for offline tests, never operator input."""
    objects = [obj for obj in build(root / 'clusters/local')
               if obj['metadata']['name'] not in {'values-longhorn', 'values-rancher', 'rancher-official', 'values-openbao', 'openbao-official', 'values-headlamp', 'values-keycloak'}]
    parent = next(o for o in objects if o['kind'] == 'HelmRelease')
    parent['spec']['valuesFrom'].insert(2, {'kind':'ConfigMap','name':'values-headlamp','valuesKey':'oidc.yaml','optional':True})
    for name in ['headlamp', 'keycloak']:
        selected = build(root / 'configuration/packages' / name)
        if name == 'headlamp':
            # Preserve the prior proven OIDC fixture independently of initial token mode.
            import yaml
            config = next(o for o in selected if o['kind'] == 'ConfigMap')
            config['data']['oidc.yaml'] = (root / 'configuration/packages/headlamp/oidc.yaml').read_text()
            value = yaml.safe_load(config['data']['values.yaml'])
            value['addons']['headlamp']['values']['upstream']['nodeSelector'] = {'kubernetes.io/hostname':'REPLACE_WITH_WORKER_NODE'}
            config['data']['values.yaml'] = yaml.safe_dump(value)
        if name == 'keycloak':
            import yaml
            config = next(o for o in selected if o['kind'] == 'ConfigMap')
            value = yaml.safe_load(config['data']['values.yaml'])
            value['addons']['keycloak']['values']['upstream']['nodeSelector'] = {'kubernetes.io/hostname':'REPLACE_WITH_WORKER_NODE'}
            value['addons']['keycloak']['values']['postgresql']['primary']['nodeSelector'] = {'kubernetes.io/hostname':'REPLACE_WITH_WORKER_NODE'}
            config['data']['values.yaml'] = yaml.safe_dump(value)
        objects += selected
    return objects
