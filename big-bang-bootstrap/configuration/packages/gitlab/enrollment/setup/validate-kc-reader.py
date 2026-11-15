#!/usr/bin/env python3
"""Literal setup selection and custody checks only; never calls native APIs."""
import json,os,re,sys,stat
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from verify_group_paths import safe,verify
from identity_context import derive
UUID=r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}'
def read(path):
 safe(path)
 def unique(pairs):
  result={}
  for key,value in pairs:
   if key in result:raise ValueError('duplicate key')
   result[key]=value
  return result
 before=os.lstat(path)
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  opened=os.fstat(fd)
  if (before.st_dev,before.st_ino)!=(opened.st_dev,opened.st_ino) or not stat.S_ISREG(opened.st_mode) or opened.st_uid!=os.getuid() or stat.S_IMODE(opened.st_mode)!=0o600 or opened.st_nlink!=1 or opened.st_size>65536:raise ValueError('changed or unsafe descriptor')
  with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(65537)
 finally:os.close(fd)
 if len(raw)>65536:raise ValueError('oversize')
 return json.loads(raw,object_pairs_hook=unique)
def validate(token,receipt,path,mode):
 safe(token,limit=4096);safe(receipt,optional=True);d=read(path)
 patterns={'kc_reader_context':r'[a-z][a-z0-9-]{0,30}','kc_reader_source_revision':r'[a-f0-9]{40}','kc_reader_origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?(?:/auth)?','kc_reader_realm':r'[A-Za-z0-9_-]{1,64}','kc_reader_ca_file':r'/[A-Za-z0-9_./-]+'}
 if not isinstance(d,dict) or set(d)!=set(patterns)|{'kc_reader_run','kc_reader_scope','kc_reader_group_ids','kc_reader_allow_enable_permissions'}:raise ValueError('fields')
 for key,pattern in patterns.items():
  if not isinstance(d[key],str) or not re.fullmatch(pattern,d[key]):raise ValueError('literal fields')
 if d['kc_reader_context'] in ('platform','tenants','system','default') or d['kc_reader_scope']!='canonical-group-reader-setup-v1' or d['kc_reader_run'] is not True or type(d['kc_reader_allow_enable_permissions']) is not bool:raise ValueError('scope')
 contract=derive(d['kc_reader_context'])
 groups=d['kc_reader_group_ids']
 if not isinstance(groups,dict) or set(groups)!={'tenant-admin','tenant-developer','tenant-viewer'} or any(not isinstance(v,str) or not re.fullmatch(UUID,v) for v in groups.values()) or len(set(groups.values()))!=3:raise ValueError('groups')
 safe(d['kc_reader_ca_file'],private=False,limit=262144)
 if os.path.lexists(receipt):
  r=read(receipt);binding={'schema':1,'context':d['kc_reader_context'],'source_revision':d['kc_reader_source_revision'],'origin':d['kc_reader_origin'],'realm':d['kc_reader_realm'],'group_ids':groups}
  # Only pre-contract Portal receipts have a legacy compatibility path.
  if 'context_digest' in r:binding['context_digest']=contract['digest']
  elif d['kc_reader_context']!='portal':raise ValueError('Unbound context receipt')
  ids={'reader_client_id','service_account_id','permissions_client_id','policy_id','permission_id'}
  if not isinstance(r,dict) or set(r)!=set(binding)|ids|{'stage','permissions_enable_requested','permissions_observed_enabled'} or any(r.get(k)!=v for k,v in binding.items()):raise ValueError('foreign receipt')
  if any(not isinstance(r[k],str) or not re.fullmatch('(?:'+UUID+')?',r[k]) for k in ids) or r['stage'] not in ('Prepared','PermissionsEnablePending','PermissionsEnabled','ClientCreated','PolicyCreated','PermissionCreated','PendingCustody'):raise ValueError('receipt state')
  if any(type(r[k]) is not bool for k in ('permissions_enable_requested','permissions_observed_enabled')):raise ValueError('enablement receipt flags')
 if mode not in ('--validate','--prepare','--locked'):raise ValueError('mode')
 if mode!='--validate':verify(token,receipt,prepare=mode=='--prepare',require_locked=mode=='--locked')
if __name__=='__main__':
 try:validate(*sys.argv[1:])
 except Exception:raise SystemExit('Invalid literal reader setup or protected ownership; no native request permitted.')
