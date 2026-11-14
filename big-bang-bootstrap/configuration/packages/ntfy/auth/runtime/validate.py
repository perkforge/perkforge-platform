"""Verification adapter only; configuration assembly remains in Ansible/YAML."""
import importlib.util
import json
from pathlib import Path
import sys
spec = importlib.util.spec_from_file_location('ntfy_guard', Path(__file__).parents[1] / 'verify_inputs.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
try:
    guard.verify(**json.loads(Path(sys.argv[1]).read_text()))
except Exception:
    raise SystemExit('Invalid ntfy runtime inputs; values suppressed') from None
