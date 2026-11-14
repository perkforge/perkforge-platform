#!/usr/bin/env python3
"""Validate literal metadata and shared context lock before Ansible interpretation."""
import argparse,json,os,re,sys,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'enrollment'))
from verify_group_paths import safe,verify

def read_json(path):
 safe(path)
 def unique(pairs):
  result={}
  for k,v in pairs:
   if k in result:raise ValueError('duplicate field')
   result[k]=v
  return result
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(65537)
 finally:os.close(fd)
 if len(raw)>65536:raise ValueError('oversize')
 return json.loads(raw,object_pairs_hook=unique)

def validate(writer,evidence,receipt,inputs,grant,locked=False,prepare=False):
 safe(writer,limit=4096);safe(receipt,limit=4096);safe(grant,optional=True,limit=4096)
 d=read_json(inputs);r=read_json(receipt)
 keys={'gitlab_membership_run','gitlab_membership_scope','gitlab_membership_operation','gitlab_membership_recovery_verified','gitlab_membership_context','gitlab_membership_source_revision','gitlab_native_origin','gitlab_native_ca_file','gitlab_native_user_id','gitlab_native_subject','gitlab_native_group_id','gitlab_native_group_path','gitlab_native_access_level','gitlab_native_role'}
 if not isinstance(d,dict) or set(d)!=keys:raise ValueError('input fields')
 if d['gitlab_membership_run'] is not True or d['gitlab_membership_recovery_verified'] is not True:raise ValueError('explicit execution required')
 op=d['gitlab_membership_operation']
 if op not in ('inspect','grant','revoke') or d['gitlab_membership_scope']!='gitlab-membership-'+op+'-v1':raise ValueError('operation')
 patterns={'gitlab_membership_context':r'[a-z][a-z0-9-]{0,30}','gitlab_membership_source_revision':r'[0-9a-f]{40}','gitlab_native_origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?','gitlab_native_ca_file':r'/[A-Za-z0-9_./-]+','gitlab_native_subject':r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}','gitlab_native_group_path':r'tenants/[a-z][a-z0-9-]{0,30}'}
 for k,p in patterns.items():
  if not isinstance(d[k],str) or not re.fullmatch(p,d[k]):raise ValueError('nonliteral input')
 if d['gitlab_membership_context'] in ('platform','system','default','tenants'):raise ValueError('reserved context')
 for k in ('gitlab_native_user_id','gitlab_native_group_id'):
  if type(d[k]) is not int or not 0<d[k]<2**63:raise ValueError('invalid native ID')
 roles={'tenant-admin':50,'tenant-developer':30,'tenant-viewer':20}
 if d['gitlab_native_role'] not in roles or type(d['gitlab_native_access_level']) is not int or d['gitlab_native_access_level']!=roles[d['gitlab_native_role']]:raise ValueError('role mismatch')
 if d['gitlab_native_group_path']!='tenants/'+d['gitlab_membership_context']:raise ValueError('context mismatch')
 if grant!=str(Path(receipt).parent/('gitlab-member-'+d['gitlab_native_subject']+'.json')) or grant in (writer,evidence,receipt,inputs):raise ValueError('stable owned grant path required')
 if not isinstance(r,dict) or type(r.get('parent_id')) is not int or r['parent_id']<=0:raise ValueError('invalid receipt object')
 if any(r.get(k)!=v for k,v in {'schema':1,'context':d['gitlab_membership_context'],'origin':d['gitlab_native_origin'],'source_revision':d['gitlab_membership_source_revision'],'group_id':d['gitlab_native_group_id'],'stage':'group-ready'}.items()):raise ValueError('unverified group receipt')
 binding={'schema':1,'origin':d['gitlab_native_origin'],'context':d['gitlab_membership_context'],'subject':d['gitlab_native_subject'],'native_user_id':d['gitlab_native_user_id'],'group_id':d['gitlab_native_group_id'],'role':d['gitlab_native_role'],'access_level':d['gitlab_native_access_level']}
 if op in ('grant','inspect'):
  a=read_json(evidence)
  expected={'schema':1,'origin':d['gitlab_native_origin'],'context':d['gitlab_membership_context'],'subject':d['gitlab_native_subject'],'source_revision':d['gitlab_membership_source_revision'],'native_user_id':d['gitlab_native_user_id'],'stage':'IdentityVerified'}
  if not isinstance(a,dict) or set(a)!=set(expected)|{'captured_at'} or any(a.get(k)!=v for k,v in expected.items()):raise ValueError('unverified identity attestation')
  t=dt.datetime.fromisoformat(a['captured_at'])
  if t.tzinfo is None or not 0<=(dt.datetime.now(dt.timezone.utc)-t).total_seconds()<=300:raise ValueError('stale identity attestation')
 if os.path.lexists(grant):
  g=read_json(grant)
  if not isinstance(g,dict) or any(g.get(k)!=v for k,v in binding.items()) or g.get('stage') not in ('GrantPending','Granted','Revoked'):raise ValueError('foreign prior grant')
  if not re.fullmatch(r'[a-f0-9]{40}',g.get('source_revision','')):raise ValueError('prior grant revision')
  if g['stage']=='GrantPending':
   t=dt.datetime.fromisoformat(g['attempted_at'])
   if t.tzinfo is None or not 0<=(dt.datetime.now(dt.timezone.utc)-t).total_seconds()<=300:raise ValueError('pending grant requires manual recovery')
 elif op=='revoke':raise ValueError('owned prior grant required')
 safe(d['gitlab_native_ca_file'],limit=262144,private=False)
 verify(writer,receipt,prepare=prepare,require_locked=locked)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('writer');p.add_argument('evidence');p.add_argument('receipt');p.add_argument('inputs');p.add_argument('grant');p.add_argument('--locked',action='store_true');p.add_argument('--prepare',action='store_true');a=p.parse_args()
 try:validate(a.writer,a.evidence,a.receipt,a.inputs,a.grant,a.locked,a.prepare)
 except (ValueError,OSError,TypeError,KeyError):raise SystemExit('Invalid protected membership inputs or context lock; no API access permitted.')
