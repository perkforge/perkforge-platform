#!/usr/bin/env python3
"""Persist bounded nonsecret phase evidence, including directory durability."""
import importlib.util,re,sys
from pathlib import Path
p=Path(__file__).with_name('bootstrap-gitlab.py');s=importlib.util.spec_from_file_location('base',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
try:
 path,setup,stage,category,disabled,ttl=sys.argv[1:]
 if disabled not in ('not-attempted','verified-disabled','unverified') or not re.fullmatch(r'unknown|[0-9]{1,10}',ttl):raise ValueError()
 if not re.fullmatch('[a-f0-9]{64}',setup) or stage not in ('ReaderAccessVerified','ManualRecovery') or category not in ('verified','preflight','foreign-probe-preflight','secret-custody','enable-owned-client','selected-read-acceptance','foreign-and-manage-denials'):raise ValueError()
 r=m.read(path)
 if r.get('setup_id')!=setup:raise ValueError()
 r.update(stage=stage,category=category,disable_result=disabled,issued_token_ttl_seconds=ttl);m.save(path,r)
except Exception:raise SystemExit('Receipt persistence unverified')
