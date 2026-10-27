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
            cls.tokens[role] = cls.api('POST', 'auth/token/create', {'policies':policies, 'no_default_policy':role == 'eso'})['auth']['client_token']
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

    def test_explicit_synthetic_enrollment_never_targets_real_pull_secret(self):
        objects=[x for x in yaml.safe_load_all(subprocess.check_output(['fleet','test','-f','enrollments/synthetic.yaml','-N','local',
            str(ROOT/'local-lab/secrets-config')],text=True,env={**os.environ,'KUBECONFIG':'/dev/null'})) if x]
        es=next(x for x in objects if x['kind']=='ExternalSecret')
        self.assertEqual(es['spec']['target']['name'],'openbao-rotation-probe')
        self.assertEqual(es['spec']['target']['creationPolicy'],'Merge')
        self.assertFalse(any(x['metadata']['name']=='portal-ghcr' for x in objects))

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
    def test_support_tls_and_network_allow_only_reviewed_peers(self):
        objects=list(yaml.safe_load_all((ROOT/'local-lab/fleet/bundles/openbao-support/resources.yaml').read_text()))
        cert=next(x for x in objects if x['kind']=='Certificate')
        self.assertEqual(cert['metadata']['namespace'],'cattle-system')
        self.assertEqual(cert['spec']['issuerRef'],{'name':'rancher','kind':'Issuer'})
        self.assertIn('openbao.openbao.svc',cert['spec']['dnsNames'])
        route=next(x for x in objects if x['kind']=='IngressRouteTCP')
        self.assertEqual(route['spec']['tls'],{'passthrough':True})
        self.assertEqual(route['spec']['routes'][0]['services'],[{'name':'openbao','port':8200}])
        policies=[x for x in objects if x['kind']=='NetworkPolicy']
        self.assertEqual(len(policies),2)
        for policy in policies:
            self.assertEqual(policy['spec']['policyTypes'],['Ingress','Egress'])
            for rule in policy['spec']['egress']:
                self.assertTrue(rule['to'])
                self.assertTrue(rule['ports'])
                for peer in rule['to']:
                    if 'ipBlock' in peer:
                        self.assertIn(peer['ipBlock']['cidr'],['10.43.0.1/32','192.168.122.201/32','10.43.163.193/32'])
                    else:
                        self.assertTrue(peer['namespaceSelector']['matchLabels'])
                        self.assertTrue(peer['podSelector']['matchLabels'])
        eso=next(x for x in policies if x['metadata']['namespace']=='external-secrets')
        self.assertEqual(eso['spec']['ingress'],[])
        for gitrepo in (ROOT/'local-lab/fleet/gitrepos').glob('*.yaml'):
            if gitrepo.name != 'openbao.yaml':
                self.assertNotIn('openbao-support',gitrepo.read_text())

    def test_operator_helpers_default_to_plan_without_access(self):
        for script in ('deliver-tls.sh','backup.sh'):
            result=subprocess.run(['bash',str(CONFIG/script)],capture_output=True,text=True,env={'PATH':'/usr/bin:/bin'})
            self.assertEqual(result.returncode,0)
            self.assertIn('Plan only',result.stdout)
            self.assertNotIn('secret value',result.stdout)

    def test_native_keycloak_payload_has_scoped_human_flow(self):
        client=json.loads((CONFIG/'config/keycloak-client.json').read_text())
        self.assertEqual(client['clientId'],'openbao')
        self.assertNotIn('secret',client)
        self.assertFalse(client['fullScopeAllowed'])
        self.assertEqual(client['attributes']['pkce.code.challenge.method'],'S256')
        for field in ('publicClient','implicitFlowEnabled','directAccessGrantsEnabled','serviceAccountsEnabled'):
            self.assertFalse(client[field])
        self.assertEqual(client['protocolMappers'][0]['config']['full.path'],'true')
        self.assertEqual(client['protocolMappers'][0]['config']['id.token.claim'],'true')

    def test_auth_roles_are_bound_and_distinct(self):
        home=json.loads((CONFIG/'roles/human-home.json').read_text())
        self.assertEqual(home['bound_claims'],{'groups':['/tenants/home/admins']})
        self.assertEqual(home['user_claim'],'sub')
        eso=json.loads((CONFIG/'roles/eso-home-portal.json').read_text())
        self.assertEqual(eso['bound_service_account_namespaces'],['tenant-home-portal'])
        self.assertEqual(eso['bound_service_account_names'],['openbao-sync'])
        self.assertEqual(eso['audience'],'openbao')
        self.assertEqual(eso['token_policies'],['eso-home-portal'])


@unittest.skipUnless(os.environ.get('BAO_BIN') and shutil.which('openssl'), 'set BAO_BIN for isolated TLS/Raft recovery test')
class PersistentRecovery(unittest.TestCase):
    def test_tls_audit_and_snapshot_restore_into_separate_data_directory(self):
        import ssl
        with tempfile.TemporaryDirectory() as directory:
            work=Path(directory)
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
                '-subj','/CN=localhost','-addext','subjectAltName=IP:127.0.0.1,DNS:localhost',
                '-keyout',str(work/'key.pem'),'-out',str(work/'cert.pem')],check=True,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            context=ssl.create_default_context(cafile=str(work/'cert.pem'))
            ports=None
            def start(name):
                nonlocal ports
                data=work/name
                data.mkdir()
                if ports is None:
                    with socket.socket() as a, socket.socket() as b:
                        a.bind(('127.0.0.1',0)); b.bind(('127.0.0.1',0))
                        ports=(a.getsockname()[1], b.getsockname()[1])
                port,cluster_port=ports
                # Exercise the actual staged audit stanza, not a second audit implementation.
                values=yaml.safe_load((ROOT/'local-lab/fleet/bundles/secrets-openbao/values.yaml').read_text())
                config=values['server']['ha']['raft']['config']
                config=config.replace('[::]:8200',f'127.0.0.1:{port}').replace('[::]:8201',f'127.0.0.1:{cluster_port}')
                config=config.replace('/openbao/tls/tls.crt',str(work/'cert.pem')).replace('/openbao/tls/tls.key',str(work/'key.pem'))
                config=config.replace('/openbao/data',str(data)).replace('/openbao/audit/audit.json','audit.json')
                config=config.replace('service_registration "kubernetes" {}','')
                config += f'\napi_addr = "https://127.0.0.1:{port}"\ncluster_addr = "https://127.0.0.1:{cluster_port}"\n'
                config=config.replace('storage "raft" {','storage "raft" {\n  node_id = "recovery-node"')
                file=work/(name+'.hcl');file.write_text(config)
                with (work/(name+'-server.log')).open('wb') as server_log:
                    proc=subprocess.Popen([os.environ['BAO_BIN'],'server','-config',str(file)],stdout=server_log,stderr=subprocess.STDOUT,
                        env={**os.environ,'BAO_TOKEN':'','VAULT_TOKEN':''},cwd=str(data))
                self.addCleanup(lambda: proc.poll() is None and (proc.terminate(),proc.wait(timeout=10)))
                url=f'https://127.0.0.1:{port}/v1/'
                def api(method,path,payload=None,token=None,binary=False):
                    raw=payload if isinstance(payload,bytes) else json.dumps(payload).encode() if payload is not None else None
                    headers={'Content-Type':'application/octet-stream' if binary else 'application/json'}
                    if token: headers['X-Vault-Token']=token
                    with urllib.request.urlopen(urllib.request.Request(url+path,data=raw,headers=headers,method=method),context=context,timeout=10) as response:
                        value=response.read()
                        return value if binary else json.loads(value) if value else {}
                for _ in range(100):
                    try: api('GET','sys/init'); break
                    except OSError: time.sleep(.1)
                else: self.fail('isolated TLS OpenBao failed to start')
                init=api('PUT','sys/init',{'secret_shares':1,'secret_threshold':1})
                api('PUT','sys/unseal',{'key':init['keys_base64'][0]})
                for _ in range(100):
                    try: api('GET','sys/health');break
                    except OSError:time.sleep(.1)
                else:self.fail('isolated OpenBao failed to become active')
                return proc,api,init
            source,api,init=start('source')
            token=init['root_token']
            api('POST','sys/mounts/tenants',{'type':'kv','options':{'version':'2'}},token)
            api('POST','tenants/data/home/tenant-home-portal/example',{'data':{'value':'synthetic-recovery-marker'}},token)
            if not shutil.which('age') or not shutil.which('age-keygen'):
                self.fail('age and age-keygen are required for the encrypted recovery acceptance')
            identity=work/'backup-age.key'
            subprocess.run(['age-keygen','-o',str(identity)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            recipient=subprocess.check_output(['age-keygen','-y',str(identity)],text=True).strip()
            backups=work/'backups';backups.mkdir(mode=0o700)
            env={**os.environ,'BAO_ADDR':f'https://127.0.0.1:{ports[0]}',
                 'BAO_TOKEN':token,'BAO_CACERT':str(work/'cert.pem'),
                 'OPENBAO_BACKUP_DIR':str(backups),'AGE_RECIPIENT':recipient,
                 'PATH':str(Path(os.environ['BAO_BIN']).parent)+os.pathsep+os.environ['PATH']}
            subprocess.run(['bash',str(CONFIG/'backup.sh'),'--apply'],env=env,check=True,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            encrypted=list(backups.glob('*.snap.age'))
            self.assertEqual(len(encrypted),1)
            self.assertEqual(encrypted[0].stat().st_mode & 0o777,0o600)
            self.assertEqual({x.suffix for x in backups.iterdir()},{'.age','.sha256'})
            subprocess.run(['sha256sum','--check',str(encrypted[0])+'.sha256'],check=True,stdout=subprocess.DEVNULL)
            snapshot=subprocess.check_output(['age','-d','-i',str(identity),str(encrypted[0])])
            self.assertGreater(len(snapshot),0)
            audit=(work/'source/audit.json').read_text()
            self.assertIn('tenants/data/home/tenant-home-portal/example',audit)
            self.assertNotIn('synthetic-recovery-marker',audit)
            self.assertEqual((work/'source/audit.json').stat().st_mode & 0o777,0o600)
            source.terminate();source.wait(timeout=10)
            restored,target,temporary=start('isolated-restore')
            # Force is confined to a fresh synthetic local server, never a real cluster.
            target('POST','sys/storage/raft/snapshot-force',snapshot,temporary['root_token'],binary=True)
            for _ in range(100):
                try:
                    state=target('GET','sys/seal-status')
                    if state['sealed']:break
                except OSError:pass
                time.sleep(.1)
            target('PUT','sys/unseal',{'key':init['keys_base64'][0]})
            for _ in range(100):
                try:
                    result=target('GET','tenants/data/home/tenant-home-portal/example',token=token)
                    break
                except urllib.error.HTTPError as exc:
                    last_status=(exc.code, json.loads(exc.read()).get('errors', []))
                    time.sleep(.1)
                except OSError:
                    last_status='connection error'
                    time.sleep(.1)
            else:
                # Local synthetic lifecycle diagnostics only; HTTP request bodies are never logged.
                lifecycle=[line for line in (work/'isolated-restore-server.log').read_text().splitlines() if any(word in line for word in ('ERROR','failed','restor','leader'))]
                self.fail('isolated snapshot restore did not become readable: ' + str(last_status) + '; lifecycle=' + '\n'.join(lifecycle[-12:]))
            self.assertEqual(result['data']['data']['value'],'synthetic-recovery-marker')
            self.assertIn('tenants/data/home/tenant-home-portal/example',(work/'isolated-restore/audit.json').read_text())

if __name__=='__main__':
    unittest.main()
