"""Pinned selected OpenBao render and installer authorization; no API access."""
import os
import copy
from pathlib import Path
import unittest
import yaml
from fixtures.render_helpers import build, helm, ordered_values, child_values, release_name

ROOT = Path(__file__).resolve().parents[2]

class OpenBaoInstaller(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chart = Path(os.environ['PREFLIGHT_SOURCES_DIR']) / 'openbao'
        root = build(ROOT / 'clusters/local')
        parent = next(x for x in root if x['kind'] == 'HelmRelease')
        outer = helm(cls.chart.parent / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(root, parent))
        cls.child = next(x for x in outer if x['kind'] == 'HelmRelease' and x['metadata']['name'] == 'openbao')
        cls.objects = helm(cls.chart, release_name(cls.child), 'openbao', child_values(outer, 'openbao'))
        cls.foundation = build(ROOT / 'configuration/packages/openbao/prerequisites')

    def test_delegated_installer_covers_every_selected_object_without_cluster_grants(self):
        self.assertEqual(self.child['spec']['serviceAccountName'], 'openbao-installer')
        self.assertFalse(self.child['spec']['suspend'])
        self.assertFalse(self.child['spec']['test']['enable'])
        self.assertFalse(any(x['kind'] in ('ClusterRole','ClusterRoleBinding','Role','RoleBinding','Secret','Ingress') for x in self.objects))
        rules = next(x for x in self.foundation if x['kind'] == 'Role')['rules']
        plural = {'ServiceAccount':'serviceaccounts','Service':'services','ConfigMap':'configmaps','StatefulSet':'statefulsets','Pod':'pods','IngressRouteTCP':'ingressroutetcps'}
        for obj in self.objects:
            group = obj['apiVersion'].split('/')[0] if '/' in obj['apiVersion'] else ''
            for verb in ('get','list','watch','create','update','patch','delete'):
                self.assertTrue(any(group in r['apiGroups'] and plural[obj['kind']] in r['resources'] and verb in r['verbs'] for r in rules), (obj['kind'],verb))
        self.assertFalse(any(x['kind'].startswith('Cluster') for x in self.foundation))
        self.assertFalse(any('lookup ' in p.read_text() for p in (self.chart/'templates').rglob('*') if p.is_file()))

    def test_tls_persistence_sealed_health_and_restricted_worker_placement(self):
        state = next(x for x in self.objects if x['kind']=='StatefulSet')
        self.assertEqual(state['spec']['replicas'],1)
        self.assertEqual(state['spec']['updateStrategy']['type'],'OnDelete')
        pod = state['spec']['template']['spec']; c = pod['containers'][0]
        self.assertEqual(pod['nodeSelector'], {'storage.perkforge.io/worker':'true'})
        self.assertTrue(pod['securityContext']['runAsNonRoot'])
        self.assertEqual(c['securityContext']['capabilities']['drop'], ['ALL'])
        self.assertFalse(c['securityContext']['allowPrivilegeEscalation'])
        self.assertEqual(c['readinessProbe']['httpGet']['scheme'],'HTTPS')
        path = c['readinessProbe']['httpGet']['path']
        self.assertNotIn('sealedcode',path); self.assertNotIn('uninitcode',path)
        self.assertNotIn('tls-skip-verify',yaml.safe_dump(c))
        tls = next(v for v in pod['volumes'] if v['name']=='server-tls')
        self.assertEqual(tls['secret']['secretName'],'openbao-server-tls')
        self.assertTrue(next(v for v in c['volumeMounts'] if v['name']=='server-tls')['readOnly'])
        claim=state['spec']['volumeClaimTemplates'][0]['spec']
        self.assertEqual(claim['storageClassName'],'longhorn')
        self.assertEqual(claim['resources']['requests']['storage'],'10Gi')
        config=next(x for x in self.objects if x['kind']=='ConfigMap')['data']
        text='\n'.join(config.values())
        self.assertIn('tls_cert_file',text); self.assertNotIn('tls_disable = 1',text)
        self.assertNotIn('service_registration',text)

    def test_no_deployment_competitor_or_automatic_initialization(self):
        values=yaml.safe_load((ROOT/'configuration/packages/openbao/values.yaml').read_text())['packages']['openbao']['values']
        self.assertFalse(values['server']['dev']['enabled'])
        self.assertFalse(values['server']['authDelegator']['enabled'])
        self.assertFalse(values['injector']['enabled']); self.assertFalse(values['csi']['enabled'])
        self.assertNotIn('postStart',values['server'])
        self.assertEqual(str(values['server']['resources']['requests']['memory']),'256Mi')
        play=yaml.safe_load((ROOT/'configuration/ansible/openbao-prerequisites.yaml').read_text())[0]
        self.assertFalse(play['vars']['openbao_foundation_apply'])
        self.assertTrue((ROOT/'configuration/packages/openbao/operations/README.md').is_file())

    def test_exact_sni_passthrough_preserves_existing_server_and_http_routes(self):
        routes = [x for x in self.objects if x['kind'] == 'IngressRouteTCP']
        self.assertEqual(len(routes), 1)
        route = routes[0]
        self.assertEqual(route['metadata']['namespace'], 'openbao')
        self.assertEqual(route['metadata']['annotations'], {'kubernetes.io/ingress.class': 'traefik'})
        self.assertEqual(route['spec'], {
            'entryPoints': ['websecure'],
            'routes': [{'match': 'HostSNI(`openbao.perkforge.home.arpa`)',
                        'services': [{'name': 'openbao', 'port': 8200}]}],
            'tls': {'passthrough': True},
        })
        # Actual chart comparison, not a second hand-written server fixture.
        root = build(ROOT / 'clusters/local')
        parent = next(x for x in root if x['kind'] == 'HelmRelease')
        outer = helm(self.chart.parent / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(root, parent))
        previous_root = copy.deepcopy(root)
        cm = next(x for x in previous_root if x['kind'] == 'ConfigMap' and x['metadata']['name'] == 'values-openbao')
        previous_values = yaml.safe_load(cm['data']['values.yaml'])
        previous_values['packages']['openbao']['values'].pop('extraObjects')
        cm['data']['values.yaml'] = yaml.safe_dump(previous_values)
        previous_outer = helm(self.chart.parent / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(previous_root, parent))
        def other_package(obj):
            # OpenBao's own generated-values checksum must change with its new route.
            return not ((obj['kind'] == 'Secret' and obj['metadata']['name'] in ('bigbang-openbao-values', 'openbao-values'))
                        or (obj['kind'] == 'HelmRelease' and obj['metadata']['name'] == 'openbao'))
        # Includes actual Rancher release/values (its HTTP ingress) and Longhorn values.
        self.assertEqual(list(filter(other_package, outer)), list(filter(other_package, previous_outer)))
        before = [yaml.safe_load(value) for value in child_values(outer, 'openbao')]
        for values in before:
            values.pop('extraObjects', None)
        baseline = helm(self.chart, release_name(self.child), 'openbao', [yaml.safe_dump(value) for value in before])
        self.assertEqual([x for x in self.objects if x['kind'] != 'IngressRouteTCP'], baseline)
        # Only a namespaced CRD-object rule is added; no CRD installation or cluster grant.
        rules = next(x for x in self.foundation if x['kind'] == 'Role')['rules']
        new = [r for r in rules if 'traefik.io' in r['apiGroups']]
        self.assertEqual(new, [{'apiGroups': ['traefik.io'], 'resources': ['ingressroutetcps'],
                               'verbs': ['get','list','watch','create','update','patch','delete']}])
        for forbidden in ['secrets', '*', 'ingressroutes', 'middlewaretcps', 'serverstransporttcps']:
            self.assertFalse(any(forbidden in r['resources'] for r in rules))
