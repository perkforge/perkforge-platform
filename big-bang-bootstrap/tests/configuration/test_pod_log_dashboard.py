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
            values = yaml.safe_load((p / 'output/helm-values.yaml').read_text())['upstream']
            self.assertEqual(set(values), {'dashboardProviders', 'dashboards'})
            helm_provider = values['dashboardProviders']['perkforge-pod-logs-org-2.yaml']['providers'][0]
            self.assertEqual(helm_provider['orgId'], 2)
            self.assertTrue(helm_provider['options']['path'].endswith('/pf-pod-logs-org-2'))
            self.assertEqual(json.loads(values['dashboards']['pf-pod-logs-org-2']['pod-logs']['json']), dashboard)

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

    def test_optional_pinned_native_chart_mount_and_preservation(self):
        chart = os.environ.get('GRAFANA_CHART_DIR')
        if not chart:
            self.skipTest('Set existing Grafana BB chart path for native Helm render; no download')
        metadata = yaml.safe_load((Path(chart) / 'Chart.yaml').read_text())
        self.assertEqual(metadata['version'], '13.2.4-bb.0')
        self.assertEqual(metadata['appVersion'], '13.2.1')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); result = render(p, pod_logs_org_id=1, pod_logs_datasource_uid='loki-platform')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            command = [os.environ.get('HELM_BIN', 'helm'), 'template', 'grafana', chart, '--namespace', 'monitoring']
            baseline = subprocess.run(command, capture_output=True, text=True, check=True)
            candidate = subprocess.run(command + ['-f', str(p / 'output/helm-values.yaml')], capture_output=True, text=True, check=True)
            def objects(text):
                return {(v['kind'], v['metadata']['name']): v for v in yaml.safe_load_all(text) if v}
            before, after = objects(baseline.stdout), objects(candidate.stdout)
            for key, obj in before.items():
                if key[0] not in ['Deployment', 'ConfigMap']:
                    self.assertEqual(after[key], obj)
                if key[0] == 'ConfigMap':
                    for name, data in obj.get('data', {}).items():
                        self.assertEqual(after[key]['data'][name], data)
            added = [v for k, v in after.items() if k not in before and k[0] == 'ConfigMap']
            dashboard = next(v for v in added if 'pod-logs.json' in v.get('data', {}))
            self.assertEqual(json.loads(dashboard['data']['pod-logs.json'])['panels'][-1]['datasource']['uid'], 'loki-platform')
            deployment = next(v for v in after.values() if v['kind'] == 'Deployment')
            pod = deployment['spec']['template']['spec']
            self.assertTrue(any(v.get('configMap', {}).get('name') == dashboard['metadata']['name'] for v in pod['volumes']))
            old_pod = next(v for v in before.values() if v['kind'] == 'Deployment')['spec']['template']['spec']
            for volume in old_pod['volumes']:
                self.assertIn(volume, pod['volumes'])
            for old_container in old_pod['containers']:
                current = next(c for c in pod['containers'] if c['name'] == old_container['name'])
                for key, value in old_container.items():
                    if key == 'volumeMounts':
                        for mount in value:
                            self.assertIn(mount, current[key])
                    else:
                        self.assertEqual(current[key], value)
            grafana = next(c for c in pod['containers'] if c['name'] == 'grafana')
            self.assertTrue(any(v['mountPath'].endswith('/pf-pod-logs-org-1/pod-logs.json') for v in grafana['volumeMounts']))

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
