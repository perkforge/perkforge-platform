#!/usr/bin/env python3
"""Stateful route fixture; public certificate only, never private TLS contents."""
import base64,json,os,sys
from pathlib import Path
p=Path(os.environ['HEADLAMP_ROUTE_FIXTURE']);s=json.loads(p.read_text());a=sys.argv[1:];v=next(x for x in a if x in ('get','create','delete'));s.setdefault('events',[]).append(a)
if v=='get':
 r=a[a.index(v)+1:]
 if r[0]=='namespace':print(s.get('uid','fixture-uid'))
 elif r[0]=='secret':
  assert r[1]=='headlamp-local-tls' and 'tls\\.crt' in a[-1] and 'tls.key' not in a[-1]
  print('kubernetes.io/tls\n'+base64.b64encode(s['certificate'].encode()).decode())
 elif r[0]=='service':print(json.dumps({'spec':{'ports':[{'port':4466}]}}))
 else:
  assert r[:2]==['ingress','headlamp-identity'];o=s['objects'].get('headlamp-identity')
  if o:print(json.dumps(o))
elif v=='create':
 o=json.load(sys.stdin);assert o['kind']=='Ingress' and o['metadata']['namespace']=='headlamp' and o['metadata']['name']=='headlamp-identity';assert 'headlamp-identity' not in s['objects']
 o['metadata'].update(uid='route-uid',resourceVersion='7');s['objects']['headlamp-identity']=o;s.setdefault('writes',[]).append('create')
else:
 assert '--raw=/apis/networking.k8s.io/v1/namespaces/headlamp/ingresses/headlamp-identity' in a
 body=json.load(sys.stdin);o=s['objects']['headlamp-identity'];assert body['preconditions']=={'uid':o['metadata']['uid'],'resourceVersion':o['metadata']['resourceVersion']}
 if s.get('deleteConflict'):p.write_text(json.dumps(s));raise SystemExit('Synthetic conflict, no deletion')
 del s['objects']['headlamp-identity'];s.setdefault('writes',[]).append('delete')
p.write_text(json.dumps(s))
