#!/usr/bin/env python3
"""One owned writer replacement only; no issuer/root/reader/automatic retry."""
import argparse,base64,datetime as dt,fcntl,hashlib,importlib.util,json,os,re,stat,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('bootstrap_common',HERE/'bootstrap-gitlab.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
Blocked=base.Blocked;safe=base.safe
sys.path.insert(0,str(HERE.parent/'acceptance'))
from validate import read
POLICY='tenant-identity-writer-rotation-v1'
RECORD='identity/gitlab/tenants-writer-v1'
RUBY_SHA256='4f035e893b9f055a7f62061d443fef3afa976c5ab976548891cc828e7dba4dc9'
SUBJECT='64f9a45d-083e-43b8-be26-e796dfd20928'

def validate(token,receipt,path):
 safe(token,limit=4096);safe(receipt,optional=True);d=read(path)
 patterns={'scope':r'gitlab-tenants-writer-rotation-v1','attempt_id':r'[a-f0-9]{64}','actor_subject':base.UUID,'gitlab_origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?','bao_origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?','ca_file':r'/[A-Za-z0-9_./-]+','toolbox_pod':r'gitlab-toolbox-[a-z0-9-]{1,70}','toolbox_uid':base.UUID,'gitlab_namespace_uid':base.UUID,'expires_at':r'[0-9]{4}-[0-9]{2}-[0-9]{2}','original_receipt_file':r'/[A-Za-z0-9_./-]+'}
 ints={'actor_native_id':3,'parent_id':7,'old_token_id':2,'expected_record_version':1}
 if not isinstance(d,dict) or set(d)!=set(patterns)|set(ints)|{'run','expected_bot_id'}:raise Blocked('InvalidSelection')
 for k,p in patterns.items():
  if not isinstance(d[k],str) or not re.fullmatch(p,d[k]):raise Blocked('NonliteralSelection')
 if d['run'] is not True or d['actor_subject']!=SUBJECT:raise Blocked('ActorOrScopeMismatch')
 for k,v in ints.items():
  if type(d[k]) is not int or d[k]!=v:raise Blocked('OwnedBindingMismatch')
 if type(d['expected_bot_id']) is not int or not 0<d['expected_bot_id']<2**63:raise Blocked('BotBindingRequired')
 expiry=dt.datetime.combine(dt.date.fromisoformat(d['expires_at']),dt.time(),dt.timezone.utc)
 if not 3600<=(expiry-dt.datetime.now(dt.timezone.utc)).total_seconds()<=172800:raise Blocked('ExpiryOutsidePilotWindow')
 original=read(d['original_receipt_file'])
 if not isinstance(original,dict) or original.get('stage')!='GitLabCustodyVerified' or original.get('parent_id')!=7 or original.get('writer_token_id')!=2 or not isinstance(original.get('setup_id'),str) or not re.fullmatch(r'[a-f0-9]{64}',original['setup_id']) or set(original.get('stored',[]))!={'reader','writer'}:raise Blocked('OriginalReceiptMismatch')
 d['original_setup_id']=original['setup_id']
 safe(d['ca_file'],private=False,limit=262144)
 if os.path.lexists(receipt):raise Blocked('ExistingAttemptManualRecovery')
 return d

class Bao(base.Bao):
 def authority(self):
  v=self.call('auth/token/lookup-self')['data']
  if v.get('policies')!=[POLICY] or v.get('identity_policies',[]) or v.get('renewable') is not False or v.get('period',0) or not 900<=v.get('ttl',0)<=3600 or v.get('explicit_max_ttl')!=3600:raise Blocked('UnapprovedCustodyAuthority')
  actual=self.call('sys/policies/acl/'+POLICY)['data']['policy']
  if actual!=(HERE/'writer-rotation-policy.hcl').read_text():raise Blocked('CustodyPolicyDrift')
 def preflight(self,d):
  self.authority()
  m=self.call('platform/metadata/'+RECORD)['data']
  if m.get('current_version')!=1:raise Blocked('CustodyVersionChanged')
  v=self.call('platform/data/'+RECORD)['data'];old=v.get('data',{});meta=v.get('metadata',{})
  if meta.get('version')!=1 or meta.get('destroyed') or meta.get('deletion_time') or set(old)!={'token','setup_id','native_token_id','expires_at'} or old.get('setup_id')!=d['original_setup_id'] or old.get('native_token_id')!=2 or old.get('expires_at')!='2026-11-16':raise Blocked('OriginalCustodyMismatch')
  # Old token value is never authenticated, printed or returned.
 def store(self,d,new):
  self.authority()
  data={'token':new['successor_token'],'setup_id':d['original_setup_id'],'native_token_id':new['successor_id'],'expires_at':d['expires_at'],'previous_native_token_id':2,'rotation_attempt':d['attempt_id']}
  r=self.call('platform/data/'+RECORD,'POST',{'options':{'cas':1},'data':data})
  if r.get('data',{}).get('version')!=2:raise Blocked('CustodyWriteUncertain')
  v=self.call('platform/data/'+RECORD)['data']
  if v.get('metadata',{}).get('version')!=2 or v.get('data')!=data:raise Blocked('CustodyReadbackFailed')

def native(d,mode='rotate',successor=None):
 namespace=json.loads(base.command(['kubectl','get','namespace','gitlab','-o','json']))
 pod=json.loads(base.command(['kubectl','-n','gitlab','get','pod',d['toolbox_pod'],'-o','json']))
 if namespace['metadata']['uid']!=d['gitlab_namespace_uid'] or pod['metadata']['uid']!=d['toolbox_uid']:raise Blocked('NativeTargetChanged')
 selected={k:d[k] for k in ('run','attempt_id','original_setup_id','actor_native_id','actor_subject','gitlab_origin','parent_id','old_token_id','expected_bot_id','expires_at')};selected['mode']=mode
 if mode=='revoke-successor':selected['successor_id']=successor['successor_id']
 encoded=base64.b64encode(json.dumps(selected).encode()).decode()
 source=HERE/'gitlab-writer-rotation.rb';fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  st=os.fstat(fd)
  if not stat.S_ISREG(st.st_mode) or st.st_size>65536:raise Blocked('NativeSourceInvalid')
  raw_source=os.read(fd,65537)
 finally:os.close(fd)
 if hashlib.sha256(raw_source).hexdigest()!=RUBY_SHA256:raise Blocked('NativeSourceChanged')
 script=raw_source.decode()+"\nrequire 'base64'\nr=PerkforgeIdentityWriterRotation.execute(JSON.parse(Base64.strict_decode64('"+encoded+"')))\nSTDOUT.write('PERKFORGE_ROTATION:'+JSON.generate(r)+\"\\n\")\n"
 raw=base.command(['kubectl','-n','gitlab','exec','-i',d['toolbox_pod'],'-c','toolbox','--','gitlab-rails','runner','-'],script.encode())
 lines=[x[len(b'PERKFORGE_ROTATION:'):] for x in raw.splitlines() if x.startswith(b'PERKFORGE_ROTATION:')]
 if len(lines)!=1:raise Blocked('NativeResponseUncertain')
 return json.loads(lines[0])

def binding(d,new):
 return isinstance(new,dict) and all(new.get(k)==v for k,v in {'parent_id':7,'old_token_id':2,'bot_id':d['expected_bot_id'],'attempt_id':d['attempt_id'],'original_setup_id':d['original_setup_id'],'expires_at':d['expires_at']}.items()) and type(new.get('successor_id')) is int and new['successor_id']>0 and new['successor_id']!=2

def execute(d,token,receipt,bao_factory=Bao,native_call=native):
 state={'schema':1,'setup_id':d['attempt_id'],'original_setup_id':d['original_setup_id'],'parent_id':7,'old_token_id':2,'bot_id':d['expected_bot_id'],'expected_record_version':1,'stage':'CustodyPreflight'};new=None;owned=False
 try:
  if os.path.lexists(receipt):raise Blocked('ExistingAttemptManualRecovery')
  bao=bao_factory(d,token);bao.preflight(d)
  base.save(receipt,state,first=True)
  state['stage']='RotationRequested';base.save(receipt,state)
  new=native_call(d)
  owned=binding(d,new)
  if not owned or new.get('stage')!='Rotated':raise Blocked('NativeResponseUncertain')
  state['successor_id']=new['successor_id'];state['stage']='NativeRotated';base.save(receipt,state)
  if not isinstance(new.get('successor_token'),str) or not re.fullmatch(r'[A-Za-z0-9_.-]{8,4096}',new['successor_token']):raise Blocked('InvalidSuccessorResponse')
  state['stage']='CustodyCASRequested';base.save(receipt,state)
  bao.store(d,new)
  state['stage']='WriterCustodyVerified';state['record_version']=2;base.save(receipt,state)
  return {'stage':state['stage'],'successor_id':new['successor_id'],'record_version':2,'eso_delivery':'NotVerified','reader_rotated':False}
 except Exception as exc:
  category=str(exc) if isinstance(exc,Blocked) else 'RotationFailed'
  state['stage']='ManualRecovery' if os.path.lexists(receipt) else 'BlockedBeforeNative';state['category']=category
  if owned:
   try:
    result=native_call(d,'revoke-successor',new)
    state['successor_revocation']='Verified' if binding(d,result) and result.get('stage')=='Revoked' else 'Unverified'
   except Exception:state['successor_revocation']='Unverified'
  if os.path.lexists(receipt) and category!='ExistingAttemptManualRecovery':
   try:base.save(receipt,state)
   except Exception:state['category']='ReceiptDurabilityUnverified'
  return {k:state[k] for k in ('stage','category','successor_revocation') if k in state}
 finally:new=None

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='inert');p.add_argument('token',nargs='?');p.add_argument('receipt',nargs='?');p.add_argument('inputs',nargs='?');a=p.parse_args()
 if a.mode not in ('validate','apply'):print('INERT');return 0
 try:
  d=validate(a.token,a.receipt,a.inputs)
  if a.mode=='validate':print('Validated; no native/custody requests');return 0
  lock=a.receipt+'.lock';safe(lock,optional=True,limit=0)
  fd=os.open(lock,os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK|(os.O_CREAT|os.O_EXCL if not os.path.lexists(lock) else 0),0o600)
  try:
   safe(lock,limit=0)
   opened=os.fstat(fd);current=os.lstat(lock)
   if not stat.S_ISREG(opened.st_mode) or opened.st_uid!=os.getuid() or stat.S_IMODE(opened.st_mode)!=0o600 or opened.st_nlink!=1 or opened.st_size or (opened.st_dev,opened.st_ino)!=(current.st_dev,current.st_ino):raise Blocked("UnsafeLock")
   fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   r=execute(d,a.token,a.receipt);print(json.dumps(r));return 0 if r['stage']=='WriterCustodyVerified' else 1
  finally:os.close(fd)
 except Exception:print('{"stage":"BlockedBeforeNative","category":"InvalidSelectionOrExistingAttempt"}');return 1
if __name__=='__main__':raise SystemExit(main())
