from pathlib import Path
import copy,importlib.util,sys,unittest
ROOT=Path(__file__).resolve().parents[2];directory=ROOT/'tests/fixtures'
sys.path.insert(0,str(directory))
from garage_model import reconcile
from garage_plan import TAG,PERMISSIONS
class FakeAPI:
 def __init__(self):
  self.node='a'*64;self.status={'layoutVersion':0,'nodes':[{'id':self.node,'isUp':True,'draining':False,'garageVersion':'v2.2.0','dataPartition':{'available':31*1024**3,'total':31*1024**3}}]};self.layout={'version':0,'roles':[],'parameters':{'zoneRedundancy':'maximum'},'partitionSize':0,'stagedRoleChanges':[],'stagedParameters':None};self.keys=[];self.buckets={};self.calls=[];self.fail=None;self.read_fail=None
 def __call__(self,name,body=None):
  self.calls.append((name,copy.deepcopy(body)))
  if name==self.read_fail:raise RuntimeError('synthetic ready-layout read failure')
  if name in ('ListKeys','ListBuckets') and self.layout['version']==0:raise RuntimeError('Internal error: Layout not ready')
  if name=='GetClusterStatus':result=self.status
  elif name=='GetClusterLayout':result=self.layout
  elif name=='ListKeys':result=[{'id':k['accessKeyId'],'name':k['name']} for k in self.keys]
  elif name=='ListBuckets':result=[{'id':k,'globalAliases':v['globalAliases']} for k,v in self.buckets.items()]
  elif name.startswith('GetKeyInfo?'):result=self.keys[0]
  elif name.startswith('GetBucketInfo?'):result=self.buckets[name.split('id=')[1]]
  elif name=='UpdateClusterLayout':self.layout['stagedRoleChanges']=body['roles'];result={}
  elif name=='PreviewClusterLayoutChanges':result={'newLayout':{**self.layout,'version':1,'roles':self.layout['stagedRoleChanges'],'stagedRoleChanges':[]},'message':[]}
  elif name=='ApplyClusterLayout':self.layout.update(version=1,roles=self.layout['stagedRoleChanges'],stagedRoleChanges=[]);self.status['layoutVersion']=1;result={}
  elif name=='ImportKey':self.keys=[{'accessKeyId':body['accessKeyId'],'name':body['name'],'expired':False,'permissions':{'createBucket':False},'buckets':[]}];result={}
  elif name=='CreateBucket':
   bucket_id=hex(len(self.buckets)+1)[2:].zfill(64);result={'id':bucket_id,'globalAliases':[body['globalAlias']],'websiteAccess':False,'keys':[]};self.buckets[bucket_id]=result
  elif name=='AllowBucketKey':
   bucket=self.buckets[body['bucketId']];bucket['keys']=[{'accessKeyId':body['accessKeyId'],'name':TAG,'bucketLocalAliases':[],'permissions':body['permissions']}];self.keys[0]['buckets'].append({'id':body['bucketId'],'globalAliases':bucket['globalAliases'],'localAliases':[],'permissions':body['permissions']});result={}
  else:raise ValueError('unexpected API request')
  if self.fail==name:raise TimeoutError('synthetic response lost after mutation')
  return copy.deepcopy(result)
class Bootstrap(unittest.TestCase):
 def test_complete_bootstrap_and_zero_change_repeat(self):
  api=FakeAPI();receipt={};saved=[]
  save=lambda value:saved.append(copy.deepcopy(value))
  result=reconcile(api,receipt,save,api.node,'GK'+'b'*24,'c'*64,True)
  self.assertTrue(result['ready']);self.assertEqual(result['changed'],15);self.assertIsNone(receipt['pending']);self.assertEqual(len(receipt['buckets']),6)
  names=[name for name,body in api.calls];self.assertLess(names.index('ApplyClusterLayout'),names.index('ListKeys'));self.assertLess(names.index('ApplyClusterLayout'),names.index('ListBuckets'))
  self.assertEqual(reconcile(api,receipt,save,api.node,'GK'+'b'*24,'c'*64)['changed'],0)
  self.assertFalse(any('Delete' in name or 'UpdateKey' in name for name,body in api.calls))
  self.assertTrue(all('secretAccessKey' not in str(value) for value in saved))
 def test_uncertain_create_blocks_retry_and_preserves_intent(self):
  api=FakeAPI();api.fail='CreateBucket';receipt={};saved=[];save=lambda value:saved.append(copy.deepcopy(value))
  with self.assertRaises(TimeoutError):reconcile(api,receipt,save,api.node,'GK'+'b'*24,'c'*64,True)
  self.assertEqual(saved[-1]['pending']['operation'],'CreateBucket');before=len(api.calls)
  with self.assertRaises(ValueError):reconcile(api,receipt,save,api.node,'GK'+'b'*24,'c'*64,True)
  self.assertEqual(len(api.calls),before);self.assertEqual(len(api.buckets),1)
 def test_uncertain_layout_mutations_keep_intent_and_block_retry(self):
  for action in ('UpdateClusterLayout','ApplyClusterLayout'):
   api=FakeAPI();api.fail=action;receipt={};saved=[];save=lambda value:saved.append(copy.deepcopy(value))
   with self.subTest(action=action),self.assertRaises(TimeoutError):reconcile(api,receipt,save,api.node,'GK'+'b'*24,'c'*64,True)
   self.assertEqual(saved[-1]['pending']['operation'],action);before=len(api.calls)
   with self.assertRaises(ValueError):reconcile(api,receipt,save,api.node,'GK'+'b'*24,'c'*64,True)
   self.assertEqual(len(api.calls),before);self.assertEqual(api.keys,[])
 def test_owned_staged_layout_resumes_after_read_only_preview_failure(self):
  api=FakeAPI();api.fail='PreviewClusterLayoutChanges';receipt={};saved=[];save=lambda value:saved.append(copy.deepcopy(value))
  with self.assertRaises(TimeoutError):reconcile(api,receipt,save,api.node,'GK'+'b'*24,'c'*64,True)
  self.assertIsNone(receipt['pending']);self.assertEqual(api.layout['version'],0);self.assertEqual(len(api.layout['stagedRoleChanges']),1)
  api.fail=None;result=reconcile(api,receipt,save,api.node,'GK'+'b'*24,'c'*64,True)
  self.assertTrue(result['ready']);self.assertEqual(result['changed'],14);self.assertEqual(len(receipt['buckets']),6)
 def test_without_first_layout_approval_no_remote_write(self):
  api=FakeAPI()
  with self.assertRaises(ValueError):reconcile(api,{},lambda value:None,api.node,'GK'+'b'*24,'c'*64)
  self.assertFalse(any(body is not None for name,body in api.calls))
 def test_foreign_key_is_not_adopted_or_modified(self):
  api=FakeAPI();receipt={};reconcile(api,receipt,lambda value:None,api.node,'GK'+'b'*24,'c'*64,True)
  api.keys=[{'accessKeyId':'GK'+'d'*24,'name':'foreign'}];before=len(api.calls)
  with self.assertRaises(ValueError):reconcile(api,receipt,lambda value:None,api.node,'GK'+'b'*24,'c'*64,True)
  self.assertFalse(any(body is not None for name,body in api.calls[before:]))
 def test_unreceipted_ready_or_staged_layout_is_not_adopted(self):
  for phase in ('staged','ready'):
   api=FakeAPI();role={'id':api.node,'zone':'gitlab-local','capacity':28*1024**3,'tags':[TAG]}
   if phase=='staged':api.layout['stagedRoleChanges']=[role]
   else:api.layout.update(version=1,roles=[role]);api.status['layoutVersion']=1
   with self.subTest(phase=phase),self.assertRaises(ValueError):reconcile(api,{},lambda value:None,api.node,'GK'+'b'*24,'c'*64,True)
   self.assertFalse(any(body is not None for name,body in api.calls))
 def test_cli_private_receipts_and_repeat_with_loopback_fixture(self):
  import json,os,subprocess,tempfile,threading
  from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
  api=FakeAPI()
  class H(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_GET(self):self.reply()
   def do_POST(self):self.reply()
   def reply(self):
    if self.headers.get('Authorization')!='Bearer offline-admin-token':self.send_error(403);return
    body=json.loads(self.rfile.read(int(self.headers['Content-Length']))) if self.command=='POST' else None
    try:result=api(self.path.removeprefix('/v2/'),body)
    except TimeoutError:self.send_error(503);return
    except RuntimeError as error:
     data=json.dumps({'code':'InternalError','message':str(error),'region':'garage','path':self.path}).encode();self.send_response(500);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
    data=json.dumps(result).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
  server=ThreadingHTTPServer(('127.0.0.1',0),H);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with tempfile.TemporaryDirectory(prefix='garage-cli-fixture-') as directory:
    p=Path(directory);state=p/'state';state.mkdir(mode=0o700)
    for name,value in [('admin','offline-admin-token'),('key-id','GK'+'b'*24),('key-secret','c'*64)]:
     path=p/name;path.write_text(value);path.chmod(0o600)
    v={'gitlab_garage_run':True,'gitlab_garage_scope':'gitlab-garage-init-v1','gitlab_garage_url':f'http://127.0.0.1:{server.server_port}','gitlab_garage_node':api.node,'gitlab_garage_state_directory':str(state),'gitlab_garage_admin_file':str(p/'admin'),'gitlab_garage_key_id_file':str(p/'key-id'),'gitlab_garage_key_secret_file':str(p/'key-secret'),'gitlab_garage_allow_first_layout':True}
    vf=p/'vars.json';vf.write_text(json.dumps(v));vf.chmod(0o600)
    command=['ansible-playbook','-i','localhost,',str(ROOT/'configuration/packages/gitlab/reconcile-garage.yaml'),'-e','@'+str(vf)]
    env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(p/'local'),'ANSIBLE_REMOTE_TEMP':str(p/'remote')}
    first=subprocess.run(command,capture_output=True,text=True,timeout=180,env=env);self.assertEqual(first.returncode,0,first.stderr);self.assertIn('\"ready\": true',first.stdout)
    names=[name for name,body in api.calls];self.assertLess(names.index('ApplyClusterLayout'),names.index('ListKeys'));self.assertLess(names.index('ApplyClusterLayout'),names.index('ListBuckets'))
    path=state/'garage-bootstrap.json';self.assertEqual(path.stat().st_mode&0o777,0o600);receipt=json.loads(path.read_text());self.assertIsNone(receipt['pending'])
    second=subprocess.run(command,capture_output=True,text=True,timeout=180,env=env);self.assertEqual(second.returncode,0,second.stderr);self.assertIn('changed=0',second.stdout)
    for secret in ('offline-admin-token','c'*64):self.assertNotIn(secret,first.stdout+first.stderr+second.stdout+second.stderr+path.read_text())
    self.assertFalse((state/'garage-bootstrap.lock').exists())
    # A post-layout HTTP500 remains fatal; it is never treated as an empty store.
    api.read_fail='ListKeys';before=len(api.calls)
    failed_read=subprocess.run(command,capture_output=True,text=True,timeout=30,env=env);self.assertNotEqual(failed_read.returncode,0)
    self.assertFalse(any(body is not None for name,body in api.calls[before:]));self.assertIsNone(json.loads(path.read_text())['pending']);api.read_fail=None
    # Even exact matching staged/ready layouts need prior durable ownership.
    for phase in ('staged','ready'):
     api=FakeAPI();role={'id':api.node,'zone':'gitlab-local','capacity':28*1024**3,'tags':[TAG]}
     if phase=='staged':api.layout['stagedRoleChanges']=[role]
     else:api.layout.update(version=1,roles=[role]);api.status['layoutVersion']=1
     foreign_state=p/('foreign-'+phase);foreign_state.mkdir(mode=0o700);v['gitlab_garage_state_directory']=str(foreign_state);vf.write_text(json.dumps(v))
     refusal=subprocess.run(command,capture_output=True,text=True,timeout=30,env=env);self.assertNotEqual(refusal.returncode,0)
     self.assertFalse(any(body is not None for name,body in api.calls));self.assertFalse((foreign_state/'garage-bootstrap.json').exists());self.assertFalse((foreign_state/'garage-bootstrap.lock').exists())
    # Actual Ansible, not only the independent model: uncertain create blocks retry.
    api=FakeAPI();api.fail='CreateBucket';failed_state=p/'failed-state';failed_state.mkdir(mode=0o700)
    v['gitlab_garage_state_directory']=str(failed_state);vf.write_text(json.dumps(v))
    failed=subprocess.run(command,capture_output=True,text=True,timeout=180,env=env);self.assertNotEqual(failed.returncode,0)
    pending=json.loads((failed_state/'garage-bootstrap.json').read_text());self.assertEqual(pending['pending']['operation'],'CreateBucket');self.assertEqual(len(api.buckets),1)
    before=len(api.calls);retry=subprocess.run(command,capture_output=True,text=True,timeout=30,env=env);self.assertNotEqual(retry.returncode,0);self.assertEqual(len(api.calls),before)
    self.assertFalse((failed_state/'garage-bootstrap.lock').exists())

  finally:server.shutdown();server.server_close();thread.join(timeout=2)
