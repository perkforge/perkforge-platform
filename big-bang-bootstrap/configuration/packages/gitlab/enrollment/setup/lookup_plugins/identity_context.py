"""Read-only shared literal context contract lookup."""
import importlib.util
from pathlib import Path
from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError
P = Path(__file__).resolve().parents[2] / 'identity_context.py'
spec = importlib.util.spec_from_file_location('identity_context_contract', P)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)
class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        if len(terms) != 1:
            raise AnsibleError('Exactly one selected context required')
        try:
            return [contract.derive(terms[0])]
        except ValueError as exc:
            raise AnsibleError('Invalid selected identity context') from exc
