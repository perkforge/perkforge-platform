"""Public payload rendering and native chart integration; never live configuration."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[3]
SSO = ROOT / 'big-bang-bootstrap/configuration/authorization/sso/mattermost'

class MattermostPreparation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.output = self.d / 'review'
        self.inputs = dict(mattermost_sso_render=True, mattermost_sso_output=str(self.output),
                          mattermost_sso_origin='https://mattermost.example.test',
                          mattermost_sso_issuer='https://identity.example.test/auth/realms/perkforge')

    def run_play(self, inputs=None, check=False, success=True):
        p = subprocess.run(['ansible-playbook', str(SSO / 'prepare.yaml'), '-e', json.dumps(self.inputs if inputs is None else inputs)] + (['--check'] if check else []),
                           env=dict(os.environ, KUBECONFIG='/dev/null', ANSIBLE_LOCAL_TEMP=str(self.d/'local'), ANSIBLE_REMOTE_TEMP=str(self.d/'remote')),
                           text=True, capture_output=True, timeout=90)
        self.assertEqual(p.returncode == 0, success, p.stdout+p.stderr)

    def test_defaults_check_and_repeat_preserve_output(self):
        self.run_play({})
        self.run_play(check=True)
        self.assertFalse(self.output.exists())
        self.run_play()
        before = {p.name:p.read_bytes() for p in self.output.iterdir()}
        self.run_play(success=False)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.output.iterdir()})

    def test_exact_disabled_client_and_public_values(self):
        self.run_play()
        c = json.loads((self.output/'client.json').read_text())
        self.assertEqual(c['clientId'],'mattermost')
        self.assertEqual(c['redirectUris'],[self.inputs['mattermost_sso_origin']+'/signup/openid/complete'])
        self.assertEqual(c['webOrigins'],[])
        for k in ('enabled','publicClient','directAccessGrantsEnabled','serviceAccountsEnabled','implicitFlowEnabled','fullScopeAllowed'):
            self.assertFalse(c[k])
        self.assertNotIn('secret',c)
        self.assertEqual(len(c['protocolMappers']),1)
        v=yaml.safe_load((self.output/'values.yaml').read_text())['addons']['mattermost']
        self.assertFalse(v['enabled']); self.assertTrue(v['flux']['suspend'])
        self.assertFalse(v['values']['sso']['enabled'])
        self.assertEqual(v['values']['ingress'],dict(enabled=False,host='mattermost.example.test'))
        env={x['name']:x for x in v['values']['existingSecretEnvs']}
        self.assertEqual(env['MM_OPENIDSETTINGS_DISCOVERYENDPOINT']['value'],self.inputs['mattermost_sso_issuer']+'/.well-known/openid-configuration')
        self.assertEqual(env['MM_OPENIDSETTINGS_SECRET']['valueFrom']['secretKeyRef'],dict(name='mattermost-oidc-client',key='client-secret'))
        self.assertEqual(env['MM_TEAMSETTINGS_ENABLEUSERCREATION']['value'],'false')
        self.assertEqual(env['SSL_CERT_FILE']['value'],'/etc/mattermost-identity-ca/ca.crt')
        self.assertEqual(self.output.stat().st_mode & 0o777,0o700)
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in self.output.iterdir()))

    def test_bad_endpoints_and_output_fail_closed(self):
        for changes in [dict(mattermost_sso_origin=x) for x in ('http://app.test','https://app.test/path','https://user@app.test','https://app.INVALID','https://app.test\n','https://identity.example.test')] + [dict(mattermost_sso_issuer='https://identity.example.test/realms/foreign'),dict(mattermost_sso_output='relative')]:
            self.run_play(self.inputs|changes,success=False)
            self.assertFalse(self.output.exists())

    def test_native_site_url_and_secret_ca_consumers(self):
        from fixtures.collaboration import package_render
        self.run_play()
        _,objects=package_render(ROOT/'big-bang-bootstrap','mattermost',('mattermost-operator',),extra_values=(self.output/'values.yaml',))['mattermost']
        secret=next(x for x in objects if x['kind']=='Secret' and x['metadata']['name']=='mattermost-envs')
        self.assertEqual(secret['stringData']['MM_SERVICESETTINGS_SITEURL'],self.inputs['mattermost_sso_origin'])
        cr=next(x for x in objects if x['kind']=='Mattermost')
        self.assertEqual(cr['spec']['volumes'],[dict(name='identity-ca',configMap=dict(name='mattermost-identity-ca'))])
        self.assertEqual(cr['spec']['volumeMounts'],[dict(name='identity-ca',mountPath='/etc/mattermost-identity-ca',readOnly=True)])
        env={x['name']:x for x in cr['spec']['mattermostEnv']}
        self.assertEqual(env['MM_OPENIDSETTINGS_SECRET']['valueFrom']['secretKeyRef']['name'],'mattermost-oidc-client')
        self.assertEqual(sum(x['name']=='MM_SERVICESETTINGS_SITEURL' for x in cr['spec']['mattermostEnv']),1)
