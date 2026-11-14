"""Source-only native composition; no cluster or credentials."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

MODULE = Path(__file__).resolve().parents[2] / 'configuration/packages/mattermost/runtime'

class RuntimeRender(unittest.TestCase):
    def run_play(self, inputs, check=False):
        return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(MODULE / 'render.yaml'), '-e', json.dumps(inputs)] + (['--check'] if check else []), capture_output=True, text=True, timeout=45)

    def test_default_and_check_inert(self):
        for check in (False, True):
            r = self.run_play({}, check)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_compose_and_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ca = root / 'ca.crt'; ca.write_text('synthetic-public-ca\n')
            inputs = dict(mattermost_runtime_render=True,
                mattermost_runtime_origin='https://chat.example.test',
                mattermost_runtime_issuer='https://sso.example.test/realms/perkforge',
                mattermost_runtime_ca_file=str(ca),
                mattermost_runtime_ca_sha256=hashlib.sha256(ca.read_bytes()).hexdigest(),
                mattermost_runtime_output_dir=str(root / 'out'),
                mattermost_runtime_storage_class='dedicated-rwo',
                mattermost_runtime_node_selector={'workload.example.test/stateful':'true'},
                mattermost_runtime_api_cidrs=['192.0.2.1/32'],
                mattermost_runtime_ingress_cidrs=['192.0.2.2/32'])
            r = self.run_play(inputs); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            addons = yaml.safe_load((root/'out/values.yaml').read_text())['addons']
            for package in addons.values():
                self.assertTrue(package['enabled']); self.assertFalse(package['flux']['suspend'])
            self.assertIn('ClusterRole', json.dumps(addons['mattermostOperator']['postRenderers']))
            app = addons['mattermost']; values = app['values']
            self.assertEqual(values['users'],100)
            self.assertEqual(values['securityContext']['fsGroup'],2000)
            self.assertEqual(values['containerSecurityContext']['capabilities'],{'drop':['ALL']})
            self.assertFalse(values['enterprise']['enabled'])
            self.assertEqual(values['postgresql']['primary']['persistence']['storageClass'],'dedicated-rwo')
            self.assertEqual(len(app['postRenderers']),2)
            self.assertIn('externalVolume',app['postRenderers'][0]['kustomize']['patches'][0]['patch'])
            wait = json.loads(app['postRenderers'][1]['kustomize']['patches'][0]['patch'])
            self.assertEqual(wait[0]['path'],'/spec/egress')
            size = json.loads(app['postRenderers'][1]['kustomize']['patches'][1]['patch'])
            self.assertEqual(size,[{'op':'remove','path':'/spec/size'}])
            self.assertNotIn('0.0.0.0/0',json.dumps(wait))
            env = {x['name']:x for x in values['existingSecretEnvs']}
            self.assertEqual(env['MM_OPENIDSETTINGS_SECRET']['valueFrom']['secretKeyRef']['name'],'mattermost-oidc-client')
            policies=list(yaml.safe_load_all((root/'out/network.yaml').read_text()))
            self.assertEqual(len(policies),5)
            db=next(x for x in policies if x['metadata']['name']=='mattermost-database')
            self.assertEqual(db['spec']['egress'],[])
            self.assertNotIn('0.0.0.0/0',json.dumps(policies))
            original_limits = values['resources']['limits'].copy()
            db_limits = values['postgresql']['primary']['resources']['limits'].copy()
            r = self.run_play({**inputs,
                'mattermost_runtime_operator_node_selector': {'role.example.test/operator':'true'},
                'mattermost_runtime_app_requests': {'cpu':'100m','memory':'1Gi'},
                'mattermost_runtime_database_requests': {'cpu':'50m','memory':'256Mi'}})
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            selected = yaml.safe_load((root/'out/values.yaml').read_text())['addons']
            self.assertEqual(selected['mattermostOperator']['values']['nodeSelector'], {'role.example.test/operator':'true'})
            revised = selected['mattermost']['values']
            self.assertEqual(revised['nodeSelector'],inputs['mattermost_runtime_node_selector'])
            self.assertEqual(revised['resources']['requests'],{'cpu':'100m','memory':'1Gi'})
            self.assertEqual(revised['resources']['limits'],original_limits)
            self.assertEqual(revised['postgresql']['primary']['resources']['requests'],{'cpu':'50m','memory':'256Mi'})
            self.assertEqual(revised['postgresql']['primary']['resources']['limits'],db_limits)
            for delta in ({'mattermost_runtime_origin':'http://chat.example.test'}, {'mattermost_runtime_api_cidrs':['0.0.0.0/0']}, {'mattermost_runtime_ca_sha256':'bad'}):
                r=self.run_play({**inputs,**delta}); self.assertNotEqual(r.returncode,0)

if __name__ == '__main__':
    unittest.main()
