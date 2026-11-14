#!/usr/bin/env python3
"""Validate only the fixed private staging interface before loading Ansible."""
import os,re,sys
from pathlib import Path
from contract import inputs,safe

def validate(phase,input_file,work):
 if phase not in ('attest','memberships') or not re.fullmatch(r'/[A-Za-z0-9_./-]+',work) or str(Path(work))!=work:raise ValueError('stage')
 if input_file!=work+'/phase-inputs.json':raise ValueError('fixed input path')
 inputs(input_file,phase)
 names=['gitlab-reader','kc-client-id','kc-client-secret','lab-ca.crt','api-token','api-ca.crt'] if phase=='attest' else ['group-writer','lab-ca.crt','envelope.json']
 for name in names:safe(work+'/'+name,limit=262144 if name.endswith('.crt') or name=='envelope.json' else 4096)
 for name in ['run.log','result.json','snapshot-inputs.json','snapshot.json','kc-token','subject-inputs.json']+(['envelope.json'] if phase=='attest' else []):
  if os.path.lexists(work+'/'+name):raise ValueError('fresh phase work required')
 if phase=='attest':
  client=Path(work+'/kc-client-id').read_text().strip()
  if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',client):raise ValueError('client binding')
if __name__=='__main__':
 try:validate(*sys.argv[1:])
 except Exception:raise SystemExit('Invalid phase staging; no credential use permitted.')
 print('Private phase staging verified.')
