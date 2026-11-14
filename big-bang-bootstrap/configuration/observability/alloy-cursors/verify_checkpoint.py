#!/usr/bin/env python3
"""Validate native cursor metadata only; never generate config or print target keys."""
import argparse,hashlib,json,time
from pathlib import Path
import yaml
from yaml.nodes import MappingNode,ScalarNode

def validate(raw):
 if not 1 <= len(raw) <= 4*1024*1024: raise ValueError('cursor size outside bound')
 node=yaml.compose(raw)
 if not isinstance(node,MappingNode) or len(node.value)!=1 or node.value[0][0].value!='positions':raise ValueError('unexpected root')
 entries=node.value[0][1]
 if not isinstance(entries,MappingNode) or not entries.value:raise ValueError('empty/nonmapping positions')
 seen=set()
 for key,value in entries.value:
  if not isinstance(key,MappingNode) or len(key.value)!=2:raise ValueError('unexpected target key')
  fields={}
  for k,v in key.value:
   if not isinstance(k,ScalarNode) or not isinstance(v,ScalarNode) or k.value in fields:raise ValueError('invalid target field')
   fields[k.value]=v.value
  if set(fields)!={'path','labels'} or not fields['path'] or len(fields['path'])>8192 or len(fields['labels'])>65536:raise ValueError('unexpected target schema')
  identity=(fields['path'],fields['labels'])
  if identity in seen:raise ValueError('duplicate target')
  seen.add(identity)
  if not isinstance(value,ScalarNode) or not value.value.isdecimal() or int(value.value)<0 or int(value.value)>int((time.time()+300)*1000000):raise ValueError('invalid cursor offset')
 return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'targets':len(seen)}

def main():
 p=argparse.ArgumentParser();p.add_argument('file');p.add_argument('--capture-time',type=int,required=True);p.add_argument('--source-mtime',type=int,required=True);p.add_argument('--expected-hash');a=p.parse_args()
 now=int(time.time())
 if not 0 <= now-a.capture_time <= 600 or not 0 <= a.capture_time-a.source_mtime <=60:raise ValueError('checkpoint capture stale or source file not freshly synced')
 d=validate(Path(a.file).read_bytes())
 if a.expected_hash and d['sha256']!=a.expected_hash:raise ValueError('checkpoint digest mismatch')
 print(json.dumps(d))
if __name__=='__main__':
 try:main()
 except Exception:raise SystemExit('Checkpoint verification failed; contents withheld')
