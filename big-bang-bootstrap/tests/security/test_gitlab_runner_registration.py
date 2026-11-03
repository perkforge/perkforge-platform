"""One-time runner token custody and lifecycle against synthetic HTTPS only."""
import base64,hashlib,json,os,shutil,ssl,subprocess,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[2]
class RunnerAPI(unittest.TestCase):
 def test_paused_create_uncertain_response_repeat_activation_and_drain(self):
  with tempfile.TemporaryDirectory(prefix='gitlab-runner-fixture-') as directory:
   p=Path(directory);private=p/'private';private.mkdir(mode=0o700)
   subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(p/'key'),'-out',str(p/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   s={'runner':None,'creates':0,'pauseWrites':0,'failCreate':True,'running':0,'ticks':0}
   class H(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def respond(self,code,value=None):
     self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers()
     if value is not None:self.wfile.write(json.dumps(value).encode())
    def do_GET(self):
     if self.headers.get('PRIVATE-TOKEN')!='OFFLINE-RUNNER-API-TOKEN':return self.respond(403,{})
     path=urlsplit(self.path).path
     if path=='/api/v4/version':return self.respond(200,{'version':'19.4.2-ee'})
     if path=='/api/v4/user':return self.respond(200,{'id':21})
     if path=='/api/v4/projects/31':return self.respond(200,{'id':31,'path_with_namespace':'platform/acceptance','visibility':'private','default_branch':'main'})
     if path=='/api/v4/projects/31/protected_branches/main':return self.respond(200,{'name':'main','allow_force_push':False,'push_access_levels':[{'access_level':40}]})
     if path=='/api/v4/projects/31/runners':return self.respond(200,[{'id':7,'description':s['runner']['description']}] if s['runner'] else [])
     if path=='/api/v4/runners/7/jobs':return self.respond(200,[{'id':1}] if s['running'] else [])
     if path=='/api/v4/runners/7' and s['runner']:
      s['ticks']+=1;return self.respond(200,{**s['runner'],'contacted_at':str(s['ticks'])})
     return self.respond(404,{})
    def do_POST(self):
     if self.headers.get('PRIVATE-TOKEN')!='OFFLINE-RUNNER-API-TOKEN':return self.respond(403,{})
     assert self.path=='/api/v4/user/runners';body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
     assert body['runner_type']=='project_type' and body['project_id']==31 and body['paused'] is True and body['locked'] is True and body['run_untagged'] is False
     assert body['access_level']=='ref_protected' and body['tag_list']=='perkforge-platform' and body['maximum_timeout']==300
     assert s['runner'] is None;s['creates']+=1;s['runner']={k:v for k,v in body.items() if k!='project_id'};s['runner'].update(id=7,tag_list=['perkforge-platform'],projects=[{'id':31}])
     return self.respond(503,{}) if s['failCreate'] else self.respond(201,{'id':7,'token':'glrt-OFFLINE_AUTH_TOKEN','token_expires_at':None})
    def do_PUT(self):
     assert self.headers.get('PRIVATE-TOKEN')=='OFFLINE-RUNNER-API-TOKEN' and self.path=='/api/v4/runners/7'
     body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));assert set(body)=={'paused'};s['runner']['paused']=body['paused'];s['pauseWrites']+=1;return self.respond(200,s['runner'])
   server=ThreadingHTTPServer(('127.0.0.1',0),H);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(p/'ca',p/'key');server.socket=ctx.wrap_socket(server.socket,server_side=True);self.addCleanup(server.server_close)
   # Bootstrap integration: app credentials exist BEFORE the GitLab API is started.
   output=p/'output';output.mkdir(mode=0o700);kube=p/'kube';kube.write_text('not a kubeconfig');kube.chmod(0o600)
   kubectl=p/'kubectl';shutil.copy2(ROOT/'tests/fixtures/gitlab_delivery_cli.py',kubectl);kubectl.chmod(0o700)
   cluster_state=p/'cluster';cluster_state.write_text(json.dumps({'api':'https://synthetic.invalid:6443','uid':'synthetic-cluster-uid','objects':{}}))
   package_env={**os.environ,'GITLAB_DELIVERY_TEST_STATE':str(cluster_state),'ANSIBLE_LOCAL_TEMP':str(p/'assembly-local'),'ANSIBLE_REMOTE_TEMP':str(p/'assembly-remote')}
   def package(play,variables):
    vf=p/'package-vars';vf.write_text(json.dumps(variables));vf.chmod(0o600)
    r=subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'configuration/packages/gitlab'/play),'-e','@'+str(vf)],env=package_env,capture_output=True,text=True,timeout=60)
    for secret in ('OFFLINE-APPLICATION-INPUT-123456','glrt-OFFLINE_AUTH_TOKEN'):self.assertNotIn(secret,r.stdout+r.stderr)
    return r
   app={'gitlab_credentials_run':True,'gitlab_credentials_profile':'application','gitlab_credentials_scope':'gitlab-application-private-assembly-v1','gitlab_credentials_output_dir':str(output),'gitlab_origin':'https://localhost:'+str(server.server_port),'gitlab_issuer':'https://identity.fixture.invalid/auth/realms/perkforge'}
   for name in ('database_password','valkey_password','client_secret'):
    path=p/name;path.write_text('OFFLINE-APPLICATION-INPUT-123456');path.chmod(0o600);app['gitlab_'+name+'_file']=str(path)
   self.assertFalse((private/'runner-token').exists());r=package('prepare-credentials.yaml',app);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   base_delivery={'gitlab_delivery_run':True,'gitlab_kubectl':str(kubectl),'gitlab_kubeconfig':str(kube),'gitlab_context':'synthetic','gitlab_expected_api':'https://synthetic.invalid:6443','gitlab_expected_cluster_uid':'synthetic-cluster-uid'}
   r=package('deliver-credentials.yaml',{**base_delivery,'gitlab_delivery_profile':'application','gitlab_delivery_scope':'gitlab-application-credential-delivery-v1','gitlab_credentials_manifest':str(output/'application-credentials.json')});self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   self.assertEqual(set(json.loads(cluster_state.read_text())['objects']),{'gitlab/gitlab-database','gitlab/gitlab-valkey-acl','gitlab/gitlab-redis','gitlab/gitlab-oidc-provider'})
   application_bytes=(output/'application-credentials.json').read_bytes()
   runner_input={'gitlab_credentials_run':True,'gitlab_credentials_profile':'runner','gitlab_credentials_scope':'gitlab-runner-private-assembly-v1','gitlab_credentials_output_dir':str(output),'gitlab_runner_token_file':str(private/'runner-token')}
   self.assertNotEqual(package('prepare-credentials.yaml',runner_input).returncode,0);self.assertFalse((output/'runner-credentials.json').exists());self.assertEqual(s['creates'],0)
   threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.shutdown)
   token=p/'api-token';token.write_text('OFFLINE-RUNNER-API-TOKEN');token.chmod(0o600)
   v={'gitlab_runner_run':True,'gitlab_runner_recovery_verified':True,'gitlab_runner_manager_verified':True,'gitlab_runner_origin':'https://localhost:'+str(server.server_port),'gitlab_runner_ca_file':str(p/'ca'),'gitlab_runner_api_token_file':str(token),'gitlab_runner_private_directory':str(private),'gitlab_runner_actor_id':21,'gitlab_runner_project_id':31,'gitlab_runner_project_path':'platform/acceptance'}
   def run(operation='prepare',extra=None,check=False):
    vf=p/'vars';vf.write_text(json.dumps({**v,'gitlab_runner_operation':operation,'gitlab_runner_scope':'gitlab-runner-'+operation+'-v1',**(extra or {})}));vf.chmod(0o600)
    r=subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'configuration/packages/gitlab-runner/reconcile-registration.yaml'),'-e','@'+str(vf)]+(['--check'] if check else []),env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(p/'local'),'ANSIBLE_REMOTE_TEMP':str(p/'remote')},capture_output=True,text=True,timeout=90)
    for secret in ('OFFLINE-RUNNER-API-TOKEN','glrt-OFFLINE_AUTH_TOKEN'):self.assertNotIn(secret,r.stdout+r.stderr)
    return r
   def ok(*a,**kw):
    r=run(*a,**kw);self.assertEqual(r.returncode,0,r.stdout+r.stderr);return r
   ok(check=True);self.assertEqual(s['creates'],0)
   self.assertNotEqual(run().returncode,0);self.assertEqual(s['creates'],1);self.assertEqual(json.loads((private/'runner-receipt.json').read_text())['phase'],'creation-pending')
   self.assertNotEqual(run().returncode,0);self.assertEqual(s['creates'],1)
   # Reset only disposable fixture state to model separate, reviewed orphan recovery.
   (private/'runner-receipt.json').unlink();s['runner']=None;s['failCreate']=False
   ok();self.assertTrue(s['runner']['paused']);self.assertEqual((private/'runner-token').stat().st_mode&0o777,0o600);self.assertEqual((private/'runner-receipt.json').stat().st_mode&0o777,0o600)
   # Handoff the ACTUAL registration output to the later, independent secret stage.
   r=package('prepare-credentials.yaml',runner_input);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   self.assertEqual((output/'application-credentials.json').read_bytes(),application_bytes)
   runner_manifest=output/'runner-credentials.json';self.assertEqual(len(json.loads(runner_manifest.read_text())['items']),1)
   before_cluster=cluster_state.read_bytes();wrong=package('deliver-credentials.yaml',{**base_delivery,'gitlab_delivery_profile':'application','gitlab_delivery_scope':'gitlab-application-credential-delivery-v1','gitlab_credentials_manifest':str(runner_manifest)});self.assertNotEqual(wrong.returncode,0);self.assertEqual(cluster_state.read_bytes(),before_cluster)
   r=package('deliver-credentials.yaml',{**base_delivery,'gitlab_delivery_profile':'runner','gitlab_delivery_scope':'gitlab-runner-credential-delivery-v1','gitlab_credentials_manifest':str(runner_manifest)});self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   secret=json.loads(cluster_state.read_text())['objects']['gitlab-runner/gitlab-runner-auth'];self.assertEqual(base64.b64decode(secret['data']['runner-token']).decode(),(private/'runner-token').read_text());self.assertTrue(secret['immutable'])
   ca_delivery={'gitlab_ca_run':True,'gitlab_ca_stage':'runner','gitlab_ca_scope':'gitlab-ca-runner-v1','gitlab_ca_file':str(p/'ca'),'gitlab_ca_file_sha256':hashlib.sha256((p/'ca').read_bytes()).hexdigest(),'gitlab_origin':v['gitlab_runner_origin'],**{key:value for key,value in base_delivery.items() if key not in ('gitlab_delivery_run',)}}
   r=package('deliver-public-ca.yaml',ca_delivery);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   # Match the delivered object and hostname filename against the PINNED deployment.
   from fixtures.render_helpers import build,helm,ordered_values,child_values
   sources=Path(os.environ['PREFLIGHT_SOURCES_DIR']);root_objects=build(ROOT/'clusters/local-gitlab-runner');parent=next(x for x in root_objects if x['kind']=='HelmRelease' and x['metadata']['name']=='bigbang')
   extra=json.dumps({'addons':{'gitlabRunner':{'values':{'upstream':{'gitlabUrl':v['gitlab_runner_origin']}}}}})
   outer=helm(sources/'bigbang/chart','bigbang','bigbang',ordered_values(root_objects,parent)+[extra]);rendered=helm(sources/'gitlab-runner/chart','gitlab-runner','gitlab-runner',child_values(outer,'gitlab-runner'));deployment=next(x for x in rendered if x['kind']=='Deployment')
   ca_ref=next(volume['secret'] for volume in deployment['spec']['template']['spec']['volumes'] if volume.get('secret',{}).get('secretName')=='gitlab-runner-public-ca');self.assertFalse(ca_ref.get('optional',False))
   ca_secret=json.loads(cluster_state.read_text())['objects'][deployment['metadata']['namespace']+'/'+ca_ref['secretName']];self.assertEqual(set(ca_secret['data']),{'localhost.crt'});self.assertEqual(base64.b64decode(ca_secret['data']['localhost.crt']).decode(),(p/'ca').read_text().strip());self.assertTrue(ca_secret['immutable'])
   r=package('deliver-public-ca.yaml',ca_delivery);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout)
   before=s['creates'];self.assertIn('changed=0',ok().stdout);self.assertEqual(s['creates'],before)
   self.assertNotEqual(run('activate',{'gitlab_runner_manager_verified':False}).returncode,0);self.assertEqual(s['pauseWrites'],0)
   ok('activate');self.assertFalse(s['runner']['paused']);s['running']=1;self.assertNotEqual(run('pause').returncode,0);self.assertTrue(s['runner']['paused']);s['running']=0;self.assertIn('changed=0',ok('pause').stdout)
   s['runner']['locked']=False;before=s['pauseWrites'];self.assertNotEqual(run('activate').returncode,0);self.assertEqual(s['pauseWrites'],before)
   self.assertEqual((private/'runner-token').read_text(),'glrt-OFFLINE_AUTH_TOKEN');self.assertFalse((private/'.registration-lock').exists())
