#!/usr/bin/env python3
"""Literal finite-phase contract validation; no native mutation or credential output."""
import argparse,datetime as dt,hashlib,json,os,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from verify_group_paths import safe
from identity_context import derive
UUID=r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}'
ROLES={'tenant-admin','tenant-developer','tenant-viewer'}
def unique(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise ValueError('duplicate key')
  d[k]=v
 return d
def read(path):
 safe(path,limit=262144)
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(262145)
 finally:os.close(fd)
 if len(raw)>262144:raise ValueError('oversize')
 return json.loads(raw,object_pairs_hook=unique)
def age(value):
 t=dt.datetime.fromisoformat(value)
 if t.tzinfo is None or not 0<=(dt.datetime.now(dt.timezone.utc)-t).total_seconds()<=300:raise ValueError('stale evidence')
def inputs(path,phase):
 d=read(path)
 patterns={'identity_context':r'[a-z][a-z0-9-]{0,30}','identity_source_revision':r'[a-f0-9]{40}','identity_platform_revision':r'[a-f0-9]{40}','identity_contract_sha256':r'[a-f0-9]{64}','identity_invocation':r'[a-f0-9]{64}','identity_previous_invocation':r'(?:[a-f0-9]{64})?','identity_gitlab_origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?','identity_keycloak_origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?(?:/auth)?','identity_keycloak_realm':r'[A-Za-z0-9_-]{1,64}','identity_kubernetes_origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?','identity_receipt_uid':UUID,'identity_receipt_namespace':r'[a-z][a-z0-9-]{0,62}','identity_receipt_name':r'[a-z][a-z0-9-]{0,30}-identity-evidence'}
 if isinstance(d,dict) and 'identity_context_digest' in d:patterns['identity_context_digest']=r'[a-f0-9]{64}'
 if not isinstance(d,dict) or set(d)!=set(patterns)|{'identity_run','identity_scope','identity_retry_generation','identity_group_ids','identity_membership_recovery_verified'}:raise ValueError('unexpected fields')
 for k,p in patterns.items():
  if not isinstance(d[k],str) or not re.fullmatch(p,d[k]):raise ValueError('nonliteral field')
 if type(d['identity_membership_recovery_verified']) is not bool or (phase=='memberships' and d['identity_membership_recovery_verified'] is not True):raise ValueError('recovery prerequisite')
 if phase not in ('attest','memberships') or d['identity_run'] is not True or d['identity_scope']!='gitlab-identity-'+phase+'-v1':raise ValueError('phase scope')
 selected=derive(d['identity_context'])
 if d['identity_receipt_namespace']!=selected['writer_namespace'] or d['identity_receipt_name']!=selected['evidence_name']:raise ValueError('context binding')
 if d.get('identity_context_digest')!=selected['digest'] and not (d['identity_context']=='portal' and 'identity_context_digest' not in d):raise ValueError('context digest')
 if type(d['identity_retry_generation']) is not int or not 0<=d['identity_retry_generation']<=1000000:raise ValueError('retry generation')
 if d['identity_previous_invocation']=='' and d['identity_retry_generation']!=0:raise ValueError('prior attempt required')
 g=d['identity_group_ids']
 if not isinstance(g,dict) or set(g)!=ROLES or any(not isinstance(v,str) or not re.fullmatch(UUID,v) for v in g.values()) or len(set(g.values()))!=3:raise ValueError('group IDs')
 material={k:v for k,v in d.items() if k not in ('identity_invocation','identity_scope','identity_run')}
 expected=hashlib.sha256(json.dumps(material,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 if expected!=d['identity_invocation']:raise ValueError('invocation digest')
 return d
def envelope(d,path):
 e=read(path)
 binding={'schema':1,'context':d['identity_context'],'source_revision':d['identity_source_revision'],'platform_revision':d['identity_platform_revision'],'contract_sha256':d['identity_contract_sha256'],'invocation':d['identity_invocation'],'previous_invocation':d['identity_previous_invocation'],'retry_generation':d['identity_retry_generation'],'receipt_uid':d['identity_receipt_uid']}
 if 'identity_context_digest' in d:binding['context_digest']=d['identity_context_digest']
 if not isinstance(e,dict) or set(e)!=set(binding)|{'captured_at','snapshot','identities'} or any(e.get(k)!=v for k,v in binding.items()):raise ValueError('envelope binding')
 age(e['captured_at']);s=e['snapshot']
 sb={'schema':1,'stage':'SnapshotVerified','context':binding['context'],'source_revision':binding['source_revision'],'contract_sha256':binding['contract_sha256'],'origin':d['identity_keycloak_origin']}
 if not isinstance(s,dict) or set(s)!=set(sb)|{'realm','captured_at','groups','members'} or any(s.get(k)!=v for k,v in sb.items()):raise ValueError('snapshot binding')
 if s['realm']!=d['identity_keycloak_realm']:raise ValueError('realm binding')
 age(s['captured_at'])
 expected_groups=[{'role':r,'id':d['identity_group_ids'][r],'path':'/tenants/'+binding['context']+'/'+{'tenant-admin':'admins','tenant-developer':'developers','tenant-viewer':'viewers'}[r]} for r in sorted(ROLES)]
 if s['groups']!=expected_groups or not isinstance(s['members'],list) or len(s['members'])>3:raise ValueError('bounded complete snapshot')
 members={}
 for m in s['members']:
  if not isinstance(m,dict) or set(m)!={'subject','role','enabled'} or not isinstance(m['subject'],str) or not re.fullmatch(UUID,m['subject']) or m['role'] not in ROLES or type(m['enabled']) is not bool or m['subject'] in members:raise ValueError('snapshot member')
  members[m['subject']]=m
 if not isinstance(e['identities'],list) or len(e['identities'])!=sum(m['enabled'] for m in members.values()):raise ValueError('complete identity set')
 seen=set()
 for a in e['identities']:
  ab={'schema':1,'origin':d['identity_gitlab_origin'],'context':binding['context'],'source_revision':binding['source_revision']}
  if not isinstance(a,dict) or any(a.get(k)!=v for k,v in ab.items()) or a.get('stage') not in ('IdentityVerified','PendingFirstLogin','PendingAccountApproval'):raise ValueError('identity binding')
  keys=set(ab)|{'subject','stage','captured_at'}|({'native_user_id'} if a['stage']=='IdentityVerified' else set())
  if set(a)!=keys or a['subject'] not in members or not members[a['subject']]['enabled'] or a['subject'] in seen:raise ValueError('identity selection')
  if a['stage']=='IdentityVerified' and (type(a['native_user_id']) is not int or not 0<a['native_user_id']<2**63):raise ValueError('native ID')
  age(a['captured_at']);seen.add(a['subject'])
 return e
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',required=True);p.add_argument('--inputs',required=True);p.add_argument('--envelope');a=p.parse_args()
 try:
  d=inputs(a.inputs,a.phase)
  if a.envelope:envelope(d,a.envelope)
 except Exception:raise SystemExit('Invalid or stale phase evidence; no authority to continue.')
 print('Finite phase contract verified; runtime issuer custody remains required.')
