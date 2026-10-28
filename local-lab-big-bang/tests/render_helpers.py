"""Offline render helpers for tests; output is never deployment source."""
from pathlib import Path
import os
import subprocess
import tempfile

import yaml


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
        return [obj for obj in yaml.safe_load_all(result.stdout) if obj]


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
