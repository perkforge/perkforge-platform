"""Approved local ntfy source, not proof of live exposure or authorization."""
import unittest
from pathlib import Path
import yaml
BASE=Path(__file__).resolve().parents[2]/'configuration/packages/ntfy/local'
class NtfyLocal(unittest.TestCase):
    def test_exact_local_scope(self):
        docs=list(yaml.safe_load_all((BASE/'resources.yaml').read_text()))
        self.assertEqual(len(docs),7)
        self.assertEqual(len({(d['kind'],d['metadata']['name']) for d in docs}),7)
        self.assertTrue(all(d['metadata']['namespace']=='ntfy' for d in docs))
        by_kind={d['kind']:d for d in docs}
        config=yaml.safe_load(by_kind['ConfigMap']['data']['server.yml'])
        self.assertEqual(config['base-url'],'https://ntfy.perkforge.home.arpa')
        self.assertEqual(config['cache-duration'],'24h')
        self.assertEqual(config['auth-default-access'],'deny-all')
        pvc=by_kind['StatefulSet']['spec']['volumeClaimTemplates'][0]['spec']
        self.assertEqual(pvc['storageClassName'],'longhorn')
        self.assertEqual(pvc['resources']['requests']['storage'],'1Gi')
        self.assertNotIn('Secret',by_kind)
        self.assertEqual(by_kind['NetworkPolicy']['spec']['egress'],[])
    def test_prerequisites_excluded_and_bounded(self):
        k=yaml.safe_load((BASE/'kustomization.yaml').read_text())
        self.assertEqual(k['resources'],['resources.yaml'])
        ns,role,binding=yaml.safe_load_all((BASE/'prerequisites.yaml').read_text())
        self.assertEqual(ns['metadata']['name'],'ntfy')
        self.assertEqual(role['kind'],'Role')
        self.assertEqual(role['metadata']['namespace'],'ntfy')
        for rule in role['rules']:
            self.assertFalse(set(rule['resources']) & {'secrets','roles','rolebindings','clusterroles','clusterrolebindings','*'})
            self.assertFalse(set(rule['verbs']) & {'delete','deletecollection','*','bind','escalate'})
        self.assertEqual(binding['subjects'],[{'kind':'ServiceAccount','name':'platform-reconciler','namespace':'flux-system'}])
