#!/usr/bin/env python3
"""Reuse the reviewed exact Linux lock-owner proof for the whole writer phase."""
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from verify_group_paths import verify
if __name__=='__main__':
 try:
  mode,work,group=sys.argv[1:]
  if mode not in ('--prepare','--locked') or Path(group).name!='gitlab-group.json':raise ValueError('lock arguments')
  os.environ['PERKFORGE_GROUP_LOCK_OWNER']=os.environ.get('PERKFORGE_PHASE_LOCK_OWNER','0')
  verify(work+'/group-writer',str(Path(group).parent/'trigger'),prepare=mode=='--prepare',require_locked=mode=='--locked')
 except Exception:raise SystemExit('Missing or foreign whole-context phase lock; no native changes permitted.')
