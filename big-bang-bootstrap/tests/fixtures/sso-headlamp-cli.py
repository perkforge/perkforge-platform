#!/usr/bin/env python3
"""Stateful synthetic Kubernetes CLI, never invokes another tool or network."""
import json,os,sys
from pathlib import Path
p=Path(os.environ['HEADLAMP_FIXTURE_STATE']);s=json.loads(p.read_text());a=sys.argv[1:]
v=next(x for x in a if x in ('get','create','delete'));s.setdefault('events',[]).append(v)
if v=='get':
 r=a[a.index(v)+1:];kind=r[0].lower()
 if kind=='namespace':print(s.get('uid','fixture-cluster'))
 elif kind=='pods':print(json.dumps(s['apiPods']))
 elif kind=='deployment':print(json.dumps(s['deployment']))
 else:
  obj=s['objects'].get(kind+'/'+r[1])
  if obj is None:
   if '--ignore-not-found' not in a:raise SystemExit('Synthetic missing object')
  else:print(json.dumps(obj))
elif v=='create':
 obj=json.load(sys.stdin);key=obj['kind'].lower()+'/'+obj['metadata']['name']
 assert key not in s['objects']
 if obj['kind']=='ConfigMap' and s.get('failCA'):
  p.write_text(json.dumps(s));raise SystemExit('Synthetic delivery interruption')
 obj['metadata'].update(uid='fixture-uid',resourceVersion='fixture-version');s['objects'][key]=obj;s.setdefault('writes',[]).append(('create',key));print('created')
else:
 assert '--raw=/apis/rbac.authorization.k8s.io/v1/clusterrolebindings/perkforge-sso-platform-admins' in a
 body=json.load(sys.stdin);assert body['preconditions']=={'uid':'fixture-uid','resourceVersion':'fixture-version'}
 key='clusterrolebinding/perkforge-sso-platform-admins';del s['objects'][key];s.setdefault('writes',[]).append(('delete',key));print('{}')
p.write_text(json.dumps(s))
