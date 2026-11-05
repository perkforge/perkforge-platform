#!/usr/bin/env python3
"""Stateful offline service/API fixture. No SSH, sudo or network calls."""
import json,os,sys
from pathlib import Path
p=Path(os.environ['API_OIDC_FIXTURE']);s=json.loads(p.read_text());a=sys.argv[1:];tool=Path(sys.argv[0]).name
if tool=='systemctl':
 if a[:2]==['restart','rke2-server']:
  s['restarts']=s.get('restarts',0)+1
  drop=Path(s['root'])/'config.yaml.d/90-perkforge-oidc-v1.yaml'
  import yaml
  s['args']=['--secure-port=6443']+(['--'+x for x in yaml.safe_load(drop.read_text())['kube-apiserver-arg+']] if drop.exists() else [])
  s['ready']=True
  if s.pop('fail_restart',False):
   s['ready']=False;p.write_text(json.dumps(s));raise SystemExit(1)
 elif a[0]=='is-active':print('active')
 elif a[0]=='cat':print(s.get('unit','ExecStart=/usr/bin/rke2 server\nEnvironment=') )
 elif a[0]=='show':print(s.get('env_paths',''))
 else:raise SystemExit('Unexpected synthetic service command')
else:
 assert 'get' in a
 if '--raw=/readyz' in a:
  if not s.get('ready',True):raise SystemExit(1)
  print('ok')
 elif 'namespace' in a:
  if not s.get('ready',True):raise SystemExit(1)
  print(s.get('uid','fixture-uid'))
 elif 'pods' in a:
  print(json.dumps({'items':[{'spec':{'containers':[{'args':s.get('args',[]),'volumeMounts':[{'mountPath':s['root']+'/identity/ca.crt','readOnly':True}]}]}}]}))
 elif 'nodes' in a:print(json.dumps({'items':[{'metadata':{'name':'control-1'},'status':{'conditions':[{'type':'Ready','status':'True'}]}}]}))
 else:raise SystemExit('Unexpected synthetic API request')
p.write_text(json.dumps(s))
