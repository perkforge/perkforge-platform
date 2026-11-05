"""Actual Ansible route reconciliation and trusted loopback HTTPS, never a cluster."""
import copy,hashlib,json,os,shutil,ssl,subprocess,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
PLAY=ROOT/'configuration/authorization/sso/reconcile-headlamp-routing.yaml'

@unittest.skipUnless(os.environ.get('RUN_PLATFORM_SSO_TESTS'),'isolated SSO fixture job')
class HeadlampRouting(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.d=Path(self.t.name)
  self.cert=self.d/'ca.crt';key=self.d/'key.pem'
  subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','2','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(key),'-out',str(self.cert)],check=True,capture_output=True)
  self.http_status=200;owner=self
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_GET(self):self.send_response(owner.http_status);self.end_headers();self.wfile.write(b'fixture')
  srv=ThreadingHTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(self.cert),str(key));srv.socket=ctx.wrap_socket(srv.socket,server_side=True)
  threading.Thread(target=srv.serve_forever,daemon=True).start();self.addCleanup(srv.server_close);self.addCleanup(srv.shutdown)
  self.origin=f'https://localhost:{srv.server_port}'
  fp=subprocess.check_output(['openssl','x509','-in',str(self.cert),'-fingerprint','-sha256','-noout'],text=True).strip().split('=')[-1].replace(':','').lower()
  self.cli=self.d/'kubectl';shutil.copy2(ROOT/'tests/fixtures/headlamp-route-cli.py',self.cli);self.cli.chmod(0o700)
  self.state=self.d/'state.json';self.other={'kind':'Ingress','metadata':{'name':'keycloak-identity'},'spec':{'preserve':'unchanged'}};self.state.write_text(json.dumps({'objects':{'keycloak-identity':self.other},'certificate':self.cert.read_text()}))
  self.owner={'platform.perkforge.io/https-owner':'headlamp-v1'};self.candidate=yaml.safe_load((ROOT/'configuration/identity/routing/headlamp.yaml').read_text());self.candidate['metadata']['labels']=self.owner;self.candidate['spec']['tls'][0]['hosts']=['localhost'];self.candidate['spec']['rules'][0]['host']='localhost'
  doc=yaml.safe_load((ROOT/'configuration/authorization/sso/tasks/headlamp-routing.yaml').read_text())
  def short(rows):
   for t in rows:
    if 'retries' in t:t['retries']=1;t['delay']=0
    for k in ('block','rescue','always'):
     if k in t:short(t[k])
  short(doc);tasks=self.d/'tasks.yaml';tasks.write_text(yaml.safe_dump(doc,sort_keys=False));self.play=self.d/'play.yaml';self.play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'tasks':[{'ansible.builtin.include_tasks':str(tasks)}]}]))
  self.v={'headlamp_route_cli':[str(self.cli)],'headlamp_route_cluster_uid':'fixture-uid','headlamp_route_origin':self.origin,'headlamp_route_owner':self.owner,'headlamp_route_candidate':self.candidate,'headlamp_route_public_ca':str(self.cert),'headlamp_route_ca_fingerprint':fp}
 def data(self):return json.loads(self.state.read_text())
 def run_play(self,op='apply',extra=None):
  r=subprocess.run(['ansible-playbook',str(self.play),'-e',json.dumps({**self.v,'headlamp_route_operation':op,**(extra or {})})],capture_output=True,text=True,timeout=45,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(self.d/'local'),'ANSIBLE_REMOTE_TEMP':str(self.d/'remote'),'HEADLAMP_ROUTE_FIXTURE':str(self.state)})
  self.assertEqual(self.data()['objects']['keycloak-identity'],self.other);return r
 def ok(self,op='apply',extra=None):
  r=self.run_play(op,extra);self.assertEqual(r.returncode,0,r.stdout+r.stderr);return r
 def test_create_repeat_inspect_and_uid_checked_rollback_isolate_headlamp(self):
  self.ok();self.assertEqual(self.data()['writes'],['create']);self.assertIn('changed=0',self.ok().stdout);self.assertIn('changed=0',self.ok('inspect').stdout)
  self.ok('rollback');self.assertEqual(self.data()['writes'],['create','delete']);self.assertIn('changed=0',self.ok('rollback').stdout)
 def test_partial_https_failure_preserves_owned_route_and_retry_does_not_duplicate(self):
  self.http_status=503;self.assertNotEqual(self.run_play().returncode,0);self.assertEqual(self.data()['writes'],['create'])
  self.http_status=200;self.ok();self.assertEqual(self.data()['writes'],['create'])
 def test_foreign_or_wrong_cluster_and_wrong_ca_never_create(self):
  self.assertNotEqual(self.run_play(extra={'headlamp_route_cluster_uid':'wrong'}).returncode,0)
  self.assertNotEqual(self.run_play(extra={'headlamp_route_ca_fingerprint':'0'*64}).returncode,0)
  s=self.data();s['objects']['headlamp-identity']=copy.deepcopy(self.candidate);s['objects']['headlamp-identity']['metadata']['labels']={'foreign':'true'};self.state.write_text(json.dumps(s));self.assertNotEqual(self.run_play().returncode,0);self.assertNotIn('writes',self.data())
 def test_wrong_certificate_hostname_refuses_and_rollback_conflict_does_not_retry(self):
  bad=copy.deepcopy(self.candidate);bad['spec']['tls'][0]['hosts']=['wrong.fixture.test'];bad['spec']['rules'][0]['host']='wrong.fixture.test'
  self.assertNotEqual(self.run_play(extra={'headlamp_route_origin':'https://wrong.fixture.test','headlamp_route_candidate':bad}).returncode,0);self.assertNotIn('writes',self.data())
  self.ok();s=self.data();s['deleteConflict']=True;self.state.write_text(json.dumps(s));self.assertNotEqual(self.run_play('rollback').returncode,0);self.assertEqual(self.data()['writes'],['create'])
 def test_default_check_and_unreviewed_entrypoint_have_no_api_calls(self):
  for args,rc in (([],0),(['--check','-e','headlamp_route_run=true'],0),(['-e','headlamp_route_run=true'],2)):
   r=subprocess.run(['ansible-playbook',str(PLAY),*args],capture_output=True,text=True,timeout=20,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(self.d/'local'),'ANSIBLE_REMOTE_TEMP':str(self.d/'remote')});self.assertEqual(r.returncode,rc,r.stdout+r.stderr)
  self.assertNotIn('events',self.data())

if __name__=='__main__':unittest.main()

class HeadlampPrerequisiteContract(unittest.TestCase):
 def test_rendered_api_contract_matches_host_maintenance_and_callback_routing(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);host=yaml.safe_load((ROOT.parent/'infrastructure/ansible/tasks/api-oidc.yml').read_text())[0]
   template=ROOT/'configuration/authorization/sso/templates/headlamp.yaml.j2';out=d/'headlamp.yaml'
   values={'api_oidc_root':'/etc/rancher/rke2','api_oidc_host_kubectl':'/fixture/kubectl','api_oidc_issuer':'https://identity.fixture.test/auth/realms/perkforge','api_oidc_client_id':'headlamp-local','sso_keycloak_origin':'https://identity.fixture.test','sso_keycloak_path':'/auth','sso_realm':'perkforge','sso_apps':{'headlamp':{'client_id':'headlamp-local','origin':'https://headlamp.fixture.test'}},'sso_public_ca_file':'/fixture/public-ca.crt','sso_headlamp_apiserver_ca_path':'/etc/rancher/rke2/identity/ca.crt'}
   play=d/'play.yaml';args=d/'args.json';play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'vars':values,'tasks':[host,{'ansible.builtin.copy':{'content':"{{ lookup('template','"+str(template)+"') }}",'dest':str(out)}},{'ansible.builtin.copy':{'content':'{{ api_oidc_args | to_json }}','dest':str(args)}}]}]))
   r=subprocess.run(['ansible-playbook',str(play)],capture_output=True,text=True,timeout=20,env={**os.environ,'ANSIBLE_LOCAL_TEMP':td+'/local','ANSIBLE_REMOTE_TEMP':td+'/remote'});self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   contract=yaml.safe_load(out.read_text())
   actual=json.loads(args.read_text());self.assertEqual(contract['provisioning_fragment']['kube-apiserver-arg+'],actual)
   self.assertNotIn('kube-apiserver-extra-mount+',contract['provisioning_fragment'])
   route=yaml.safe_load((ROOT/'configuration/identity/routing/headlamp.yaml').read_text());self.assertEqual(route['spec']['rules'][0]['http']['paths'][0]['backend']['service'],{'name':'headlamp-headlamp','port':{'number':4466}})
   self.assertEqual(route['spec']['tls'][0]['secretName'],'headlamp-local-tls')
   self.assertEqual(contract['gitops_values']['addons']['headlamp']['values']['upstream']['config']['oidc']['externalSecret']['name'],'perkforge-headlamp-sso-v1')
