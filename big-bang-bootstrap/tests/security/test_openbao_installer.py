"""Pinned selected OpenBao render and installer authorization; no API access."""
import os
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
        plural = {'ServiceAccount':'serviceaccounts','Service':'services','ConfigMap':'configmaps','StatefulSet':'statefulsets','Pod':'pods'}
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
