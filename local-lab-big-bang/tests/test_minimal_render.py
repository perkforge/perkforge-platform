"""Render the complete four-app TEST selection; never apply or provision secrets."""
import json
import os
from pathlib import Path
import unittest

import yaml

from render_helpers import build, child_values, helm, ordered_values, release_name
from resource_inventory import inventory

ROOT = Path(__file__).resolve().parents[1]


class MinimalRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        cls.app = Path(os.environ['TENANT_APP_CHECKOUT'])
        cls.objects, cls.reports = {}, {}
        cls.flux = build(cls.sources / 'bigbang/base/flux')
        for target in ('local', 'dev'):
            root = build(ROOT / 'examples/clusters' / target)
            release = next(obj for obj in root if obj['kind'] == 'HelmRelease')
            assert release['spec']['suspend']
            values = ordered_values(root, release)
            cls.objects[target] = {'root': root}
            cls.objects[target]['default'] = helm(cls.sources / 'bigbang/chart', 'bigbang', 'bigbang', values)
            outer = helm(cls.sources / 'bigbang/chart', 'bigbang', 'bigbang',
                         values + [(ROOT / 'preflight/values.yaml').read_text()])
            cls.objects[target]['outer'] = outer
            cls.reports[target] = {'flux': inventory(cls.flux)}
            for name in ('headlamp', 'keycloak', 'openbao'):
                child = next(obj for obj in outer if obj['kind'] == 'HelmRelease' and obj['metadata']['name'] == name)
                chart = cls.sources / name / ('.' if name == 'openbao' else 'chart')
                objects = helm(chart, release_name(child), child['spec']['targetNamespace'], child_values(outer, name))
                cls.objects[target][name] = objects
                cls.reports[target][name] = inventory(objects)
            app = build(cls.app / 'gitops/clusters' / target)
            app_release = next(obj for obj in app if obj['kind'] == 'HelmRelease')
            # The existing approved image digest comes from the pinned app release;
            # app environment/profile/cluster values override its legacy endpoint inputs.
            app_values = [(cls.app / 'bundles/portal/values.yaml').read_text()] + ordered_values(app, app_release)
            objects = helm(cls.app / 'bundles/portal/chart', 'portal', 'tenant-example-portal', app_values,
                           ('--set', 'enabled=true'))
            cls.objects[target]['portal'] = objects
            cls.reports[target]['portal'] = inventory(objects)
        output = os.environ.get('CAPACITY_REPORT_DIR')
        if output:
            Path(output).mkdir(parents=True, exist_ok=True)
            for target, report in cls.reports.items():
                (Path(output) / (target + '.json')).write_text(json.dumps(report, indent=2) + '\n')

    def test_default_stays_paused_and_preflight_is_exact_allowlist(self):
        for target, objects in self.objects.items():
            default = {obj['metadata']['name'] for obj in objects['default'] if obj['kind'] == 'HelmRelease'}
            self.assertEqual(default, {'headlamp', 'openbao'})
            selected = {obj['metadata']['name'] for obj in objects['outer'] if obj['kind'] == 'HelmRelease'}
            self.assertEqual(selected, {'headlamp', 'keycloak', 'openbao'})
            for obj in objects['root']:
                if obj['kind'] in ('GitRepository', 'Kustomization', 'HelmRelease'):
                    self.assertTrue(obj['spec']['suspend'])
            self.assertEqual(len(self.reports[target]['portal']['workloads']), 1)

    def test_real_keycloak_database_pin_connection_and_external_credentials(self):
        chart = yaml.safe_load((self.sources / 'keycloak/chart/Chart.yaml').read_text())
        self.assertEqual(chart['version'], '7.3.2-bb.1')
        self.assertIn(('postgresql', '18.12.4'), [(d['name'], str(d['version'])) for d in chart['dependencies']])
        for objects in self.objects.values():
            child = objects['keycloak']
            self.assertFalse(any(obj['kind'] == 'Secret' for obj in child))
            pods = [obj for obj in child if obj['kind'] == 'StatefulSet']
            self.assertEqual(len(pods), 2)
            keycloak = next(obj for obj in pods if obj['metadata']['name'] == 'keycloak-keycloak')
            container = keycloak['spec']['template']['spec']['containers'][0]
            env = {value['name']: value for value in container['env']}
            services = {obj['metadata']['name'] for obj in child if obj['kind'] == 'Service'}
            self.assertIn(env['KC_DB_URL_HOST']['value'], services)
            self.assertEqual(env['KC_DB_PASSWORD']['valueFrom']['secretKeyRef']['name'], 'keycloak-database-existing')
            self.assertEqual(container['envFrom'], [{'secretRef': {'name': 'keycloak-bootstrap-existing'}}])
            database = next(obj for obj in pods if obj['metadata']['name'] == 'keycloak-postgresql')
            probe = database['spec']['template']['spec']['containers'][0]['readinessProbe']['exec']['command']
            self.assertIn('pg_isready', probe[-1])
            self.assertNotIn('bitnami', probe[-1])
            images = self.reports['local']['keycloak']['images']
            self.assertTrue(any(image.endswith(':18.6') for image in images))
            self.assertTrue(any(image.endswith(':26.8.0') for image in images))

    def test_ui_and_inventory_do_not_hide_extra_privilege_or_unsized_hooks(self):
        for target, objects in self.objects.items():
            self.assertFalse(any(obj['kind'] == 'ClusterRoleBinding' for obj in objects['headlamp']))
            for name in ('headlamp', 'keycloak', 'openbao', 'portal'):
                self.assertFalse(any(obj['kind'] == 'Secret' for obj in objects[name]))
                steady = [w for w in self.reports[target][name]['workloads'] if not w['hook']]
                self.assertTrue(all(not w['unsized'] for w in steady))
            hook = next(w for w in self.reports[target]['openbao']['workloads'] if w['hook'] == 'test')
            self.assertTrue(hook['unsized'])
            release = next(obj for obj in objects['outer'] if obj['kind'] == 'HelmRelease' and obj['metadata']['name'] == 'openbao')
            self.assertFalse(release['spec']['test']['enable'])
            binding = next(obj for obj in objects['openbao'] if obj['kind'] == 'ClusterRoleBinding')
            self.assertEqual(binding['roleRef']['name'], 'system:auth-delegator')

    def test_full_flux_and_storage_cost_are_accounted(self):
        report = self.reports['local']
        self.assertEqual(len(report['flux']['workloads']), 4)
        self.assertEqual(report['flux']['steadyRequestsMi'], 2208)
        self.assertAlmostEqual(report['flux']['steadyRequestsCPU'], 1.6)
        self.assertEqual(sum(c['bytes'] for name in report for c in report[name]['claims']), 14 * 1024**3)
        print('Local complete render: requests %.3f CPU / %.0f MiB; limits %.0f MiB; 14 GiB PVC' % (
            sum(x['steadyRequestsCPU'] for x in report.values()),
            sum(x['steadyRequestsMi'] for x in report.values()),
            sum(x['steadyLimitsMi'] for x in report.values())))
