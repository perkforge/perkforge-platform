#!/usr/bin/env python3
"""Synthetic foundation kubectl only, no networking or real kubeconfig parsing."""
import json,os,sys
from pathlib import Path
p=Path(os.environ['GITLAB_FOUNDATION_TEST_STATE']);s=json.loads(p.read_text());a=sys.argv[1:]
for flag in ('--kubeconfig','--context'):
 if flag in a:i=a.index(flag);del a[i:i+2]
kind=a[1] if len(a)>1 else '';namespace=a[a.index('-n')+1] if '-n' in a else ''
if a[0]=='get':
 key=kind+'/'+namespace+'/'+a[2];obj=s['objects'].get(key)
 if obj:print(json.dumps(obj))
 elif '--ignore-not-found' not in a:sys.exit(1)
elif a[0]=='create':
 obj=json.load(sys.stdin);key=obj['kind']+'/'+obj['metadata'].get('namespace','')+'/'+obj['metadata']['name']
 if key in s['objects']:sys.exit(1)
 s['objects'][key]=obj;s['creates'].append(key);p.write_text(json.dumps(s));print('created')
else:sys.exit(2)
