"""Synthetic local OpenBao and actual official-chart/Fleet rendering; no cluster calls."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'local-lab/openbao'


@unittest.skipUnless(os.environ.get('BAO_BIN'), 'set BAO_BIN for synthetic policy integration')
class PolicyIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        cls.url = f'http://127.0.0.1:{port}/v1/'
        cls.root = 'synthetic-test-root'
        cls.proc = subprocess.Popen([os.environ['BAO_BIN'], 'server', '-dev',
            f'-dev-listen-address=127.0.0.1:{port}', f'-dev-root-token-id={cls.root}'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env={**os.environ, 'BAO_TOKEN': '', 'VAULT_TOKEN': ''})
        cls.addClassCleanup(cls.stop)
        for _ in range(100):
            try:
                cls.api('GET', 'sys/health')
                break
            except (OSError, urllib.error.URLError):
                time.sleep(.1)
        else:
            raise RuntimeError('local synthetic OpenBao did not become ready')
        for mount in ('platform', 'tenants'):
            cls.api('POST', f'sys/mounts/{mount}', {'type':'kv','options':{'version':'2'}})
        for file in CONFIG.joinpath('policies').glob('*.hcl'):
            cls.api('PUT', 'sys/policies/acl/' + file.stem, {'policy':file.read_text()})
        cls.tokens = {}
        for role, policies in {'home':['human-home'], 'platform':['human-platform', 'human-platform-tenant-access'],
                'restricted-platform':['human-platform'], 'eso':['eso-home-portal']}.items():
            cls.tokens[role] = cls.api('POST', 'auth/token/create', {'policies':policies, 'no_default_policy':True})['auth']['client_token']
        for path in ('tenants/data/home/tenant-home-portal/registry/ghcr',
                'tenants/data/bravo/tenant-bravo/registry/ghcr', 'platform/data/registry/ghcr'):
            cls.api('POST', path, {'data':{'dockerconfigjson':'synthetic-initial'}})

    @classmethod
    def stop(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)

    @classmethod
    def api(cls, method, path, payload=None, token=None):
        req = urllib.request.Request(cls.url + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={'X-Vault-Token':token or cls.root, 'Content-Type':'application/json'}, method=method)
        with urllib.request.urlopen(req, timeout=5) as response:
            raw=response.read()
            return json.loads(raw) if raw else {}

    def denied(self, method, path, role, payload=None):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.api(method, path, payload, self.tokens[role])
        self.assertEqual(caught.exception.code, 403)

    def test_home_crud_and_cross_scope_denials(self):
        path='tenants/data/home/tenant-home-portal/application/example'
        for value in ('synthetic-first', 'synthetic-second'):
            self.api('POST', path, {'data':{'value':value}}, self.tokens['home'])
            self.assertEqual(self.api('GET', path, token=self.tokens['home'])['data']['data']['value'], value)
        self.api('DELETE', path, token=self.tokens['home'])
        self.api('DELETE', path.replace('/data/', '/metadata/'), token=self.tokens['home'])
        for path in ('tenants/data/bravo/tenant-bravo/registry/ghcr', 'platform/data/registry/ghcr',
                     'tenants/data/home/unowned-namespace/example'):
            for method in ('GET', 'POST', 'DELETE'):
                self.denied(method, path, 'home', {'data':{'value':'synthetic'}} if method=='POST' else None)
        self.denied('LIST', 'tenants/metadata/', 'home')

    def test_eso_exact_path_read_only_and_rotation(self):
        path='tenants/data/home/tenant-home-portal/registry/ghcr'
        self.api('POST', path, {'data':{'dockerconfigjson':'synthetic-rotated'}}, self.tokens['home'])
        self.assertEqual(self.api('GET', path, token=self.tokens['eso'])['data']['data']['dockerconfigjson'], 'synthetic-rotated')
        for method in ('POST', 'DELETE'):
            self.denied(method, path, 'eso', {'data':{}} if method=='POST' else None)
        for path in ('tenants/data/home/tenant-home-portal/application/example',
                     'tenants/data/home/tenant-home-nextcloud/registry/ghcr',
                     'tenants/data/bravo/tenant-bravo/registry/ghcr', 'platform/data/registry/ghcr'):
            self.denied('GET', path, 'eso')
        self.denied('LIST', 'tenants/metadata/home/tenant-home-portal', 'eso')

    def test_platform_access_can_be_removed_independently(self):
        for path in ('platform/data/registry/ghcr','tenants/data/bravo/tenant-bravo/registry/ghcr'):
            self.api('GET', path, token=self.tokens['platform'])
        self.api('GET','platform/data/registry/ghcr',token=self.tokens['restricted-platform'])
        self.denied('GET','tenants/data/home/tenant-home-portal/registry/ghcr','restricted-platform')
        for role in self.tokens:
            self.denied('POST','sys/mounts/forbidden',role,{'type':'kv'})


@unittest.skipUnless(os.environ.get('OPENBAO_CHART') and os.environ.get('ESO_CHART') and shutil.which('helm') and shutil.which('fleet'), 'set chart directories and Helm/Fleet PATH')
class Rendering(unittest.TestCase):
    def chart(self, name, chart, namespace, bundle):
        return list(yaml.safe_load_all(subprocess.check_output(['helm','template',name,os.environ[chart],'-n',namespace,
            '-f',str(ROOT/'local-lab/fleet/bundles'/bundle/'values.yaml')], text=True)))

    def test_openbao_tls_persistence_no_injector(self):
        objects=self.chart('openbao','OPENBAO_CHART','openbao','secrets-openbao')
        sts=next(x for x in objects if x and x['kind']=='StatefulSet')
        self.assertEqual(sts['spec']['replicas'],1)
        self.assertEqual({x['metadata']['name'] for x in sts['spec']['volumeClaimTemplates']},{'data','audit'})
        config=next(x for x in objects if x and x['kind']=='ConfigMap')['data']['extraconfig-from-values.hcl']
        self.assertIn('storage "raft"',config)
        self.assertIn('tls_cert_file',config)
        self.assertNotIn('tls_disable = 1',config)
        self.assertFalse(any(x and x['kind']=='Deployment' for x in objects))

    def test_eso_namespace_scope_and_no_token_wildcard(self):
        objects=self.chart('eso-home-portal','ESO_CHART','external-secrets','eso-home-portal')
        self.assertFalse(any(x and x['kind'] in ('ClusterRole','ClusterRoleBinding','ValidatingWebhookConfiguration') for x in objects))
        for x in objects:
            if x and x['kind']=='Role':
                for rule in x['rules']:
                    self.assertNotIn('serviceaccounts/token',rule.get('resources',[]))
        deployment=next(x for x in objects if x and x['kind']=='Deployment')
        args=deployment['spec']['template']['spec']['containers'][0]['args']
        self.assertIn('--namespace=tenant-home-portal',args)

    def test_disabled_and_enabled_delivery_actual_fleet(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'bundle'
            shutil.copytree(ROOT/'local-lab/secrets-config',bundle)
            def render():
                return [x for x in yaml.safe_load_all(subprocess.check_output(['fleet','test','-N','local',str(bundle)], text=True, env={**os.environ,'KUBECONFIG':'/dev/null'})) if x]
            self.assertFalse(render())
            values=yaml.safe_load((bundle/'values.yaml').read_text())
            values['enabled']=True
            (bundle/'values.yaml').write_text(yaml.safe_dump(values))
            objects=render()
            self.assertEqual(len(objects),5)
            self.assertTrue(all(x['metadata']['namespace']=='tenant-home-portal' for x in objects))
            es=next(x for x in objects if x['kind']=='ExternalSecret')
            self.assertEqual(es['spec']['target']['creationPolicy'],'Merge')
            self.assertEqual(es['spec']['target']['deletionPolicy'],'Retain')
            self.assertEqual(es['spec']['target']['template']['data']['.dockerconfigjson'],'{{ .dockerconfigjson }}')
            store=next(x for x in objects if x['kind']=='SecretStore')
            self.assertEqual(store['spec']['provider']['vault']['auth']['kubernetes']['serviceAccountRef']['audiences'],['openbao'])
            role=next(x for x in objects if x['kind']=='Role')
            self.assertEqual(role['rules'][0]['resourceNames'],['openbao-sync'])
            home=yaml.safe_load((bundle/'tenants/home.yaml').read_text())
            home['remoteKey']='bravo/tenant-bravo/registry/ghcr'
            (bundle/'tenants/home.yaml').write_text(yaml.safe_dump(home))
            result=subprocess.run(['fleet','test','-N','local',str(bundle)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)


class StaticContract(unittest.TestCase):
    def test_auth_roles_are_bound_and_distinct(self):
        home=json.loads((CONFIG/'roles/human-home.json').read_text())
        self.assertEqual(home['bound_claims'],{'groups':['/tenants/home/admins']})
        self.assertEqual(home['user_claim'],'sub')
        eso=json.loads((CONFIG/'roles/eso-home-portal.json').read_text())
        self.assertEqual(eso['bound_service_account_namespaces'],['tenant-home-portal'])
        self.assertEqual(eso['bound_service_account_names'],['openbao-sync'])
        self.assertEqual(eso['audience'],'openbao')
        self.assertEqual(eso['token_policies'],['eso-home-portal'])


if __name__=='__main__':
    unittest.main()
