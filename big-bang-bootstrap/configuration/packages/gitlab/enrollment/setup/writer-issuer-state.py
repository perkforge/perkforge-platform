#!/usr/bin/env python3
"""Private selection/receipt custody only; all provider configuration is Ansible."""
import hashlib,importlib.util,json,os,re,stat,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('bootstrap',HERE/'bootstrap-gitlab.py');b=importlib.util.module_from_spec(sp);sp.loader.exec_module(b)
sp=importlib.util.spec_from_file_location('guard',HERE.parent/'verify_group_paths.py');g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
POLICY='tenant-identity-writer-rotation-v1'
def raw(path,limit=65536):
 g.safe(path,limit=limit);before=os.lstat(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  now=os.fstat(fd)
  if (before.st_dev,before.st_ino,before.st_mode,before.st_uid,before.st_nlink)!=(now.st_dev,now.st_ino,now.st_mode,now.st_uid,now.st_nlink):raise ValueError()
  data=os.read(fd,limit+1)
  if len(data)>limit:raise ValueError()
  return data
 finally:os.close(fd)
def unique(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise ValueError()
  d[k]=v
 return d
def read(p):return json.loads(raw(p),object_pairs_hook=unique)
def output(receipt):return str(Path(receipt).parent/'writer-rotation-setup-token')
def select(root,receipt,path):
 for p in (root,receipt,path):
  if not re.fullmatch(r'/[A-Za-z0-9_./-]+',p):raise ValueError()
 g.safe(root,limit=4096);g.safe(receipt,optional=True);g.safe(output(receipt),optional=True,limit=4096)
 if len({root,receipt,path,output(receipt),receipt+'.lock'})!=5:raise ValueError()
 d=read(path);patterns={'scope':'writer-rotation-issuer-v1','setup_id':r'[a-f0-9]{64}','bao_origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?','cluster_id':b.UUID,'ca_file':r'/[A-Za-z0-9_./-]+'}
 if not isinstance(d,dict) or set(d)!=set(patterns)|{'run'} or d['run'] is not True:raise ValueError()
 for k,p in patterns.items():
  if not isinstance(d[k],str) or not re.fullmatch(p,d[k]):raise ValueError()
 g.safe(d['ca_file'],private=False,limit=262144)
 if d['ca_file'] in (root,receipt,path,output(receipt),receipt+'.lock'):raise ValueError()
 return d
def digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def state(receipt,d):
 r=read(receipt)
 if r.get('schema')!=1 or r.get('setup_id')!=d['setup_id'] or r.get('selection_sha256')!=digest(d):raise ValueError()
 return r
def stdin():
 x=sys.stdin.buffer.read(65537)
 if len(x)>65536:raise ValueError()
 return json.loads(x,object_pairs_hook=unique)
def main():
 if len(sys.argv)==1:print('INERT');return
 mode,root,receipt,path=sys.argv[1:];d=select(root,receipt,path)
 if mode=='validate':return
 if mode=='prepare':g.verify(root,receipt,prepare=True);return
 g.verify(root,receipt,require_locked=True)
 if mode=='start':
  if os.path.lexists(receipt) or os.path.lexists(output(receipt)):raise ValueError()
  b.save(receipt,{'schema':1,'setup_id':d['setup_id'],'selection_sha256':digest(d),'stage':'Preflight'},first=True);return
 r=state(receipt,d)
 if mode=='root':
  token=raw(root,4096).decode().strip()
  if not re.fullmatch(r'[A-Za-z0-9_.-]{8,4096}',token):raise ValueError()
  print(token);return
 if mode=='record':
  stage=stdin()['stage']
  if stage not in ('PolicyRequested','Requesting','Issued','ManualRecovery','Cleaned'):raise ValueError()
  if stage=='Requesting':
   if 'requested_at' in r:raise ValueError()
   r['requested_at']=int(time.time())
  r['stage']=stage
 elif mode=='received':
  x=stdin();a=x['auth'];accessor=a.get('accessor')
  if r['stage']!='Requesting' or not isinstance(accessor,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,256}',accessor) or accessor==x['root_accessor']:raise ValueError()
  r.update(accessor=accessor,stage='Received')
 elif mode=='store':
  x=stdin();a=x['auth'];v=x['identity'];token=a.get('client_token')
  if r['stage']!='Received' or a.get('accessor')!=r['accessor'] or v.get('accessor')!=r['accessor'] or v.get('id')!=token or token==x['root_token']:raise ValueError()
  if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{8,4096}',token):raise ValueError()
  if a.get('policies')!=[POLICY] or a.get('identity_policies',[]) or a.get('renewable') is not False or type(a.get('lease_duration')) is not int or not 900<=a['lease_duration']<=3600:raise ValueError()
  verify_identity(v,r)
  if v['ttl']<900:raise ValueError()
  p=output(receipt);g.safe(p,optional=True,limit=4096)
  # Persist intended bytes before exclusive creation, allowing safe cleanup after a write/fsync failure.
  r['token_sha256']=hashlib.sha256(token.encode()).hexdigest();b.save(receipt,r)
  fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'w') as f:f.write(token);f.flush();os.fsync(f.fileno())
  b.sync_parent(p);r['stage']='Stored'
 elif mode=='cleanup-contract':
  if not isinstance(r.get('accessor'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,256}',r['accessor']) or type(r.get('requested_at')) is not int:raise ValueError()
  print(json.dumps({'accessor':r['accessor'],'requested_at':r['requested_at'],'display_name':'token-identity-writer-rotation-'+d['setup_id']}));return
 elif mode=='verify-cleanup':verify_identity(stdin(),r);return
 elif mode=='remove':
  p=output(receipt)
  if os.path.lexists(p):
   if not r.get('token_sha256') or hashlib.sha256(raw(p,4096)).hexdigest()!=r['token_sha256']:raise ValueError()
   os.unlink(p);b.sync_parent(p)
  r['revoked']=True
 else:raise ValueError()
 b.save(receipt,r)
def verify_identity(v,r):
 if v.get('type')!='service' or v.get('orphan') is not False:raise ValueError()
 if v.get('accessor')!=r['accessor'] or v.get('policies')!=[POLICY] or v.get('identity_policies',[]) or v.get('renewable') is not False or v.get('period',0)!=0 or v.get('explicit_max_ttl')!=3600 or v.get('creation_ttl')!=3600 or v.get('display_name')!='token-identity-writer-rotation-'+r['setup_id']:raise ValueError()
 if type(v.get('creation_time')) is not int or not r['requested_at']-5<=v['creation_time']<=r['requested_at']+60:raise ValueError()
 if type(v.get('ttl')) is not int or not 0<=v['ttl']<=3600:raise ValueError()
if __name__=='__main__':
 try:main()
 except Exception:raise SystemExit('Writer issuer selection/custody unverified; retain effects for manual recovery.')
