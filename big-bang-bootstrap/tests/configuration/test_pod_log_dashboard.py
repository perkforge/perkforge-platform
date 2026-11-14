"""Offline dashboard rendering; this is not log authorization or live acceptance."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'configuration/observability/pod-log-dashboard'


def render(folder, **changes):
    values = dict(pod_logs_render=True, pod_logs_org_id=2,
                  pod_logs_datasource_uid='fixture-scoped-logs',
                  pod_logs_coverage='Synthetic approved namespace only',
                  pod_logs_output=str(folder / 'output'))
    values.update(changes)
    variables = folder / 'inputs.yaml'
    variables.write_text(yaml.safe_dump(values))
    return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(SOURCE / 'render.yaml'),
                           '-e', '@' + str(variables)], capture_output=True, text=True,
                          env={**os.environ, 'ANSIBLE_LOCAL_TEMP': str(folder / 'ansible')}, timeout=40)


class PodLogDashboard(unittest.TestCase):
    def test_default_off_and_no_external_actions(self):
        play = yaml.safe_load((SOURCE / 'render.yaml').read_text())[0]
        self.assertFalse(play['vars']['pod_logs_render'])
        modules = {k for task in play['tasks'][0]['block'] for k in task if k.startswith('ansible.')}
        self.assertEqual(modules, {'ansible.builtin.assert', 'ansible.builtin.file', 'ansible.builtin.template'})
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); result = render(p, pod_logs_render=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((p / 'output').exists())

    def test_explicit_scoped_datasource_native_panels_and_chained_variables(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); result = render(p)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            dashboard = json.loads((p / 'output/dashboard.json').read_text())
            provider = yaml.safe_load((p / 'output/provider.yaml').read_text())['providers'][0]
            self.assertEqual(provider['orgId'], 2)
            self.assertTrue(provider['options']['path'].endswith('/org-2'))
            self.assertFalse(provider['allowUiUpdates']); self.assertFalse(dashboard['editable'])
            self.assertEqual(dashboard['time'], {'from': 'now-15m', 'to': 'now'})
            self.assertEqual(dashboard['refresh'], '30s')
            variables = dashboard['templating']['list']
            self.assertEqual([v['name'] for v in variables], ['namespace', 'pod', 'container'])
            for v in variables:
                self.assertEqual(v['type'], 'query'); self.assertEqual(v['query']['type'], 1)
                self.assertEqual(v['query']['label'], v['name']); self.assertEqual(v['allValue'], '.+')
                self.assertEqual(v['datasource'], {'type': 'loki', 'uid': 'fixture-scoped-logs'})
            self.assertIn('${namespace:regex}', variables[1]['query']['stream'])
            self.assertIn('${pod:regex}', variables[2]['query']['stream'])
            self.assertEqual([v['type'] for v in dashboard['panels']], ['text', 'timeseries', 'stat', 'logs'])
            self.assertIn('not authorization', dashboard['panels'][0]['options']['content'])
            for panel in dashboard['panels'][1:]:
                self.assertEqual(panel['datasource']['uid'], 'fixture-scoped-logs')
                for target in panel['targets']:
                    self.assertEqual(target['datasource'], panel['datasource'])
                    for name in ['namespace', 'pod', 'container']:
                        self.assertIn('${' + name + ':regex}', target['expr'])
            logs = dashboard['panels'][-1]
            self.assertEqual(logs['targets'][0]['maxLines'], 1000)
            self.assertEqual(logs['options']['dedupStrategy'], 'none')
            self.assertNotIn('loki-pilot', json.dumps(dashboard))
            self.assertNotIn('http', json.dumps(dashboard))
            self.assertEqual(dashboard['links'], [])

    def test_invalid_or_missing_inputs_never_choose_a_shared_fallback(self):
        for changes in [dict(pod_logs_datasource_uid=None), dict(pod_logs_datasource_uid=''),
                        dict(pod_logs_datasource_uid='${shared}'), dict(pod_logs_org_id=0),
                        dict(pod_logs_org_id=True), dict(pod_logs_coverage='')]:
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp); result = render(p, **changes)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((p / 'output/dashboard.json').exists())

    def test_org_binding_changes_only_native_provider_and_explicit_datasource(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); result=render(p, pod_logs_org_id=7, pod_logs_datasource_uid='other-reviewed-uid')
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            d=json.loads((p/'output/dashboard.json').read_text())
            self.assertEqual(d['panels'][-1]['datasource']['uid'], 'other-reviewed-uid')
            provider=yaml.safe_load((p/'output/provider.yaml').read_text())['providers'][0]
            self.assertEqual(provider['orgId'],7)
            self.assertTrue(provider['options']['path'].endswith('/org-7'))


if __name__ == '__main__': unittest.main()
