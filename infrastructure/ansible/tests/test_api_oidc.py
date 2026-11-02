"""Actual Ansible maintenance against synthetic root files and service/API state."""
import copy,json,os,shutil,ssl,subprocess,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
PLAY=ROOT/'playbooks/configure-api-oidc.yml'

class ApiOidcGates(unittest.TestCase):
 def test_default_check_unreviewed_and_wrong_scope_never_ssh(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);marker=d/'ssh-called';ssh=d/'ssh';ssh.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\nexit 99\n');ssh.chmod(0o700)
   inv=d/'inventory.yml';inv.write_text('all:\n  children:\n    rke2_servers:\n      hosts:\n        control-1:\n          ansible_user: fixture\n')
   for flags,rc in (([],0),(['--check','-e','api_oidc_run=true'],0),(['-e','api_oidc_run=true'],2)):
    r=subprocess.run(['ansible-playbook','-i',str(inv),str(PLAY),*flags],capture_output=True,text=True,timeout=30,env={**os.environ,'PATH':td+':'+os.environ['PATH'],'ANSIBLE_LOCAL_TEMP':td+'/local','ANSIBLE_REMOTE_TEMP':td+'/remote'})
    self.assertEqual(r.returncode,rc,r.stdout+r.stderr);self.assertFalse(marker.exists())

@unittest.skipUnless(os.environ.get('RUN_PLATFORM_SSO_TESTS'),'isolated offline maintenance fixtures only')
class ApiOidcTransaction(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.d=Path(self.t.name);self.root=self.d/'rke2';self.root.mkdir();(self.root/'config.yaml.d').mkdir()
  self.base='node-name: control-1\nagent-token: synthetic-private-value\nkube-apiserver-arg:\n- audit-log-maxage=7\n';(self.root/'config.yaml').write_text(self.base)
  (self.root/'config.yaml.d/10-unrelated.yaml').write_text('write-kubeconfig-mode: "0600"\n');(self.root/'perkforge-owner.json').write_text(json.dumps({'owner':'perkforge-infrastructure','cluster':'fixture-cluster','role':'server'}))
  self.state=self.d/'state.json';self.envfile=self.d/'environment';self.envfile.write_text('RKE2_KUBECONFIG_MODE=0600\n');self.state.write_text(json.dumps({'root':str(self.root),'ready':True,'args':['--secure-port=6443'],'env_paths':str(self.envfile)+' (ignore_errors=yes)'}))
  self.bin=self.d/'bin';self.bin.mkdir()
  for n in ('systemctl','kubectl'):shutil.copy2(ROOT/'tests/api-oidc-cli.py',self.bin/n);(self.bin/n).chmod(0o700)
  cert=self.d/'ca.crt';key=self.d/'server.key'
  subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','2','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(key),'-out',str(cert)],check=True,capture_output=True)
  owner=self;self.bad_issuer=False
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_GET(self):
    body=json.dumps({'issuer':'https://wrong.fixture.test' if owner.bad_issuer else owner.issuer,'code_challenge_methods_supported':['S256'],'id_token_signing_alg_values_supported':['RS256']}).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.issuer=f'https://localhost:{server.server_port}/auth/realms/perkforge';ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(cert),str(key));server.socket=ctx.wrap_socket(server.socket,server_side=True);threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
  # Only filesystem privilege and service/API transport are synthetic. Actual
  # Ansible ownership/checksum/transaction modules and HTTPS discovery run intact.
  tasks=self.d/'tasks';shutil.copytree(ROOT/'tasks',tasks)
  for p in tasks.glob('api-oidc*.yml'):
   doc=yaml.safe_load(p.read_text())
   def adapt(rows):
    for t in rows:
     if 'async' in t:t.pop('async');t.pop('poll')
     for k in ('block','rescue','always'):
      if k in t:adapt(t[k])
   adapt(doc);p.write_text(yaml.safe_dump(doc,sort_keys=False))
  self.play=self.d/'play.yml';self.play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'tasks':[{'ansible.builtin.include_tasks':str(tasks/'api-oidc.yml')}]}]))
  import pwd,grp,hashlib
  self.v={'api_oidc_root':str(self.root),'api_oidc_user':pwd.getpwuid(os.getuid()).pw_name,'api_oidc_group':grp.getgrgid(os.getgid()).gr_name,'api_oidc_uid':os.getuid(),'api_oidc_host_kubectl':str(self.bin/'kubectl'),'api_oidc_release_commit':'a'*40,'api_oidc_cluster_id':'fixture-cluster','api_oidc_cluster_uid':'fixture-uid','api_oidc_expected_base_sha256':hashlib.sha256(self.base.encode()).hexdigest(),'api_oidc_issuer':self.issuer,'api_oidc_client_id':'headlamp-local','api_oidc_ca_pem':cert.read_text(),'api_oidc_retries':1,'api_oidc_delay':0,'api_oidc_expected_nodes':['control-1']}
  # The production controller fixes the node to control-1; local task fixture uses localhost.
  self.owner_node='localhost'
 def data(self):return json.loads(self.state.read_text())
 def run_play(self,op='apply',extra=None):
  r=subprocess.run(['ansible-playbook',str(self.play),'-e',json.dumps({**self.v,'api_oidc_operation':op,**(extra or {})})],capture_output=True,text=True,timeout=90,env={**os.environ,'PATH':str(self.bin)+':'+os.environ['PATH'],'API_OIDC_FIXTURE':str(self.state),'ANSIBLE_LOCAL_TEMP':str(self.d/'local'),'ANSIBLE_REMOTE_TEMP':str(self.d/'remote')})
  self.assertNotIn('synthetic-private-value',r.stdout+r.stderr);return r
 def ok(self,op='apply',extra=None):
  r=self.run_play(op,extra);self.assertEqual(r.returncode,0,r.stdout+r.stderr);return r
 def test_inspect_apply_repeat_and_rollback_preserve_every_unrelated_byte(self):
  self.ok('inspect');self.assertFalse((self.root/'perkforge-oidc-v1').exists())
  self.ok();self.assertEqual(self.data()['restarts'],1)
  j=self.root/'perkforge-oidc-v1';self.assertEqual(j.stat().st_mode&0o777,0o700)
  self.assertTrue(list(j.glob('*.backup')))
  for f in j.iterdir():self.assertEqual(f.stat().st_mode&0o777,0o600)
  self.assertIn('changed=0',self.ok().stdout);self.assertEqual(self.data()['restarts'],1)
  self.ok('rollback');self.assertEqual(self.data()['restarts'],2)
  self.assertFalse((self.root/'config.yaml.d/90-perkforge-oidc-v1.yaml').exists());self.assertFalse((self.root/'identity/ca.crt').exists())
  self.assertIn('changed=0',self.ok('rollback').stdout);self.assertEqual(self.data()['restarts'],2)
  self.assertEqual((self.root/'config.yaml').read_text(),self.base)
  self.assertEqual((self.root/'config.yaml.d/10-unrelated.yaml').read_text(),'write-kubeconfig-mode: "0600"\n')
  self.assertNotEqual(self.run_play().returncode,0)
 def test_failed_restart_keeps_owned_recovery_and_rollback_works_without_initial_api(self):
  s=self.data();s['fail_restart']=True;self.state.write_text(json.dumps(s));r=self.run_play();self.assertNotEqual(r.returncode,0)
  self.assertFalse(self.data()['ready']);self.assertEqual(json.loads((self.root/'perkforge-oidc-v1/owner.json').read_text())['phase'],'prepared')
  self.ok('rollback');self.assertTrue(self.data()['ready']);self.assertEqual(self.data()['restarts'],2)
 def test_interrupted_rollback_resumes_without_api_or_ca_input(self):
  self.ok();s=self.data();s['fail_restart']=True;self.state.write_text(json.dumps(s))
  self.assertNotEqual(self.run_play('rollback',{'api_oidc_ca_pem':''}).returncode,0)
  self.assertFalse(self.data()['ready']);self.assertEqual(json.loads((self.root/'perkforge-oidc-v1/owner.json').read_text())['phase'],'rollback-pending')
  self.ok('rollback',{'api_oidc_ca_pem':''});self.assertEqual(self.data()['restarts'],3);self.assertIn('changed=0',self.ok('rollback').stdout)
 def test_missing_owned_file_partial_prepare_resumes_but_active_drift_refuses(self):
  s=self.data();s['fail_restart']=True;self.state.write_text(json.dumps(s));self.assertNotEqual(self.run_play().returncode,0)
  # Synthetic interruption before service transition: original API remains available.
  s=self.data();s['ready']=True;self.state.write_text(json.dumps(s));(self.root/'config.yaml.d/90-perkforge-oidc-v1.yaml').unlink()
  self.ok();self.assertEqual(self.data()['restarts'],2)
  (self.root/'config.yaml.d/10-unrelated.yaml').write_text('write-kubeconfig-mode: "0644"\n');n=self.data()['restarts'];self.assertNotEqual(self.run_play('rollback').returncode,0);self.assertEqual(self.data()['restarts'],n)
 def test_discovery_mismatch_leaves_only_owned_ca_and_resumes_safely(self):
  self.bad_issuer=True;self.assertNotEqual(self.run_play().returncode,0)
  self.assertTrue((self.root/'identity/ca.crt').exists());self.assertFalse((self.root/'config.yaml.d/90-perkforge-oidc-v1.yaml').exists());self.assertNotIn('restarts',self.data())
  self.bad_issuer=False;self.ok();self.assertEqual(self.data()['restarts'],1)
 def test_conflicting_auth_foreign_file_wrong_uid_and_symlinks_refuse_before_restart(self):
  original=(self.root/'config.yaml.d/10-unrelated.yaml').read_text()
  self.envfile.write_text('RKE2_CONFIG_FILE=/foreign/config.yaml\n');self.assertNotEqual(self.run_play().returncode,0);self.assertNotIn('restarts',self.data());self.envfile.write_text('RKE2_KUBECONFIG_MODE=0600\n')
  for bad in ('kube-apiserver-arg+: [oidc-client-id=other]\n','kube-apiserver-arg: [authentication-config=/foreign]\n'):
   (self.root/'config.yaml.d/10-unrelated.yaml').write_text(bad);self.assertNotEqual(self.run_play().returncode,0);self.assertNotIn('restarts',self.data())
  (self.root/'config.yaml.d/10-unrelated.yaml').write_text(original)
  self.assertNotEqual(self.run_play(extra={'api_oidc_cluster_uid':'wrong'}).returncode,0)
  ca=self.root/'identity';ca.mkdir();(ca/'ca.crt').write_text('FOREIGN');self.assertNotEqual(self.run_play().returncode,0);self.assertEqual((ca/'ca.crt').read_text(),'FOREIGN')
  (ca/'ca.crt').unlink();(ca/'ca.crt').symlink_to(self.root/'config.yaml');self.assertNotEqual(self.run_play().returncode,0);self.assertNotIn('restarts',self.data())

if __name__=='__main__':unittest.main()
