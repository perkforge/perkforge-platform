#!/usr/bin/env python3
"""Verify only literal render inputs and private output custody; no generation/API."""
import sys,re,json,os,ipaddress
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from validate import read
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from verify_group_paths import safe
from identity_context import derive

def check(path):
 d=read(path)
 if not isinstance(d,dict) or set(d) not in ({'context','gitlab_origin','output_directory'},{'context','gitlab_origin','output_directory','runtime'}):raise ValueError()
 if 'runtime' in d:
  v=d['runtime']
  if not isinstance(v,dict) or set(v)!={'bao_server','route_hosts','api_host','api_port','traefik_port'}:raise ValueError()
  if not isinstance(v['bao_server'],str) or not re.fullmatch(r'https://[a-z0-9.-]+(?::[0-9]+)?',v['bao_server']):raise ValueError()
  if type(v['route_hosts']) is not list or not 1<=len(v['route_hosts'])<=8:raise ValueError()
  for h in v['route_hosts']+[v['api_host']]:
   if type(h) is not str:raise ValueError()
   n=ipaddress.ip_network(h,strict=True)
   if str(n)!=h:raise ValueError()
   if n.prefixlen!=n.max_prefixlen or n.network_address.is_unspecified or n.network_address.is_multicast or n.network_address.is_loopback:raise ValueError()
  if len(set(v['route_hosts']))!=len(v['route_hosts']):raise ValueError()
  if v['api_host'] in v['route_hosts'] and v['api_port']==443:raise ValueError()
  for k in ('api_port','traefik_port'):
   if type(v[k]) is not int or not 1<=v[k]<=65535:raise ValueError()
 if type(d['context']) is not str:raise ValueError()
 derive(d['context'])
 if not isinstance(d['gitlab_origin'],str) or not re.fullmatch(r'https://[a-z0-9.-]+(?::[0-9]+)?',d['gitlab_origin']):raise ValueError()
 if not isinstance(d['output_directory'],str) or not re.fullmatch(r'/[A-Za-z0-9_./-]+',d['output_directory']):raise ValueError()
 for name in ('foundation.yaml','release.yaml','runtime.yaml','runner-policy.hcl'):
  p=d['output_directory']+'/'+name;safe(p,optional=True,limit=131072)
  if os.path.lexists(p):raise ValueError('Use a fresh private output directory; no replacement')
 return d
if __name__=='__main__':
 try:
  if len(sys.argv)!=2:raise ValueError()
  check(sys.argv[1])
 except (ValueError,OSError,KeyError,TypeError):raise SystemExit('Manager render preflight rejected')
 print('Manager literal inputs verified')
