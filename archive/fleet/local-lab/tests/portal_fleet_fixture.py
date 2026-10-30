"""TEST ONLY: actual Fleet loader/matcher/renderer; no deployment imports this file."""
import copy
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import yaml
ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / 'local-lab/tenant-config'


def home_values():
    return yaml.safe_load((BUNDLE / 'tenants/home.yaml').read_text())


def merged_values(home=None):
    # Expected data for assertions. Rendering and actual values merging are Fleet's.
    def merge(base, override):
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                merge(base[key], value)
            else:
                base[key] = copy.deepcopy(value)
        return base
    return merge(yaml.safe_load((BUNDLE / 'values.yaml').read_text()), home or home_values())


def portal_values(home=None):
    values = merged_values(home)
    app = copy.deepcopy(values['applications']['portal'])
    repo = values['foundation']['repositories'][app['repository']]
    # Request fixture fields, never inputs to configuration generation.
    app['deployerServiceAccount'] = repo['deployerServiceAccount']
    app['fleetAgentNamespace'] = values['foundation']['fleetAgentNamespace']
    return app


def provisioned(state='paused'):
    home = home_values()
    home['foundation']['lifecycle']['state'] = state
    home['foundation']['namespaces']['tenant-home-portal']['allocation'] = copy.deepcopy(home['environments'][0]['allocation'])
    home['applications']['portal']['imageDigest'] = 'sha256:' + 'a' * 64
    home['resources']['budget'] = {'pods': '12', 'requests.cpu': '1200m', 'requests.memory': '2Gi',
        'limits.cpu': '4', 'limits.memory': '4Gi', 'persistentvolumeclaims': '6',
        'requests.storage': '12Gi', 'services': '10'}
    return home


def run_fleet(home=None, shared=None, cluster='local', extra_files=None):
    with tempfile.TemporaryDirectory(prefix='foundation-fleet-test-') as directory:
        bundle = Path(directory) / 'bundle'
        shutil.copytree(BUNDLE, bundle)
        if home is not None:
            (bundle / 'tenants/home.yaml').write_text(yaml.safe_dump(home))
        if shared is not None:
            (bundle / 'values.yaml').write_text(yaml.safe_dump(shared))
        for name, text in (extra_files or {}).items():
            path = bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        return subprocess.run([os.environ.get('FLEET', 'fleet'), 'test', '-f', 'enrollments/home.yaml', '-N', cluster, str(bundle)],
            capture_output=True, text=True, timeout=30, env={**os.environ, 'KUBECONFIG': '/dev/null'})


def render(home=None):
    result = run_fleet(home)
    if result.returncode:
        raise AssertionError(result.stderr)
    return [obj for obj in yaml.safe_load_all(result.stdout) if obj]
