#!/usr/bin/env python3
"""Read exact canonical group membership; never configure Keycloak or grant access."""
import argparse,datetime as dt,hashlib,json,os,re,ssl,stat,urllib.request
from pathlib import Path
import yaml
from verify_group_paths import safe
LIMIT=262144
ROLES={'tenant-admin':'Owner','tenant-developer':'Developer','tenant-viewer':'Reporter'}
UUID=r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}'
def unique(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise ValueError('duplicate key')
  d[k]=v
 return d
def private(path,limit=LIMIT):
 safe(path,limit=limit)
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  s=os.fstat(fd)
  if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600 or s.st_nlink!=1 or s.st_size>limit:raise ValueError('unsafe opened file')
  with os.fdopen(fd,'rb',closefd=False) as f:data=f.read(limit+1)
  if len(data)>limit:raise ValueError('oversize')
  return data
 finally:os.close(fd)
def validate(path):
 d=json.loads(private(path),object_pairs_hook=unique)
 keys={'context','source_revision','origin','ca_file','contract_sha256','group_ids'}
 if not isinstance(d,dict) or set(d)!=keys:raise ValueError('input fields')
 for k,p in {'context':r'[a-z][a-z0-9-]{0,30}','source_revision':r'[a-f0-9]{40}','origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?(?:/auth)?','ca_file':r'/[A-Za-z0-9_./-]+','contract_sha256':r'[a-f0-9]{64}'}.items():
  if not isinstance(d[k],str) or not re.fullmatch(p,d[k]):raise ValueError('nonliteral input')
 if d['context'] in {'platform','system','default','tenants'}:raise ValueError('reserved context')
 groups=d['group_ids']
 if not isinstance(groups,dict) or set(groups)!=set(ROLES) or any(not isinstance(v,str) or not re.fullmatch(UUID,v) for v in groups.values()) or len(set(groups.values()))!=3:raise ValueError('group bindings')
 safe(d['ca_file'],limit=LIMIT,private=False)
 contract=Path(__file__).resolve().parents[3]/'authorization/contexts'/ (d['context']+'.yaml')
 raw=contract.read_bytes()
 if len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=d['contract_sha256']:raise ValueError('contract mismatch')
 c=yaml.safe_load(raw)['paas_context']
 if c['schema_version']!=1 or c['id']!=d['context'] or c['targets']['gitlab']['role_mappings']!=ROLES:raise ValueError('canonical GitLab mapping')
 expected={r:'/tenants/'+d['context']+'/'+leaf for r,leaf in [('tenant-admin','admins'),('tenant-developer','developers'),('tenant-viewer','viewers')]}
 if c['keycloak']['groups']!=expected or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',c['keycloak']['realm']):raise ValueError('canonical group contract')
 return d,c
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError('redirect forbidden')
def snapshot(d,c,token):
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=d['ca_file'])))
 base=d['origin']+'/admin/realms/'+c['keycloak']['realm']
 def get(path):
  req=urllib.request.Request(base+path,headers={'Authorization':'Bearer '+token,'Accept':'application/json'},method='GET')
  with opener.open(req,timeout=10) as response:
   if response.status!=200:raise ValueError('read failed')
   raw=response.read(LIMIT+1)
   if len(raw)>LIMIT:raise ValueError('oversize response')
   return json.loads(raw,object_pairs_hook=unique)
 def one_pass():
  people={};bindings=[]
  for role in sorted(ROLES):
   gid=d['group_ids'][role];path=c['keycloak']['groups'][role]
   meta=get('/groups/'+gid)
   if not isinstance(meta,dict) or meta.get('id')!=gid or meta.get('path')!=path or meta.get('subGroupCount')!=0 or meta.get('subGroups',[])!=[]:raise ValueError('group drift or nesting')
   bindings.append({'role':role,'id':gid,'path':path})
   seen=set()
   for first in range(0,501,100):
    page=get('/groups/'+gid+'/members?briefRepresentation=true&first='+str(first)+'&max=100')
    if not isinstance(page,list) or len(page)>100 or first+len(page)>500:raise ValueError('membership bound exceeded')
    for user in page:
     if not isinstance(user,dict) or not isinstance(user.get('id'),str) or not re.fullmatch(UUID,user['id']) or type(user.get('enabled')) is not bool:raise ValueError('member identity')
     subject=user['id']
     if subject in seen or subject in people:raise ValueError('duplicate or conflicting roles')
     seen.add(subject);people[subject]={'subject':subject,'role':role,'enabled':user['enabled']}
    if len(page)<100:break
   else:raise ValueError('membership bound exceeded')
  return {'groups':bindings,'members':[people[s] for s in sorted(people)]}
 first=one_pass();second=one_pass()
 if first!=second:raise ValueError('membership changed during read')
 return {'schema':1,'stage':'SnapshotVerified','context':d['context'],'source_revision':d['source_revision'],'contract_sha256':d['contract_sha256'],'origin':d['origin'],'realm':c['keycloak']['realm'],'captured_at':dt.datetime.now(dt.timezone.utc).isoformat(),**second}
def main():
 p=argparse.ArgumentParser();mode=p.add_mutually_exclusive_group();mode.add_argument('--read',action='store_true');mode.add_argument('--validate',action='store_true');p.add_argument('token',nargs='?');p.add_argument('receipt',nargs='?');p.add_argument('inputs',nargs='?');a=p.parse_args()
 if not a.read and not a.validate:print('INERT: explicit read required');return
 d,c=validate(a.inputs);safe(a.token,limit=4096);safe(a.receipt,optional=True)
 if os.path.lexists(a.receipt):raise ValueError('fresh receipt required')
 if a.validate:print('Validated; no authentication or file creation');return
 token=private(a.token,4096).decode('ascii').strip()
 if not re.fullmatch(r'[A-Za-z0-9_.-]{8,4096}',token):raise ValueError('invalid token encoding')
 fd=os.open(a.receipt,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);owned=os.fstat(fd)
 try:
  result=snapshot(d,c,token)
  with os.fdopen(fd,'wb',closefd=False) as f:f.write((json.dumps(result,sort_keys=True)+'\n').encode());f.flush();os.fsync(fd)
  print('SnapshotVerified; native authority and caller provenance remain external acceptance gates')
 except Exception:
  current=os.lstat(a.receipt)
  if (current.st_dev,current.st_ino)==(owned.st_dev,owned.st_ino):os.unlink(a.receipt)
  raise
 finally:os.close(fd)
if __name__=='__main__':
 try:main()
 except Exception:raise SystemExit('Canonical identity snapshot unavailable; no native mutation performed.')
