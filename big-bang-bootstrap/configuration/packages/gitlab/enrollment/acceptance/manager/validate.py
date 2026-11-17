#!/usr/bin/env python3
"""Verify only literal render inputs and private output custody; no generation/API."""
import sys,re,json,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from validate import read
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from verify_group_paths import safe
from identity_context import derive

def check(path):
 d=read(path)
 if not isinstance(d,dict) or set(d)!={'context','gitlab_origin','output_directory'}:raise ValueError()
 if type(d['context']) is not str:raise ValueError()
 derive(d['context'])
 if not isinstance(d['gitlab_origin'],str) or not re.fullmatch(r'https://[a-z0-9.-]+(?::[0-9]+)?',d['gitlab_origin']):raise ValueError()
 if not isinstance(d['output_directory'],str) or not re.fullmatch(r'/[A-Za-z0-9_./-]+',d['output_directory']):raise ValueError()
 for name in ('foundation.yaml','release.yaml'):
  p=d['output_directory']+'/'+name;safe(p,optional=True,limit=131072)
  if os.path.lexists(p):raise ValueError('Use a fresh private output directory; no replacement')
 return d
if __name__=='__main__':
 try:
  if len(sys.argv)!=2:raise ValueError()
  check(sys.argv[1])
 except (ValueError,OSError,KeyError,TypeError):raise SystemExit('Manager render preflight rejected')
 print('Manager literal inputs verified')
