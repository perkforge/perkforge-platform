#!/usr/bin/env python3
"""Literal source selection, protected issuance receipts and token-file custody."""
import importlib.util,json,os,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('base',HERE/'bootstrap-gitlab.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
sys.path.insert(0,str(HERE.parent))
from identity_context import derive,policy_text
def binding(r,context=None):
 common={'schema','setup_id','stage','accessors','revoked'}
 if type(r.get('schema')) is not int:raise ValueError('receipt schema')
 if r.get('schema')==1 and set(r)==common:
  c=derive('portal')
 elif r.get('schema')==2 and set(r)==common|{'identity_context','context_digest'}:
  c=derive(r['identity_context'])
  if r['context_digest']!=c['digest']:raise ValueError('context digest')
 else:raise ValueError('receipt shape')
 if context is not None and c['context']!=context:raise ValueError('crossed context')
 return c
def policies(c):return {'gitlab':'tenant-identity-bootstrap-gitlab-v1','keycloak':c['bootstrap_policy']}
def inputs(token,receipt,path,legacy_cleanup=False):
 if any(not re.fullmatch(r'/[A-Za-z0-9_./-]+',p) for p in (token,receipt,path)):raise ValueError()
 b.safe(token,limit=4096);b.safe(receipt,optional=True);d=b.read(path)
 patterns={'scope':r'identity-custody-issuer-v1','setup_id':r'[a-f0-9]{64}','bao_origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?','ca_file':r'/[A-Za-z0-9_./-]+','cluster_id':b.UUID}
 if not isinstance(d,dict) or d.get('run') is not True:raise ValueError()
 if set(d)==set(patterns)|{'run'} and legacy_cleanup:
  r=b.read(receipt)
  if r.get('schema')!=1 or r.get('setup_id')!=d['setup_id']:raise ValueError('legacy cleanup only')
  binding(r,'portal');d['identity_context']='portal'
 elif set(d)!=set(patterns)|{'run','identity_context'}:raise ValueError('explicit context required')
 derive(d['identity_context'])
 if any(not isinstance(d[k],str) or not re.fullmatch(v,d[k]) for k,v in patterns.items()):raise ValueError()
 b.safe(d['ca_file'],private=False,limit=262144)
 for purpose in ('gitlab','keycloak'):b.safe(str(Path(receipt).parent/(purpose+'-setup-token')),optional=True,limit=4096)
 if os.path.lexists(receipt):binding(b.read(receipt),d['identity_context'])
 return d

def persist_token(receipt,setup,purpose,data):
 if purpose not in ('gitlab','keycloak'):raise ValueError()
 r=b.read(receipt)
 if r.get('setup_id')!=setup or r.get('stage')!='Requesting-'+purpose:raise ValueError()
 a=data['auth'];policy=policies(binding(r))[purpose]
 # Record an accessor before handling the secret: failures retain ownership evidence.
 if not isinstance(a.get('accessor'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,256}',a['accessor']):raise ValueError()
 r['accessors'][purpose]=a['accessor'];r['stage']='Received-'+purpose;b.save(receipt,r)
 if a.get('policies')!=[policy] or a.get('identity_policies',[]) or a.get('renewable') is not False or type(a.get('lease_duration')) is not int or not 900<=a['lease_duration']<=3600 or not isinstance(a.get('client_token'),str) or not re.fullmatch(r'[A-Za-z0-9_.-]{8,4096}',a['client_token']):raise ValueError()
 path=str(Path(receipt).parent/(purpose+'-setup-token'));b.safe(path,optional=True,limit=4096)
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w') as f:f.write(a['client_token']);f.flush();os.fsync(f.fileno())
 b.sync_parent(path);r['stage']='Stored-'+purpose;b.save(receipt,r)

def main():
 mode=sys.argv[1] if len(sys.argv)>1 else 'inert'
 if mode=='inert':print('INERT');return
 if mode in ('validate','validate-cleanup','prepare','prepare-cleanup','locked','locked-cleanup'):
  token,receipt,path=sys.argv[2:];d=inputs(token,receipt,path,legacy_cleanup=mode.endswith('cleanup'))
  if mode in ('validate','validate-cleanup'):return
  spec=importlib.util.spec_from_file_location('guard',HERE.parent/'verify_group_paths.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
  g.verify(token,receipt,prepare=mode in ('prepare','prepare-cleanup'),require_locked=mode in ('locked','locked-cleanup'))
  if mode=='locked-cleanup':
   r=b.read(receipt)
   if r.get('setup_id')!=d['setup_id'] or r.get('schema') not in (1,2) or not isinstance(r.get('accessors'),dict) or set(r['accessors'])-{'gitlab','keycloak'}:raise ValueError()
  if mode=='locked':
   if os.path.lexists(receipt) or any(os.path.lexists(Path(receipt).parent/(p+'-setup-token')) for p in ('gitlab','keycloak')):raise ValueError('Existing attempt requires review')
   b.save(receipt,{'schema':2,'setup_id':d['setup_id'],'stage':'Preflight','accessors':{},'revoked':[],'identity_context':d['identity_context'],'context_digest':derive(d['identity_context'])['digest']},first=True)
 elif mode=='contract':
  receipt,setup=sys.argv[2:];r=b.read(receipt)
  if r['setup_id']!=setup:raise ValueError()
  c=binding(r);print(json.dumps({'names':c,'keycloak_policy':policy_text(c['context']),'token_policies':policies(c)}))
 elif mode=='record':
  receipt,setup,stage=sys.argv[2:];r=b.read(receipt)
  if r.get('setup_id')!=setup or stage not in ('Requesting-gitlab','Requesting-keycloak','Issued','ManualRecovery','Cleaned'):raise ValueError()
  binding(r);r['stage']=stage;b.save(receipt,r)
 elif mode=='token':
  receipt,setup,purpose=sys.argv[2:];raw=sys.stdin.buffer.read(65537)
  if len(raw)>65536:raise ValueError()
  persist_token(receipt,setup,purpose,json.loads(raw))
 elif mode=='revoked':
  receipt,setup,purpose=sys.argv[2:];r=b.read(receipt)
  if r.get('setup_id')!=setup or purpose not in ('gitlab','keycloak') or purpose not in r['accessors']:raise ValueError()
  binding(r);r['revoked']=sorted(set(r['revoked'])|{purpose});b.save(receipt,r)
 else:raise ValueError()
if __name__=='__main__':
 try:main()
 except Exception:raise SystemExit('Issuer selection or durable custody unverified; no automatic retry')
