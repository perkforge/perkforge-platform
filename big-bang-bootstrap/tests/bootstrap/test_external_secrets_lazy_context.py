"""Bounded real-public-bundle regression through Ansible's actual filter runtime."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / 'configuration/ansible/filter_plugins/external_secrets_foundation_guard.py'


@unittest.skipUnless(os.environ.get('ESO_CHART_SOURCE') and shutil.which('ansible-playbook'),
                     'exact public ESO chart and Ansible required')
class RealBundleLazyContext(unittest.TestCase):
    def test_real_registered_context_is_bounded_exact_and_unchanged(self):
        bundle = Path(os.environ['ESO_CHART_SOURCE']) / 'chart/crds/bundle.yaml'
        pin = yaml.safe_load((ROOT / 'configuration/external-secrets/source-pin.yaml').read_text())
        self.assertEqual(hashlib.sha256(bundle.read_bytes()).hexdigest(), pin['crd_bundle_sha256'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            filters = root / 'filter_plugins'
            filters.mkdir()
            shutil.copy(GUARD, filters / 'external_secrets_foundation_guard.py')
            # A public fixture only: reproduce registered command results, including
            # their large duplicated stdout/lines and desired-object loop input.
            (filters / 'performance_fixture.py').write_text('''import copy
import importlib.util
import json
from pathlib import Path
import time
spec = importlib.util.spec_from_file_location('guard', Path(__file__).with_name('external_secrets_foundation_guard.py'))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
def fixture_results(items, source_hash):
    results = []
    for item in items:
        desired = guard.plain_structure(item)
        desired['metadata'].setdefault('labels', {})['perkforge.io/owner'] = guard.OWNER
        desired['metadata'].setdefault('annotations', {})[guard.HASH_ANNOTATION] = source_hash
        actual = copy.deepcopy(desired)
        actual['metadata']['managedFields'] = [{'manager': guard.CRD_MANAGER, 'operation': 'Update'}]
        actual['status'] = {'storedVersions': [v['name'] for v in actual['spec']['versions'] if v.get('storage')]}
        actual['spec']['conversion'] = {'strategy': 'None'}
        actual['spec']['preserveUnknownFields'] = False
        raw = json.dumps(actual, indent=4)
        results.append({'item': desired, 'stdout': raw, 'stdout_lines': raw.splitlines(), 'rc': 0})
    return results

def check_results(results):
    start = time.monotonic()
    before = guard.plain_structure(results)
    checks = guard.comparison_checks(results)
    assert all(c['matches'] for c in checks), checks
    assert guard.plain_structure(results) == before, 'comparison mutated inputs'
    # Verify that a mutation within the full CRD schema still rejects.
    wrong = copy.deepcopy(before[0])
    actual = json.loads(wrong['stdout'])
    actual['spec']['versions'][0]['schema']['openAPIV3Schema']['description'] = 'unreviewed drift'
    wrong['stdout'] = json.dumps(actual)
    assert not guard.comparison_checks([wrong])[0]['matches']
    elapsed = time.monotonic() - start
    assert elapsed < 10, 'public bundle guard exceeded ten seconds: ' + str(elapsed)
    return {'count': len(checks), 'elapsed_seconds': round(elapsed, 3), 'unchanged': True, 'drift_rejected': True}

class FilterModule:
    def filters(self):
        return {'fixture_results': fixture_results, 'check_results': check_results}
''')
            play = [{'hosts': 'localhost', 'gather_facts': False,
                     'vars': {'bundle_path': str(bundle), 'source_hash': pin['crd_bundle_sha256']},
                     'tasks': [
                         {'ansible.builtin.set_fact': {'desired': "{{ lookup('file', bundle_path) | from_yaml_all | select | list }}"}},
                         {'ansible.builtin.set_fact': {'registered': '{{ desired | fixture_results(source_hash) }}'}, 'no_log': True},
                         {'ansible.builtin.debug': {'msg': '{{ registered | check_results }}'}},
                     ]}]
            play_path = root / 'play.yaml'
            play_path.write_text(yaml.safe_dump(play))
            env = dict(os.environ, KUBECONFIG='/dev/null', ANSIBLE_LOCAL_TEMP=str(root / 'ansible-tmp'))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local', str(play_path)],
                                    text=True, capture_output=True, env=env, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('"count": ' + str(pin['crd_count']), result.stdout)
            self.assertIn('"unchanged": true', result.stdout)
            self.assertIn('"drift_rejected": true', result.stdout)
            # Public bounded measurement, useful in test evidence without schemas.
            print(result.stdout[result.stdout.index('    "msg":'):result.stdout.index('PLAY RECAP')].strip())


if __name__ == '__main__':
    unittest.main()
