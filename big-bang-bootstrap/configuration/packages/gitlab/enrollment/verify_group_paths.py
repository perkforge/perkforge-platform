#!/usr/bin/env python3
"""Local path/lock verification only. Never reads credentials or calls an API."""
import argparse,fcntl,os,stat,re,json
from pathlib import Path

def safe(path,optional=False,limit=65536,private=True):
 p=Path(path)
 if not re.fullmatch(r'[A-Za-z0-9_./-]+',path) or not p.is_absolute() or str(p)!=path or '..' in p.parts:raise ValueError('noncanonical path')
 parts=list(reversed(p.parents))
 for parent in parts:
  s=parent.lstat()
  if not stat.S_ISDIR(s.st_mode) or s.st_uid not in (0,os.getuid()):raise ValueError('unsafe ancestor')
  writable=s.st_mode & 0o022
  sticky_root=s.st_uid==0 and bool(s.st_mode & stat.S_ISVTX)
  if writable and not sticky_root:raise ValueError('writable ancestor')
 # A root sticky directory itself is not a private custody directory.
 s=p.parent.lstat()
 if private and (s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o700):raise ValueError('private parent required')
 try:s=p.lstat()
 except FileNotFoundError:
  if optional:return
  raise
 if not stat.S_ISREG(s.st_mode) or s.st_uid not in ((os.getuid(),) if private else (0,os.getuid())) or (stat.S_IMODE(s.st_mode)!=0o600 if private else bool(s.st_mode & 0o022)) or s.st_nlink!=1 or s.st_size>limit:raise ValueError('unsafe leaf')
 # Open nonfollowing/nonblocking; reject replacement/type changes before returning.
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  now=os.fstat(fd)
  if (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_nlink)!=(now.st_dev,now.st_ino,now.st_mode,now.st_uid,now.st_nlink):raise ValueError('leaf changed')
 finally:os.close(fd)

def validate_inputs(path):
 def unique(pairs):
  result={}
  for key,value in pairs:
   if key in result:raise ValueError('duplicate input key')
   result[key]=value
  return result
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  s=os.fstat(fd)
  if not stat.S_ISREG(s.st_mode) or s.st_size>65536:raise ValueError('invalid inputs')
  with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(65537)
 finally:os.close(fd)
 if len(raw)>65536:raise ValueError('oversized inputs')
 data=json.loads(raw,object_pairs_hook=unique)
 allowed={'gitlab_group_run','gitlab_group_scope','gitlab_group_context','gitlab_group_source_revision','gitlab_group_previous_revision','gitlab_group_allow_parent_create','gitlab_group_expected_parent_id','gitlab_native_origin','gitlab_native_ca_file'}
 if not isinstance(data,dict) or not set(data)<=allowed:raise ValueError('unknown input keys')
 required={'gitlab_group_run','gitlab_group_scope','gitlab_group_context','gitlab_group_source_revision','gitlab_native_origin','gitlab_native_ca_file'}
 if not required<=set(data):raise ValueError('missing input keys')
 for key in ['gitlab_group_run','gitlab_group_allow_parent_create']:
  if key in data and type(data[key]) is not bool:raise ValueError('invalid boolean')
 if 'gitlab_group_expected_parent_id' in data and (type(data['gitlab_group_expected_parent_id']) is not int or not 0<=data['gitlab_group_expected_parent_id']<2**63):raise ValueError('invalid native ID')
 patterns={'gitlab_group_context':r'[a-z][a-z0-9-]{0,30}','gitlab_group_source_revision':r'[a-f0-9]{40}','gitlab_group_previous_revision':r'(?:[a-f0-9]{40})?','gitlab_native_origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?','gitlab_native_ca_file':r'/[A-Za-z0-9_./-]+'}
 for key,pattern in patterns.items():
  if key in data and (not isinstance(data[key],str) or not re.fullmatch(pattern,data[key])):raise ValueError('nonliteral input')
 if data['gitlab_group_scope']!='gitlab-enrollment-group-foundation-v1' or data['gitlab_group_context'] in {'platform','system','default','tenants'}:raise ValueError('unapproved scope')
 # Every value is a validated primitive before Ansible can evaluate templates/lookups.
 return data

def verify(token,receipt,inputs=None,prepare=False,require_locked=False,paths_only=False,ca=None):
 safe(token,limit=4096);safe(receipt,optional=True,limit=4096)
 if ca:safe(ca,limit=262144,private=False)
 if inputs:
  safe(inputs)
  validate_inputs(inputs)
 if paths_only:return
 lock=receipt+'.lock';safe(lock,optional=prepare,limit=0)
 fd=os.open(lock,os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK|(os.O_CREAT|os.O_EXCL if prepare and not os.path.lexists(lock) else 0),0o600)
 try:
  s=os.fstat(fd)
  if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600 or s.st_nlink!=1 or s.st_size:raise ValueError('unsafe lock')
  if require_locked:
   owner=int(os.environ.get('PERKFORGE_GROUP_LOCK_OWNER','0'))
   if owner<=1:raise ValueError('missing launcher lock owner')
   ancestors=set();pid=os.getppid()
   for _ in range(64):
    if pid<=1:break
    ancestors.add(pid)
    text=Path('/proc/'+str(pid)+'/status').read_text()
    pid=int(next(line.split()[1] for line in text.splitlines() if line.startswith('PPid:')))
   if owner not in ancestors:raise ValueError('lock owner is not this invocation ancestor')
   wanted=(os.major(s.st_dev),os.minor(s.st_dev),s.st_ino)
   owned=False
   for line in Path('/proc/locks').read_text().splitlines():
    fields=line.split()
    if len(fields)<8 or fields[1:4]!=['FLOCK','ADVISORY','WRITE'] or fields[4]!=str(owner):continue
    major,minor,inode=fields[5].split(':')
    if (int(major,16),int(minor,16),int(inode))==wanted:owned=True
   if not owned:raise ValueError('invocation does not own exact native lock')
   if not any((os.stat(entry).st_dev,os.stat(entry).st_ino)==(s.st_dev,s.st_ino) for entry in Path('/proc/'+str(owner)+'/fd').iterdir()):raise ValueError('owner descriptor missing')

 finally:os.close(fd)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--token',required=True);p.add_argument('--receipt',required=True);p.add_argument('--inputs');p.add_argument('--ca');p.add_argument('--prepare',action='store_true');p.add_argument('--require-locked',action='store_true');p.add_argument('--paths-only',action='store_true');a=p.parse_args()
 try:verify(a.token,a.receipt,a.inputs,a.prepare,a.require_locked,a.paths_only,a.ca)
 except (OSError,ValueError):raise SystemExit('Unsafe custody path or missing transaction lock; no API operation permitted.')
 print('Custody paths and transaction lock verified.')
