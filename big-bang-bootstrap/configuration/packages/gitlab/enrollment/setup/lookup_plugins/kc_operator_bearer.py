"""Read a private bearer afresh for each request, never cache it in a fact."""
import importlib.util
from pathlib import Path
from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError
class LookupModule(LookupBase):
 def run(self,terms,variables=None,**kwargs):
  try:
   if len(terms)!=1:raise ValueError()
   path=Path(__file__).resolve().parents[1]/'operator-bearer.py'
   spec=importlib.util.spec_from_file_location('operator_bearer',path)
   module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
   return [module.read_bearer(terms[0])]
  except Exception:raise AnsibleError('Operator bearer unavailable, unsafe, or near expiry') from None
