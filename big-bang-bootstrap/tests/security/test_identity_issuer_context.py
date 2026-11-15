"""Context binding is source authority, not a live credential acceptance test."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SETUP = Path(__file__).resolve().parents[2] / 'configuration/packages/gitlab/enrollment/setup'
spec = importlib.util.spec_from_file_location('issuer_context_state', SETUP / 'issuer-state.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Context(unittest.TestCase):
    def receipt(self, context='orchard'):
        c = m.derive(context)
        return {'schema': 2, 'setup_id': 'a' * 64, 'stage': 'Requesting-keycloak',
                'accessors': {}, 'revoked': [], 'identity_context': context,
                'context_digest': c['digest']}

    def test_context_digest_and_legacy(self):
        r = self.receipt()
        self.assertEqual(m.binding(r)['context'], 'orchard')
        with self.assertRaises(ValueError):
            m.binding(r, 'portal')
        r['context_digest'] = 'b' * 64
        with self.assertRaises(ValueError):
            m.binding(r)
        legacy = {k: v for k, v in self.receipt('portal').items()
                  if k not in ('identity_context', 'context_digest')}
        legacy['schema'] = 1
        self.assertEqual(m.binding(legacy, 'portal')['context'], 'portal')
        with self.assertRaises(ValueError):
            m.binding(legacy, 'orchard')

    def test_policy_crossing_never_persists_token(self):
        with tempfile.TemporaryDirectory() as td:
            receipt = Path(td) / 'receipt'
            receipt.write_text(json.dumps(self.receipt()))
            receipt.chmod(0o600)
            auth = {'accessor': 'FAKE-ACCESSOR', 'policies': [m.derive('portal')['bootstrap_policy']],
                    'identity_policies': [], 'renewable': False, 'lease_duration': 3600,
                    'client_token': 'FAKE-TOKEN-UNISSUED'}
            with self.assertRaises(ValueError):
                m.persist_token(str(receipt), 'a' * 64, 'keycloak', {'auth': auth})
            self.assertFalse((Path(td) / 'keycloak-setup-token').exists())
            # Accessor evidence is retained, but cleanup still requires the
            # actual exact derived policy and display-name native readback.
            self.assertEqual(json.loads(receipt.read_text())['accessors']['keycloak'], 'FAKE-ACCESSOR')

    def test_explicit_new_context_and_legacy_cleanup_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            token, receipt, inputs, ca = (root / x for x in ('token', 'receipt', 'inputs', 'ca'))
            for p in (token, ca):
                p.write_text('SYNTHETIC')
                p.chmod(0o600)
            d = {'run': True, 'scope': 'identity-custody-issuer-v1', 'setup_id': 'a' * 64,
                 'bao_origin': 'https://bao.example.test', 'ca_file': str(ca),
                 'cluster_id': '11111111-1111-4111-8111-111111111111'}
            def save():
                inputs.write_text(json.dumps(d)); inputs.chmod(0o600)
            save()
            with self.assertRaises(ValueError):
                m.inputs(str(token), str(receipt), str(inputs))
            legacy = {k: v for k, v in self.receipt('portal').items()
                      if k not in ('identity_context', 'context_digest')}
            legacy['schema'] = 1
            receipt.write_text(json.dumps(legacy)); receipt.chmod(0o600)
            self.assertEqual(m.inputs(str(token), str(receipt), str(inputs), True)['identity_context'], 'portal')
            d['identity_context'] = 'orchard'; save()
            with self.assertRaises(ValueError):
                m.inputs(str(token), str(receipt), str(inputs), True)


if __name__ == '__main__':
    unittest.main()
