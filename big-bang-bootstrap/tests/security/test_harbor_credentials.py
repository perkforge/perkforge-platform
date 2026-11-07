"""Protected Harbor assembly/delivery: synthetic inputs, real Ansible, fake kubectl.

Never opens real kubeconfig/credentials or contacts a cluster. Cryptographic generation
here is TEST FIXTURE ONLY; the production helpers accept externally prepared inputs.
"""
import base64
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
import bcrypt

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'configuration/packages/harbor'
spec = importlib.util.spec_from_file_location('harbor_credentials', PACKAGE / 'filter_plugins/harbor_credentials.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
CONTRACTS = yaml.safe_load((PACKAGE / 'tasks/contracts.yaml').read_text())[0]['ansible.builtin.set_fact']['harbor_contracts']
UID = 'synthetic-namespace-0001'
PASSWORD = 'SYNTHETIC-ONLY-HARBOR-password12345'


def pem(cert):
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def keypem(key):
    return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()


def certificates(extra_san=None, expired=False):
    now = datetime.now(timezone.utc)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Synthetic Harbor CA')])
    ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=30))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(x509.KeyUsage(True, False, False, False, False, True, True, False, False), critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
          .sign(key, hashes.SHA256()))
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    certs = {}
    for service in ('valkey','core','jobservice','registry','portal','service'):
        hosts = ['harbor.perkforge.home.arpa'] if service == 'service' else ['harbor-' + service + suffix for suffix in ('','.harbor.svc','.harbor.svc.cluster.local')]
        if extra_san:
            hosts.append(extra_san)
        leaf = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hosts[0])]))
                .issuer_name(name).public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(days=5)).not_valid_after(now + timedelta(days=-2 if expired else 7))
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(x509.SubjectAlternativeName([x509.DNSName(h) for h in hosts]), critical=False)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                .add_extension(x509.KeyUsage(True, False, True, False, False, False, False, False, False), critical=True)
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()), critical=False)
                .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), critical=False)
                .sign(key, hashes.SHA256()))
        certs[service] = pem(leaf)
    return pem(ca), certs, keypem(leaf_key), ca.fingerprint(hashes.SHA256()).hex()


def manifest(profile, ca, cert, key):
    values = {'harbor-database': {'username':'harbor','password':PASSWORD},
              'harbor-valkey-acl': {'default':PASSWORD}, 'harbor-redis':{'REDIS_PASSWORD':PASSWORD},
              'harbor-valkey-tls':{'ca.crt':ca,'tls.crt':cert['valkey'],'tls.key':key}}
    if profile == 'application':
        values = {}
        for name, contract in CONTRACTS[profile].items():
            values[name] = {k: PASSWORD for k in contract['keys']}
        values['harbor-encryption-key']['secretKey'] = 'SyntheticKey1234'
        values['harbor-xsrf']['CSRF_KEY'] = 'SyntheticXsrfKey1234567890123456'
        values['harbor-registry-credentials'] = {'REGISTRY_PASSWD':PASSWORD, 'REGISTRY_HTPASSWD':'harbor_registry_user:' + bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()}
        values['harbor-token-signing'] = {'tls.crt':cert['core'],'tls.key':key}
        for part in ('core','jobservice','registry','portal'):
            values['harbor-' + part + '-tls'] = {'ca.crt':ca,'tls.crt':cert[part],'tls.key':key}
        values['harbor-service-tls'] = {'tls.crt':cert['service'],'tls.key':key}
        values['harbor-public-ca'] = {'ca.crt':ca}
        values['harbor-internal-ca'] = {'ca.crt':ca}
        values['private-registry'] = {'.dockerconfigjson':json.dumps({'auths':{'registry1.dso.mil':{'auth':base64.b64encode(b'synthetic:fixture-only').decode()}}})}
    return {'apiVersion':'v1','kind':'List','items':[
        {'apiVersion':'v1','kind':'Secret','immutable':True,
         'metadata':{'name':n,'namespace':'harbor','labels':{'perkforge.io/owner':c['owner']},'annotations':{'perkforge.io/namespace-uid':UID}},
         'type':c['type'],'stringData':values[n]} for n,c in CONTRACTS[profile].items()]}


def api_object(item):
    obj = copy.deepcopy(item)
    obj['data'] = {k:base64.b64encode(v.encode()).decode() for k,v in obj.pop('stringData').items()}
    obj['metadata']['uid'] = 'synthetic-secret-' + obj['metadata']['name']
    return obj


FAKE = r'''#!/usr/bin/python3
import base64, json, sys
from pathlib import Path
root = Path(__file__).parent
args = sys.argv[1:]
statefile = root / 'state.json'
state = json.loads(statefile.read_text())
def event(action, name=''):
    with (root/'events.jsonl').open('a') as f: f.write(json.dumps([action,name])+'\n')
if 'config' in args:
    event('config'); print(json.dumps(state.get('config',{'current-context':'synthetic-context','contexts':[{'name':'synthetic-context','context':{'cluster':'synthetic'}}],'clusters':[{'name':'synthetic','cluster':{'server':'https://synthetic.invalid:6443'}}]}))); sys.exit(0)
if 'get' in args:
    i=args.index('get'); kind,name=args[i+1:i+3]; event('get-'+kind,name)
    if kind=='namespace':
        if name=='kube-system': print(state.get('cluster','synthetic-cluster-0001'))
        else: print(json.dumps(state.get('namespace',{'apiVersion':'v1','kind':'Namespace','metadata':{'name':'harbor','uid':'synthetic-namespace-0001','labels':{'perkforge.io/owner':'harbor-foundation-v1'}},'status':{'phase':'Active'}})))
    else:
        obj=state['objects'].get(name)
        if obj:
            if state.get('corrupt_readback')==name and name in state.get('created',[]): obj['immutable']=False
            print(json.dumps(obj))
        elif '--ignore-not-found' not in args: sys.exit(1)
    sys.exit(0)
if 'create' in args:
    obj=json.load(sys.stdin); name=obj['metadata']['name']; dry='--dry-run=server' in args
    event('dryrun' if dry else 'create',name)
    if state.get('dryrun_fail' if dry else 'create_fail')==name: sys.exit(1)
    obj['data']={k:base64.b64encode(v.encode()).decode() for k,v in obj.pop('stringData').items()}
    obj['metadata']['uid']='synthetic-secret-'+name
    if not dry:
        if name in state['objects']: sys.exit(1)
        state['objects'][name]=obj; state.setdefault('created',[]).append(name); statefile.write_text(json.dumps(state))
    print(json.dumps(obj)); sys.exit(0)
sys.exit(2)
'''


class GuardValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ca,cls.cert,cls.key,cls.pin=certificates()
        cls.data=manifest('data',cls.ca,cls.cert,cls.key)
        cls.app=manifest('application',cls.ca,cls.cert,cls.key)

    def valid(self, m, profile='data'):
        return guard.manifest_valid(m, CONTRACTS[profile], UID, profile, [self.pin], self.pin, self.pin, self.pin)

    def test_valid_profiles_and_native_schema(self):
        self.assertTrue(self.valid(self.data))
        self.assertTrue(self.valid(self.app,'application'))
        self.assertEqual(len(self.data['items']),4)
        self.assertEqual(len(self.app['items']),16)

    def test_schema_value_and_ownership_mutations(self):
        variants=[]
        def mutate(fn):
            m=copy.deepcopy(self.data); fn(m); variants.append(m)
        mutate(lambda m: m['items'].append(m['items'][0]))
        mutate(lambda m: m['items'][0]['metadata']['labels'].update({'foreign':'owner'}))
        mutate(lambda m: m['items'][0]['metadata']['annotations'].update({'foreign':'annotation'}))
        mutate(lambda m: m['items'][0]['metadata'].update({'ownerReferences':[]}))
        mutate(lambda m: m['items'][0]['metadata'].update({'namespace':'other'}))
        mutate(lambda m: m['items'][0].update({'immutable':False}))
        mutate(lambda m: m['items'][0]['stringData'].update({'username':'postgres'}))
        mutate(lambda m: m['items'][0]['stringData'].update({'password':PASSWORD+'\n'}))
        mutate(lambda m: m['items'][2]['stringData'].update({'REDIS_PASSWORD':'different-password-123456789'}))
        mutate(lambda m: m['items'][1]['stringData'].update({'default':'has whitespace invalid here'}))
        mutate(lambda m: m['items'][3]['stringData'].update({'ca.crt':self.ca+self.key}))
        mutate(lambda m: m['items'][3]['stringData'].update({'tls.crt':self.ca}))
        for m in variants:
            with self.subTest(index=variants.index(m)): self.assertFalse(self.valid(m))

    def test_application_rejects_wrong_keys_password_recipient_or_trust(self):
        def changed(name,key,value):
            m=copy.deepcopy(self.app)
            next(i for i in m['items'] if i['metadata']['name']==name)['stringData'][key]=value
            return m
        for m in [changed('harbor-encryption-key','secretKey','é'*16),
                  changed('harbor-registry-credentials','REGISTRY_PASSWD','wrong-synthetic-password'),
                  changed('harbor-token-signing','tls.key',keypem(rsa.generate_private_key(public_exponent=65537,key_size=2048))),
                  changed('private-registry','.dockerconfigjson','{"auths":{"foreign.invalid":{"auth":"dTpw"}}}'),
                  changed('harbor-public-ca','ca.crt',self.ca+self.ca),
                  changed('harbor-public-ca','ca.crt',self.ca+self.key)]:
            self.assertFalse(self.valid(m,'application'))
        self.assertFalse(guard.manifest_valid(self.app,CONTRACTS['application'],UID,'application',[],self.pin))
        self.assertFalse(guard.manifest_valid(self.app,CONTRACTS['application'],UID,'application',[self.pin],'0'*64))

    def test_initial_admin_preserves_native_password_change_compatibility(self):
        # Initial bootstrap hashes directly; later API/UI changes require8–128 and all3 classes.
        # https://github.com/goharbor/harbor/blob/v2.15.2/src/server/v2.0/handler/user.go#L431-L438
        for value in ('Aa1'+'x'*126, 'a1'*16, 'A1'*16, 'Aa'*16, 'éAa1'*8):
            bad=copy.deepcopy(self.app)
            next(i for i in bad['items'] if i['metadata']['name']=='harbor-initial-admin')['stringData']['HARBOR_ADMIN_PASSWORD']=value
            self.assertFalse(self.valid(bad,'application'))
        self.assertTrue(self.valid(self.app,'application'))

    def test_xsrf_requires_exactly_32_ascii_bytes(self):
        # https://github.com/goharbor/harbor/blob/v2.15.2/src/server/middleware/csrf/csrf.go#L69-L79
        for value in ('x'*31, 'x'*33, 'é'*32, 'é'*16):
            bad=copy.deepcopy(self.app)
            next(i for i in bad['items'] if i['metadata']['name']=='harbor-xsrf')['stringData']['CSRF_KEY']=value
            self.assertFalse(self.valid(bad,'application'))
        self.assertTrue(self.valid(self.app,'application'))

    def test_tls_rejects_extra_wildcard_expired_and_wrong_ca(self):
        for extra,expired in [('unrelated.invalid',False),('*.harbor.svc',False),(None,True)]:
            ca,cert,key,_=certificates(extra_san=extra,expired=expired)
            self.assertFalse(self.valid(manifest('data',ca,cert,key)))
        other_ca,_,_,_=certificates()
        bad=copy.deepcopy(self.data)
        bad['items'][-1]['stringData']['ca.crt']=other_ca
        self.assertFalse(self.valid(bad))

    def test_each_application_trust_purpose_is_required(self):
        for missing in range(3):
            purposes=[self.pin]*3; purposes[missing]='0'*64
            self.assertFalse(guard.manifest_valid(self.app,CONTRACTS['application'],UID,'application',[self.pin],*purposes))

    def test_existing_objects_are_exact_immutable_and_uncontrolled(self):
        desired=self.data['items'][0]; obj=api_object(desired)
        self.assertTrue(guard.secret_matches(obj,desired))
        for key,value in [('deletionTimestamp','now'),('ownerReferences',[]),('finalizers',['foreign'])]:
            bad=copy.deepcopy(obj); bad['metadata'][key]=value; self.assertFalse(guard.secret_matches(bad,desired))
        for field,value in [('immutable',False),('data',{}),('type','Opaque')]:
            bad=copy.deepcopy(obj); bad[field]=value; self.assertFalse(guard.secret_matches(bad,desired))
        bad=copy.deepcopy(obj); bad['metadata']['annotations']['foreign']='x'; self.assertFalse(guard.secret_matches(bad,desired))

    def test_path_metadata_rejects_symlink_hardlink_uid_and_weak_modes(self):
        path='/home/test/private/input'; root='/home/test/private'
        records=[]
        for p in guard.ancestors(path):
            records.append({'item':p,'stat':{'exists':True,'islnk':False,'isdir':p!=path,'isreg':p==path,'uid':1000 if p.startswith('/home/test') else 0,'mode':'0600' if p==path else ('0700' if p==root else '0755'),'nlink':1,'size':42}})
        self.assertTrue(guard.protected_path(records,path,root,1000))
        for index,key,value in [(-1,'nlink',2),(-1,'uid',0),(-1,'mode','0640'),(-2,'mode','0755'),(-2,'islnk',True),(1,'mode','0777')]:
            bad=copy.deepcopy(records); bad[index]['stat'][key]=value; self.assertFalse(guard.protected_path(bad,path,root,1000))
        self.assertFalse(guard.protected_path(records,path+'/../input',root,1000))


class RealAnsibleCredentials(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ca,cls.cert,cls.key,cls.pin=certificates()
        cls.data=manifest('data',cls.ca,cls.cert,cls.key)
        cls.app=manifest('application',cls.ca,cls.cert,cls.key)

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='harbor-credential-test-',dir=Path.home())
        self.root=Path(self.tmp.name); self.root.chmod(0o700)
        self.manifest=self.root/'credentials.json'
        self.write(self.manifest,json.dumps(self.data))
        self.write(self.root/'kubeconfig','SYNTHETIC-NONFUNCTIONAL-KUBECONFIG')
        self.write(self.root/'kubectl',FAKE,0o700)
        self.state={'objects':{}}
        self.save_state()
        self.vars={'harbor_private_root':str(self.root),'harbor_credentials_manifest':str(self.manifest),
                   'harbor_expected_namespace_uid':UID,'harbor_credentials_profile':'data',
                   'harbor_kubeconfig':str(self.root/'kubeconfig'),'harbor_kubectl':str(self.root/'kubectl'),
                   'harbor_context':'synthetic-context','harbor_expected_api':'https://synthetic.invalid:6443',
                   'harbor_expected_cluster_uid':'synthetic-cluster-0001',
                   'harbor_public_ca_sha256':[self.pin],'harbor_database_ca_sha256':self.pin,
                   'harbor_valkey_ca_sha256':self.pin,'harbor_identity_ca_sha256':self.pin}

    def tearDown(self): self.tmp.cleanup()
    def write(self,path,content,mode=0o600): path.write_text(content); path.chmod(mode)
    def save_state(self): self.write(self.root/'state.json',json.dumps(self.state))
    def events(self):
        p=self.root/'events.jsonl'
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
    def run_play(self,name,extra=None,check=False,success=True):
        args=dict(self.vars); args.update(extra or {})
        self.write(self.root/'vars.json',json.dumps(args))
        env=dict(os.environ,ANSIBLE_NOCOLOR='1',ANSIBLE_LOCAL_TEMP=str(self.root/'ansible-local'),ANSIBLE_REMOTE_TEMP=str(self.root/'ansible-remote'),PYTHONDONTWRITEBYTECODE='1')
        result=subprocess.run(['ansible-playbook','-i','localhost,',str(PACKAGE/name),'-e','@'+str(self.root/'vars.json')]+(['--check'] if check else []),text=True,capture_output=True,env=env,timeout=240)
        output=result.stdout+result.stderr
        self.assertNotIn(PASSWORD,output)
        self.assertNotIn('BEGIN PRIVATE KEY',output)
        self.assertEqual(result.returncode==0,success,output)
        return output
    def deliver(self,**kwargs):
        return self.run_play('deliver-credentials.yaml',{'harbor_delivery_run':True,'harbor_delivery_scope':'harbor-data-credential-delivery-v1'},**kwargs)

    def test_default_and_check_are_inert_with_nonexistent_private_inputs(self):
        self.vars['harbor_credentials_manifest']='/DOES-NOT-EXIST/private'
        for name,flag,scope in [('prepare-credentials.yaml','harbor_credentials_run','harbor_credentials_scope'),('deliver-credentials.yaml','harbor_delivery_run','harbor_delivery_scope')]:
            self.run_play(name)
            self.run_play(name,{flag:True,scope:'UNAPPROVED'},check=True)
        self.assertEqual(self.events(),[])

    def test_assembly_repeat_and_application_profile(self):
        for profile,source in [('data',self.data),('application',self.app)]:
            inputs={}
            for obj in source['items']:
                inputs[obj['metadata']['name']]={}
                for key,value in obj['stringData'].items():
                    p=self.root/(obj['metadata']['name']+'-'+key.replace('/','_'))
                    self.write(p,value); inputs[obj['metadata']['name']][key]=str(p)
            out=self.root/(profile+'-assembled.json')
            args={'harbor_credentials_run':True,'harbor_credentials_scope':'harbor-'+profile+'-private-assembly-v1','harbor_credentials_profile':profile,'harbor_credentials_inputs':inputs,'harbor_credentials_manifest':str(out)}
            self.run_play('prepare-credentials.yaml',args)
            self.assertEqual(json.loads(out.read_text()),source)
            self.assertEqual(out.stat().st_mode & 0o777,0o600)
            repeat=self.run_play('prepare-credentials.yaml',args)
            self.assertIn('changed=0',repeat)
        self.assertEqual(self.events(),[])

    def test_create_repeat_and_preflight_order(self):
        self.deliver()
        events=self.events(); creates=[x for x in events if x[0]=='create']
        self.assertEqual(len(creates),4)
        self.assertEqual(sum(x[0]=='dryrun' for x in events[:events.index(creates[0])]),4)
        for index,event in enumerate(events):
            if event[0]=='create': self.assertEqual(events[index+1],['get-secret',event[1]])
        count=len(events); output=self.deliver()
        self.assertIn('changed=0',output)
        self.assertFalse(any(x[0] in ('create','dryrun') for x in self.events()[count:]))

    def test_application_delivery_and_no_change_repeat(self):
        self.write(self.manifest,json.dumps(self.app))
        self.vars['harbor_credentials_profile']='application'
        args={'harbor_delivery_run':True,'harbor_delivery_scope':'harbor-application-credential-delivery-v1'}
        self.run_play('deliver-credentials.yaml',args)
        self.assertEqual(sum(e[0]=='create' for e in self.events()),16)
        before=json.loads((self.root/'state.json').read_text())['objects']
        count=len(self.events())
        output=self.run_play('deliver-credentials.yaml',args)
        self.assertIn('changed=0',output)
        self.assertFalse(any(e[0] in ('create','dryrun') for e in self.events()[count:]))
        self.assertEqual(json.loads((self.root/'state.json').read_text())['objects'],before)

    def test_actual_cluster_and_namespace_uid_mismatch_stop_before_secrets(self):
        self.state['cluster']='wrong-cluster-0001'; self.save_state()
        self.deliver(success=False)
        self.assertFalse(any(e[0] in ('get-secret','create','dryrun') for e in self.events()))
        del self.state['cluster']
        self.state['namespace']={'apiVersion':'v1','kind':'Namespace','metadata':{'name':'harbor','uid':'recreated-namespace-0001','labels':{'perkforge.io/owner':'harbor-foundation-v1'}},'status':{'phase':'Active'}}
        self.save_state(); count=len(self.events()); self.deliver(success=False)
        self.assertIn(['get-namespace','harbor'],self.events()[count:])
        self.assertFalse(any(e[0] in ('get-secret','create','dryrun') for e in self.events()[count:]))

    def test_foreign_last_target_prevents_all_creates(self):
        last=api_object(self.data['items'][-1]); last['metadata']['labels']['foreign']='x'
        self.state['objects'][last['metadata']['name']]=last; self.save_state()
        self.deliver(success=False)
        self.assertFalse(any(x[0] in ('create','dryrun') for x in self.events()))

    def test_partial_create_failure_stops_and_resumes_without_rotation(self):
        self.state['create_fail']='harbor-valkey-acl'; self.save_state()
        self.deliver(success=False)
        self.assertEqual([x[1] for x in self.events() if x[0]=='create'],['harbor-database','harbor-valkey-acl'])
        self.state=json.loads((self.root/'state.json').read_text()); first=copy.deepcopy(self.state['objects']['harbor-database']); del self.state['create_fail']; self.save_state()
        count=len(self.events()); self.deliver()
        self.assertNotIn(['create','harbor-database'],self.events()[count:])
        self.assertEqual(json.loads((self.root/'state.json').read_text())['objects']['harbor-database'],first)

    def test_bad_immediate_readback_stops_before_later_creates(self):
        self.state['corrupt_readback']='harbor-database'; self.save_state()
        self.deliver(success=False)
        self.assertEqual([x[1] for x in self.events() if x[0]=='create'],['harbor-database'])

    def test_failed_dryrun_prevents_all_creates(self):
        self.state['dryrun_fail']='harbor-redis'; self.save_state()
        self.deliver(success=False)
        self.assertFalse(any(x[0]=='create' for x in self.events()))

    def test_unprotected_input_stops_before_api(self):
        self.manifest.chmod(0o644)
        self.deliver(success=False)
        self.assertEqual(self.events(),[])

    def test_insecure_proxy_and_server_name_configs_stop_before_api(self):
        for key,value in [('insecure-skip-tls-verify',True),('proxy-url','https://untrusted.invalid'),('tls-server-name','untrusted.invalid')]:
            self.state['config']={'current-context':'synthetic-context','contexts':[{'name':'synthetic-context','context':{'cluster':'synthetic'}}],'clusters':[{'name':'synthetic','cluster':{'server':'https://synthetic.invalid:6443',key:value}}]}
            self.save_state(); count=len(self.events()); self.deliver(success=False)
            self.assertEqual(self.events()[count:],[['config','']])

    def test_wrong_namespace_uid_stops_before_secret_reads(self):
        self.vars['harbor_expected_namespace_uid']='different-namespace-0001'
        self.deliver(success=False)
        self.assertEqual(self.events(),[])  # manifest binding fails before API access


class ActualTransportCompatibility(unittest.TestCase):
    """Real issuance helpers must feed the actual credential validators unchanged."""
    def test_real_issuance_outputs_pass_credential_crypto_guards(self):
        from tests.security import test_harbor_transport as transport
        fixture = transport.HarborTransport()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        before = set(fixture.out.iterdir())
        code, log = fixture.run_play(values=fixture.internal_vars())
        self.assertEqual(code, 0, log)
        self.assertNotIn('BEGIN PRIVATE KEY', log)
        internal_bundle, = set(fixture.out.iterdir()) - before
        fixture.assert_protected(internal_bundle)
        self.assertEqual((internal_bundle / 'READY').read_text().strip(), 'harbor-internal-transport-issuance-v1')
        delivery = internal_bundle / 'delivery/internal'
        ca = (delivery / 'ca.crt').read_text()
        self.assertEqual(len(guard._ca_bundle(ca)), 1)
        for service in transport.SERVICES:
            leaf = {'tls.crt': (delivery / service / 'tls.crt').read_text(),
                    'tls.key': (delivery / service / 'tls.key').read_text()}
            guard._tls(leaf, ca, [service + suffix for suffix in ('','.harbor.svc','.harbor.svc.cluster.local')])
        self.assertEqual(len(list(delivery.rglob('*.key'))), 5)
        self.assertNotIn('ca.key', [p.name for p in delivery.rglob('*')])

        before = set(fixture.out.iterdir())
        code, log = fixture.run_play(True, fixture.public_vars(), passphrase='fixture-only')
        self.assertEqual(code, 0, log)
        self.assertNotIn('fixture-only', log)
        self.assertNotIn('BEGIN PRIVATE KEY', log)
        external_bundle, = set(fixture.out.iterdir()) - before
        fixture.assert_protected(external_bundle)
        self.assertEqual((external_bundle / 'READY').read_text().strip(), 'harbor-public-leaf-issuance-v1')
        external = external_bundle / 'delivery/external'
        external_ca = (external / 'ca.crt').read_text()
        self.assertEqual(len(guard._ca_bundle(external_ca)), 1)
        guard._tls({'tls.crt': (external / 'tls.crt').read_text(),
                    'tls.key': (external / 'tls.key').read_text()}, external_ca,
                   ['harbor.perkforge.home.arpa'])
        self.assertEqual(len(guard._ca_bundle(ca + external_ca)), 2)
        self.assertEqual({p.name for p in external.iterdir()}, {'ca.crt','tls.crt','tls.key'})


if __name__=='__main__': unittest.main()
