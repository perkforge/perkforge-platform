#!/usr/bin/env python3
"""Strict literal input/path/lock preflight only; no native requests."""
import sys,json,os,stat,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from verify_group_paths import safe,verify
from identity_context import derive

def read(path):
 safe(path)
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  s=os.fstat(fd)
  if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600 or s.st_nlink!=1 or s.st_size>65536:raise ValueError()
  raw=os.read(fd,65537)
 finally:os.close(fd)
 def unique(pairs):
  d={}
  for k,v in pairs:
   if k in d:raise ValueError()
   d[k]=v
  return d
 return json.loads(raw,object_pairs_hook=unique)

def check(token,receipt,inputs,mode):
 safe(token,limit=4096);safe(receipt,optional=True,limit=4096)
 v=read(inputs)
 required={'gitlab_acceptance_run','gitlab_acceptance_scope','gitlab_acceptance_context','gitlab_acceptance_origin','gitlab_acceptance_ca','gitlab_acceptance_source_revision','gitlab_acceptance_group_receipt','gitlab_acceptance_actor_id'}
 optional={'gitlab_acceptance_project_receipt','gitlab_acceptance_runner_directory'}
 if not isinstance(v,dict) or not required<=v.keys() or not v.keys()<=required|optional:raise ValueError()
 if v['gitlab_acceptance_run'] is not True or v['gitlab_acceptance_scope'] not in ('tenant-acceptance-project-v1','tenant-acceptance-runner-v1','tenant-acceptance-seed-v1'):raise ValueError()
 if type(v['gitlab_acceptance_actor_id']) is not int or not 0<v['gitlab_acceptance_actor_id']<2**63:raise ValueError()
 patterns={'gitlab_acceptance_context':r'[a-z][a-z0-9-]{0,30}','gitlab_acceptance_origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?','gitlab_acceptance_source_revision':r'[a-f0-9]{40}'}
 for k in required|optional:
  if k in patterns:
   if not isinstance(v[k],str) or not re.fullmatch(patterns[k],v[k]):raise ValueError()
  elif k not in ('gitlab_acceptance_run','gitlab_acceptance_scope','gitlab_acceptance_actor_id') and k in v:
   if not isinstance(v[k],str) or not re.fullmatch(r'/[A-Za-z0-9_./-]+',v[k]):raise ValueError()
 derive(v['gitlab_acceptance_context']);safe(v['gitlab_acceptance_ca'],private=False,limit=262144)
 g=read(v['gitlab_acceptance_group_receipt'])
 if not isinstance(g,dict) or g.get('stage')!='group-ready' or g.get('context')!=v['gitlab_acceptance_context'] or g.get('origin')!=v['gitlab_acceptance_origin']:raise ValueError()
 for k in ('group_id','parent_id'):
  if type(g.get(k)) is not int or g[k]<=0:raise ValueError()
 if v['gitlab_acceptance_scope'] in ('tenant-acceptance-runner-v1','tenant-acceptance-seed-v1'):
  if 'gitlab_acceptance_project_receipt' not in v:raise ValueError()
  p=read(v['gitlab_acceptance_project_receipt'])
  if not isinstance(p,dict) or p.get('stage')!='project-ready' or p.get('context')!=g['context'] or p.get('group_id')!=g['group_id'] or p.get('origin')!=g['origin'] or p.get('source_revision')!=v['gitlab_acceptance_source_revision'] or type(p.get('project_id')) is not int or p['project_id']<=0:raise ValueError()
 if v['gitlab_acceptance_scope']=='tenant-acceptance-runner-v1':
  if not optional<=v.keys():raise ValueError()
  # Dedicated native runner custody dir. validate canonical ancestry via prospective leaf.
  safe(v['gitlab_acceptance_runner_directory']+'/runner-token',optional=True,limit=4096)
  rp=v['gitlab_acceptance_runner_directory']+'/runner-receipt.json'
  safe(rp,optional=True,limit=65536)
  if os.path.lexists(rp) and not isinstance(read(rp),dict):raise ValueError()
 if mode=='prepare':verify(token,receipt,prepare=True)
 if mode=='locked':verify(token,receipt,require_locked=True)
 return v
if __name__=='__main__':
 try:
  if len(sys.argv)!=5 or sys.argv[1] not in ('validate','prepare','locked'):raise ValueError()
  check(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[1])
 except (ValueError,OSError,KeyError,TypeError):raise SystemExit('Acceptance preflight rejected; no native request permitted.')
 print('Acceptance preflight verified.')
