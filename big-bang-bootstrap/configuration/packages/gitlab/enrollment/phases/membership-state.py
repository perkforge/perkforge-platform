#!/usr/bin/env python3
"""Validate protected prior ownership metadata, never decide native permissions."""
import json,re,sys
from pathlib import Path
from contract import inputs,envelope,read,safe,age,UUID,ROLES

def verify(input_file,work,group_file):
 d=inputs(input_file,'memberships');e=envelope(d,work+'/envelope.json');g=read(group_file)
 if Path(group_file).name!='gitlab-group.json' or Path(group_file).parent.name!=d['identity_context']:raise ValueError('stable context group receipt')
 expected={'schema':1,'origin':d['identity_gitlab_origin'],'context':d['identity_context'],'source_revision':d['identity_source_revision'],'stage':'group-ready'}
 if not isinstance(g,dict) or set(g)!=set(expected)|{'parent_id','group_id','previous_revisions'} or any(g.get(k)!=v for k,v in expected.items()):raise ValueError('group binding')
 if any(type(g[k]) is not int or not 0<g[k]<2**63 for k in ('parent_id','group_id')):raise ValueError('native IDs')
 if not isinstance(g['previous_revisions'],list) or len(g['previous_revisions'])>32 or any(not isinstance(x,str) or not re.fullmatch('[a-f0-9]{40}',x) for x in g['previous_revisions']):raise ValueError('group history')
 foundation=read(str(Path(group_file).parent/'foundation-result.json'))
 expected_foundation={'schema':1,'phase':'GroupReady','context':d['identity_context'],'invocation':d['identity_invocation'],'source_revision':d['identity_source_revision'],'platform_revision':d['identity_platform_revision'],'parent_id':g['parent_id'],'group_id':g['group_id']}
 if not isinstance(foundation,dict) or set(foundation)!=set(expected_foundation)|{'captured_at'} or any(foundation.get(k)!=v for k,v in expected_foundation.items()):raise ValueError('fresh invocation foundation required')
 age(foundation['captured_at'])
 prior=[]
 for p in sorted(Path(group_file).parent.glob('gitlab-member-*.json')):
  if len(prior)>=3:raise ValueError('pilot prior receipt cap')
  r=read(str(p));base={'schema':1,'origin':d['identity_gitlab_origin'],'context':d['identity_context'],'group_id':g['group_id']}
  if not isinstance(r,dict) or any(r.get(k)!=v for k,v in base.items()) or r.get('stage') not in ('GrantPending','Granted','Revoked'):raise ValueError('foreign ownership')
  keys=set(base)|{'subject','source_revision','native_user_id','role','access_level','stage'}|({'attempted_at'} if r['stage']=='GrantPending' else set())
  if set(r)!=keys or not isinstance(r['subject'],str) or not re.fullmatch(UUID,r['subject']) or p.name!='gitlab-member-'+r['subject']+'.json':raise ValueError('prior subject')
  if not isinstance(r['source_revision'],str) or not re.fullmatch('[a-f0-9]{40}',r['source_revision']):raise ValueError('prior revision')
  if type(r['native_user_id']) is not int or not 0<r['native_user_id']<2**63 or r['role'] not in ROLES or type(r['access_level']) is not int or r['access_level']!={'tenant-admin':50,'tenant-developer':30,'tenant-viewer':20}[r['role']]:raise ValueError('prior identity/role')
  # Pending timestamps are checked by the actual writer before native requests.
  if r['stage']=='GrantPending' and not isinstance(r['attempted_at'],str):raise ValueError('pending timestamp')
  prior.append(r)
 subjects=sorted(set(x['subject'] for x in e['snapshot']['members'])|set(x['subject'] for x in prior))
 if len(subjects)>3:raise ValueError('pilot union cap')
 return {'group':g,'prior':prior,'subjects':subjects}
if __name__=='__main__':
 try:print(json.dumps(verify(*sys.argv[1:]),sort_keys=True))
 except Exception:raise SystemExit('Invalid protected membership state; no native changes permitted.')
