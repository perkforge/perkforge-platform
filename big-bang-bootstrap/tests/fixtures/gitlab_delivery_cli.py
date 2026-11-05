#!/usr/bin/env python3
"""Synthetic Secret API CLI for local tests only; never runs kubectl or a server."""
import base64,json,os,sys
from pathlib import Path
p=Path(os.environ['GITLAB_DELIVERY_TEST_STATE']);s=json.loads(p.read_text());a=sys.argv[1:]
if 'config' in a:print(s['api'],end='');sys.exit()
if 'get' in a:
 i=a.index('get');kind,name=a[i+1:i+3]
 if kind=='namespace':print(s['uid'],end='');sys.exit()
 if kind not in ('secret','configmap'):sys.exit(3)
 namespace=a[a.index('-n')+1];key=namespace+'/'+name
 if key in s['objects']:print(json.dumps(s['objects'][key]),end='')
 elif '--ignore-not-found' not in a:sys.exit(1)
 sys.exit()
if 'create' in a:
 if len(s['objects'])>=s.get('fail_after',999):sys.exit(7)
 o=json.load(sys.stdin);key=o['metadata']['namespace']+'/'+o['metadata']['name']
 if key in s['objects']:sys.exit(4)
 if 'stringData' in o:o['data']={k:base64.b64encode(v.encode()).decode() for k,v in o.pop('stringData').items()}
 o['metadata']['uid']='synthetic-'+str(len(s['objects']));o['metadata']['resourceVersion']=str(len(s['objects'])+1)
 s['objects'][key]=o;p.write_text(json.dumps(s));print('created');sys.exit()
sys.exit(5)
