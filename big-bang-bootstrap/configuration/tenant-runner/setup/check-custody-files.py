#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'packages/gitlab/enrollment'))
from verify_group_paths import safe
try:
 if len(sys.argv)!=4:raise ValueError()
 for p in sys.argv[1:]:safe(p,limit=65536)
except (ValueError,OSError):raise SystemExit('Protected custody paths rejected')
print('Protected custody paths verified')
