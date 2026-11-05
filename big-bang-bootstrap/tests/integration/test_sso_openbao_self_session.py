"""Policy contracts plus opt-in real OpenBao 2.7.2 in-memory loopback tests.
Never uses a kubeconfig, operator URL, existing token or production secret value.
"""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import time
import unittest
import requests
import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT/'configuration/authorization/sso/templates/openbao.yaml.j2'
SELF = {'auth/token/lookup-self': ['read'], 'auth/token/renew-self': ['update'],
        'auth/token/revoke-self': ['update'], 'sys/capabilities-self': ['update'],
        'sys/internal/ui/resultant-acl': ['read']}


def policy():
    return yaml.safe_load(TEMPLATE.read_text())['policies']['perkforge-sso-platform-admin']


class PolicyContract(unittest.TestCase):
    def test_only_five_exact_self_or_ui_endpoints_are_added(self):
        rules = dict(re.findall(r'path "([^"]+)" \{ capabilities = \[([^]]+)\] \}', policy()))
        actual = {p: re.findall(r'"([^"]+)"', caps) for p, caps in rules.items()
                  if p.startswith(('auth/', 'sys/'))}
        self.assertEqual(actual, SELF)
        self.assertTrue(yaml.safe_load(TEMPLATE.read_text())['roles']['platform-admin']['token_no_default_policy'])

    def test_tenant_values_retention_and_destruction_stay_outside_policy(self):
        rules = dict(re.findall(r'path "([^"]+)" \{ capabilities = \[([^]]+)\] \}', policy()))
        self.assertEqual(rules['tenants/metadata'], '"list"')
        self.assertEqual(rules['tenants/metadata/*'], '"list"')
        self.assertEqual(rules['platform/metadata/*'], '"read", "list"')
        for path in rules:
            self.assertNotIn('tenants/data', path)
            self.assertNotIn('/destroy', path)
            self.assertNotIn('/config', path)


@unittest.skipUnless(os.environ.get('RUN_OPENBAO_POLICY_TESTS') == '1',
                     'explicit opt-in for isolated pinned engine fixture')
class PinnedEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        binary = os.environ.get('OPENBAO_POLICY_TEST_BINARY', '')
        if not binary or not Path(binary).is_file():
            raise RuntimeError('Provide an existing OpenBao 2.7.2 binary; no download/install is performed')
        version = subprocess.check_output([binary, 'version'], text=True, timeout=10)
        if not version.startswith('OpenBao v2.7.2 (9e0a0d3c3504a0a00b45e61355afac5e35c78379)'):
            raise RuntimeError('Wrong pinned verification engine')
        cls.tmp = tempfile.TemporaryDirectory(prefix='openbao-policy-fixture-')
        cls.addClassCleanup(cls.tmp.cleanup)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        cls.base = 'http://127.0.0.1:'+str(port)+'/v1'
        # Public synthetic fixture credential only, isolated memory server.
        cls.root = 'synthetic-openbao-policy-fixture-only'
        env = {k:v for k,v in os.environ.items() if not k.startswith(('BAO_', 'VAULT_'))}
        env['BAO_DISABLE_MLOCK'] = 'true'
        helper_paths = [Path.home()/'.vault-token', Path.home()/'.bao-token']
        def helper_metadata():
            return {str(p): (p.lstat().st_mtime_ns, p.lstat().st_size, p.lstat().st_ino)
                    if p.exists() else None for p in helper_paths}
        helper_before = helper_metadata()
        def helpers_unchanged():
            if helper_metadata() != helper_before:
                raise AssertionError('Offline fixture changed a user token-helper cache')
        cls.addClassCleanup(helpers_unchanged)
        cls.proc = subprocess.Popen([binary, 'server', '-dev', '-dev-listen-address=127.0.0.1:'+str(port),
            '-dev-no-store-token', '-dev-root-token-id='+cls.root], env=env, cwd=cls.tmp.name,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        def stop():
            if cls.proc.poll() is None:
                cls.proc.terminate()
                try: cls.proc.wait(timeout=10)
                except subprocess.TimeoutExpired: cls.proc.kill(); cls.proc.wait(timeout=5)
        cls.addClassCleanup(stop)
        cls.session = requests.Session();cls.session.trust_env = False
        cls.addClassCleanup(cls.session.close)
        deadline = time.monotonic()+15
        while time.monotonic() < deadline:
            if cls.proc.poll() is not None: raise RuntimeError('Isolated engine failed to start')
            try:
                if cls.call('GET','/sys/health').status_code == 200: break
            except requests.ConnectionError: pass
            time.sleep(0.1)
        else: raise RuntimeError('Isolated engine readiness deadline')
        for mount in ('platform','tenants'):
            assert cls.call('POST','/sys/mounts/'+mount, {'type':'kv','options':{'version':'2'}}).status_code == 204
        assert cls.call('PUT','/sys/policies/acl/fixture-policy', {'policy':policy()}).status_code == 204
        # Exact former policy: reproduce failure without silently adding default.
        old = '\n'.join(line for line in policy().splitlines()
                         if not any('"'+path+'"' in line for path in SELF))
        assert cls.call('PUT','/sys/policies/acl/fixture-before', {'policy':old}).status_code == 204
        assert cls.call('POST','/tenants/data/synthetic-only', {'data':{'sample':'fixture-only'}}).status_code == 200

    @classmethod
    def call(cls, method, path, data=None, token=None):
        return cls.session.request(method, cls.base+path, json=data,
            headers={'X-Vault-Token': cls.root if token is None else token},
            timeout=5, allow_redirects=False)

    def token(self, name='fixture-policy'):
        r = self.call('POST','/auth/token/create', {'policies':[name], 'no_default_policy':True,
            'ttl':'15m','explicit_max_ttl':'1h','renewable':True})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['auth']['policies'], [name])
        return r.json()['auth']['client_token']

    def test_prior_policy_reproduces_missing_self_capabilities(self):
        token = self.token('fixture-before')
        for method,path in [('GET','/auth/token/lookup-self'),('POST','/auth/token/renew-self'),
                            ('POST','/auth/token/revoke-self'),('POST','/sys/capabilities-self'),
                            ('GET','/sys/internal/ui/resultant-acl')]:
            with self.subTest(path=path):
                self.assertEqual(self.call(method,path,{'paths':['platform/data/sample']},token).status_code,403)

    def test_self_lifecycle_ui_introspection_and_cross_token_denial(self):
        own = self.token(); other = self.token()
        self.assertEqual(self.call('GET','/auth/token/lookup-self',token=own).status_code,200)
        r = self.call('POST','/sys/capabilities-self',{'paths':['platform/data/sample','tenants/data/synthetic-only','sys/policies/acl/evil']},own)
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['data']['tenants/data/synthetic-only'],['deny'])
        self.assertEqual(r.json()['data']['sys/policies/acl/evil'],['deny'])
        r = self.call('POST','/sys/capabilities-self',{'token':self.root,'paths':['sys/policies/acl/evil']},own)
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['data']['capabilities'],['deny'])
        r = self.call('GET','/sys/internal/ui/resultant-acl',token=own)
        self.assertEqual(r.status_code,200);self.assertFalse(r.json()['data']['root'])
        r = self.call('GET','/sys/internal/ui/mounts',token=own)
        self.assertEqual(r.status_code,200)
        self.assertIn('platform/',r.json()['data']['secret'])
        self.assertIn('tenants/',r.json()['data']['secret'])
        self.assertEqual(self.call('POST','/auth/token/renew-self',{},own).status_code,200)
        for endpoint in ('lookup','renew','revoke','create'):
            self.assertEqual(self.call('POST','/auth/token/'+endpoint,{'token':other},own).status_code,403)
        self.assertEqual(self.call('POST','/auth/token/revoke-self',{'token':other},own).status_code,204)
        self.assertEqual(self.call('GET','/auth/token/lookup-self',token=own).status_code,403)
        self.assertEqual(self.call('GET','/auth/token/lookup-self',token=other).status_code,200)

    def test_platform_crud_tenant_names_and_sensitive_denials(self):
        token = self.token()
        self.assertEqual(self.call('POST','/platform/data/synthetic-only',{'data':{'sample':'fixture-only'}},token).status_code,200)
        self.assertEqual(self.call('GET','/platform/data/synthetic-only',token=token).status_code,200)
        self.assertEqual(self.call('POST','/platform/data/synthetic-only',{'data':{'sample':'fixture-updated'}},token).status_code,200)
        self.assertEqual(self.call('GET','/platform/data/synthetic-only',token=token).json()['data']['data']['sample'],'fixture-updated')
        self.assertEqual(self.call('GET','/tenants/metadata?list=true',token=token).status_code,200)
        self.assertEqual(self.call('GET','/tenants/data/synthetic-only',token=token).status_code,403)
        self.assertEqual(self.call('GET','/tenants/metadata/synthetic-only',token=token).status_code,403)
        for method,path,data in [('DELETE','/platform/metadata/synthetic-only',None),
            ('POST','/platform/metadata/synthetic-only',{'max_versions':1}),
            ('POST','/platform/destroy/synthetic-only',{'versions':[1]}),
            ('PUT','/sys/policies/acl/evil',{'policy':'path "*" { capabilities = ["sudo"] }'}),
            ('POST','/sys/auth/evil',{'type':'userpass'}),
            ('POST','/sys/mounts/evil',{'type':'kv'}),
            ('POST','/identity/entity',{'name':'evil'})]:
            with self.subTest(path=path):self.assertEqual(self.call(method,path,data,token).status_code,403)
        self.assertEqual(self.call('DELETE','/platform/data/synthetic-only',token=token).status_code,204)
        # Denied destructive/retention requests left fixture metadata intact.
        self.assertEqual(self.call('GET','/platform/metadata/synthetic-only').status_code,200)
