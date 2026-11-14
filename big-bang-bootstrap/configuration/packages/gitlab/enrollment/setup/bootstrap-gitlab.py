#!/usr/bin/env python3
"""One-shot native bootstrap coordinator. Default inert; no root-token fallback."""
import argparse,base64,datetime as dt,fcntl,hashlib,json,os,re,ssl,stat,subprocess,sys,tempfile,urllib.error,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phases.contract import read,safe
HERE=Path(__file__).resolve().parent
POLICY='tenant-identity-bootstrap-gitlab-v1'
RECORDS={'reader':'identity/gitlab/tenant-reader-v1','writer':'identity/gitlab/tenants-writer-v1'}
UUID=r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}'
class Blocked(Exception):pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise Blocked('RedirectDenied')
def validate(token,receipt,path):
 safe(token,limit=4096);safe(receipt,optional=True);d=read(path)
 patterns={'scope':r'gitlab-native-bootstrap-custody-v1','setup_id':r'[a-f0-9]{64}','actor_subject':UUID,'gitlab_origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?','bao_origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?','ca_file':r'/[A-Za-z0-9_./-]+','toolbox_pod':r'gitlab-toolbox-[a-z0-9-]{1,70}','toolbox_uid':UUID,'gitlab_namespace_uid':UUID,'expires_at':r'[0-9]{4}-[0-9]{2}-[0-9]{2}'}
 if not isinstance(d,dict) or set(d)!=set(patterns)|{'run','allow_parent_create','actor_native_id'}:raise Blocked('InvalidSelection')
 for key,pattern in patterns.items():
  if not isinstance(d[key],str) or not re.fullmatch(pattern,d[key]):raise Blocked('NonliteralSelection')
 if d['run'] is not True or d['allow_parent_create'] is not True or type(d['actor_native_id']) is not int or not 0<d['actor_native_id']<2**63:raise Blocked('ExplicitScopeRequired')
 expiry=dt.datetime.combine(dt.date.fromisoformat(d['expires_at']),dt.time(),dt.timezone.utc)
 if not 3600<=(expiry-dt.datetime.now(dt.timezone.utc)).total_seconds()<=172800:raise Blocked('ExpiryOutsidePilotWindow')
 safe(d['ca_file'],private=False,limit=262144)
 if os.path.lexists(receipt):raise Blocked('ExistingAttemptRequiresReview')
 return d
class Bao:
 def __init__(self,d,token):
  safe(token,limit=4096);before=os.lstat(token);fd=os.open(token,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  try:
   opened=os.fstat(fd)
   if (before.st_dev,before.st_ino)!=(opened.st_dev,opened.st_ino) or not stat.S_ISREG(opened.st_mode) or opened.st_uid!=os.getuid() or stat.S_IMODE(opened.st_mode)!=0o600 or opened.st_nlink!=1 or opened.st_size>4096:raise Blocked('UnsafeCustodyToken')
   self.token=os.read(fd,4097).decode().strip()
  finally:os.close(fd)
  self.origin=d['bao_origin'];self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect,urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=d['ca_file'])))
  if not re.fullmatch(r'[A-Za-z0-9_.-]{8,4096}',self.token):raise Blocked('InvalidCustodyToken')
 def call(self,path,method='GET',body=None,missing=False):
  req=urllib.request.Request(self.origin+'/v1/'+path,method=method,data=None if body is None else json.dumps(body).encode(),headers={'X-Vault-Token':self.token,'Content-Type':'application/json'})
  try:
   with self.opener.open(req,timeout=15) as response:
    raw=response.read(65537)
    if len(raw)>65536:raise Blocked('OversizeCustodyResponse')
    return json.loads(raw)
  except urllib.error.HTTPError as exc:
   if missing and exc.code==404:return None
   raise Blocked('CustodyRequestDenied') from None
 def authority(self):
  d=self.call('auth/token/lookup-self')['data']
  if d.get('policies')!=[POLICY] or d.get('identity_policies',[]) or d.get('renewable') is not False or d.get('period',0) or not 900<=d.get('ttl',0)<=3600:raise Blocked('UnapprovedCustodyAuthority')
  actual=self.call('sys/policies/acl/'+POLICY)['data']['policy']
  if hashlib.sha256(actual.encode()).digest()!=hashlib.sha256((HERE/'gitlab-custody-policy.hcl').read_bytes()).digest():raise Blocked('CustodyPolicyDrift')
 def preflight(self):
  self.authority()
  for path in RECORDS.values():
   if self.call('platform/metadata/'+path,missing=True) is not None:raise Blocked('ForeignCustodyRecord')
 def store(self,kind,data):
  self.authority();path='platform/data/'+RECORDS[kind]
  result=self.call(path,'POST',{'options':{'cas':0},'data':data})
  if result.get('data',{}).get('version')!=1:raise Blocked('UnexpectedCustodyVersion')
  observed=self.call(path)['data']
  if observed.get('metadata',{}).get('version')!=1 or observed.get('data')!=data:raise Blocked('CustodyReadbackFailed')

def sync_parent(path):
 fd=os.open(str(Path(path).parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)
def save(path,value,first=False):
 safe(path,optional=first)
 if first:
  fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'w') as f:json.dump(value,f);f.flush();os.fsync(f.fileno())
  sync_parent(path)
  return
 if read(path).get('setup_id')!=value.get('setup_id'):raise Blocked('ForeignAttemptReceipt')
 fd,name=tempfile.mkstemp(prefix='.bootstrap-',dir=str(Path(path).parent))
 try:
  with os.fdopen(fd,'w') as f:json.dump(value,f);f.flush();os.fsync(f.fileno())
  os.replace(name,path);sync_parent(path)
 finally:
  if os.path.exists(name):os.unlink(name)
def command(argv,input=None):
 try:
  p=subprocess.run(argv,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120,check=False)
 except Exception:raise Blocked('NativeExecutionUncertain') from None
 if p.returncode or len(p.stdout)>65536:raise Blocked('NativeExecutionUncertain')
 return p.stdout

def native(d,mode='mint',minted=None):
 # Pin the selected target namespace and Pod before sending any native code.
 namespace=json.loads(command(['kubectl','get','namespace','gitlab','-o','json']))
 pod=json.loads(command(['kubectl','-n','gitlab','get','pod',d['toolbox_pod'],'-o','json']))
 if namespace['metadata']['uid']!=d['gitlab_namespace_uid'] or pod['metadata']['uid']!=d['toolbox_uid']:raise Blocked('NativeTargetChanged')
 selected={k:d[k] for k in ('run','allow_parent_create','setup_id','actor_native_id','actor_subject','gitlab_origin','expires_at')};selected['mode']=mode
 if mode=='revoke':selected.update({k:minted[k] for k in ('parent_id','writer_token_id','reader_token_id')})
 encoded=base64.b64encode(json.dumps(selected).encode()).decode()
 script=(HERE/'gitlab-bootstrap.rb').read_text()+"\nrequire 'base64'\nresult=PerkforgeIdentityBootstrap.execute(JSON.parse(Base64.strict_decode64('"+encoded+"')))\nSTDOUT.write('PERKFORGE_RESULT:'+JSON.generate(result)+\"\\n\")\n"
 raw=command(['kubectl','-n','gitlab','exec','-i',d['toolbox_pod'],'-c','toolbox','--','gitlab-rails','runner','-'],script.encode())
 lines=[x[len(b'PERKFORGE_RESULT:'):] for x in raw.splitlines() if x.startswith(b'PERKFORGE_RESULT:')]
 if len(lines)!=1:raise Blocked('NativeResultUncertain')
 return json.loads(lines[0])

def execute(d,token,receipt,bao_factory=Bao,native_call=native):
 state={'schema':1,'setup_id':d['setup_id'],'stage':'CustodyPreflight','stored':[]};minted=None
 try:
  bao=bao_factory(d,token);bao.preflight()
  save(receipt,state,first=True)
  state['stage']='NativeRequested';save(receipt,state)
  minted=native_call(d)
  required={'stage','parent_id','writer_token_id','reader_token_id','writer_token','reader_token'}
  if isinstance(minted,dict) and minted.get('stage')=='ManualRecovery':
   report={'stage':'ManualRecovery'}
   for key in ('parent_id','writer_token_id','reader_token_id'):
    if type(minted.get(key)) is int and 0<minted[key]<2**63:report[key]=minted[key]
   for key in ('writer_revoked','reader_revoked'):
    if type(minted.get(key)) is bool:report[key]=minted[key]
   if minted.get('substage') in ('NativePreflight','ParentCreation','WriterCreation','ReaderCreation'):report['substage']=minted['substage']
   state['native_report']=report
  if not isinstance(minted,dict) or set(minted)!=required or minted['stage']!='Minted':raise Blocked('NativeResultUncertain')
  if any(type(minted[k]) is not int or not 0<minted[k]<2**63 for k in ('parent_id','writer_token_id','reader_token_id')) or any(not isinstance(minted[k],str) or not re.fullmatch(r'[A-Za-z0-9_.-]{8,4096}',minted[k]) for k in ('writer_token','reader_token')):raise Blocked('NativeResultUncertain')
  state.update({k:minted[k] for k in ('parent_id','writer_token_id','reader_token_id')});state['stage']='NativeMinted';save(receipt,state)
  for kind in ('reader','writer'):
   bao.store(kind,{'token':minted[kind+'_token'],'setup_id':d['setup_id'],'native_token_id':minted[kind+'_token_id'],'expires_at':d['expires_at']})
   state['stored'].append(kind);save(receipt,state)
  state['stage']='GitLabCustodyVerified';save(receipt,state)
  return {'stage':state['stage'],'keycloak_activation':False,'runtime_deployed':False}
 except Exception as exc:
  category=str(exc) if isinstance(exc,Blocked) else 'SetupFailed'
  state['stage']='ManualRecovery' if os.path.lexists(receipt) else 'BlockedBeforeNative';state['category']=category
  if isinstance(minted,dict) and minted.get('stage')=='Minted' and all(type(minted.get(k)) is int and minted[k]>0 for k in ('parent_id','writer_token_id','reader_token_id')):
   try:state['revocation']=native_call(d,'revoke',minted).get('stage','Unverified')
   except Exception:state['revocation']='Unverified'
  if os.path.lexists(receipt):
   try:save(receipt,state)
   except Exception:state['stage']='ManualRecovery';state['category']='ReceiptDurabilityUnverified'
  return {'stage':state['stage'],'category':state['category'],'revocation':state.get('revocation','NotVerified'),'runtime_deployed':False}
 finally:minted=None

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='inert');p.add_argument('token',nargs='?');p.add_argument('receipt',nargs='?');p.add_argument('inputs',nargs='?');a=p.parse_args()
 if a.mode not in ('validate','apply'):print('INERT: explicit bootstrap/custody selection required');return 0
 try:
  d=validate(a.token,a.receipt,a.inputs)
  if a.mode=='validate':print('Validated; zero native/custody requests');return 0
  lock=a.receipt+'.lock';safe(lock,optional=True,limit=0);fd=os.open(lock,os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK|(os.O_CREAT|os.O_EXCL if not os.path.lexists(lock) else 0),0o600)
  try:
   st=os.fstat(fd)
   if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o600 or st.st_nlink!=1 or st.st_size:raise Blocked('UnsafeLock')
   fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   if os.path.lexists(a.receipt):raise Blocked('ExistingAttemptRequiresReview')
   result=execute(d,a.token,a.receipt);print(json.dumps(result));return 0 if result['stage']=='GitLabCustodyVerified' else 1
  finally:os.close(fd)
 except Exception:print('{"stage":"BlockedBeforeNative","category":"InvalidSelectionOrExistingAttempt"}');return 1
if __name__=='__main__':raise SystemExit(main())
