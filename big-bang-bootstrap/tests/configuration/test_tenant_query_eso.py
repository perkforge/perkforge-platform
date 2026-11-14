"""Focused offline render checks; no OpenBao or Kubernetes calls."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

BASE = Path(__file__).resolve().parents[2] / 'configuration/observability/tenant-query/eso'

class QueryESO(unittest.TestCase):
    def test_portable_exact_consumers_and_machine_scopes(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            values = dict(query_eso_render_enabled=True, query_eso_output_dir=directory,
                          query_eso_monitoring_namespace='metrics-adopter', query_eso_gateway_namespace='queries-adopter',
                          query_eso_server='https://bao.example.test:8200', query_eso_record_root='observability/cluster-a',
                          query_eso_kv_mount='runtime', query_eso_identity_prefix='eso-example')
            variables = folder / 'inputs.yaml'; variables.write_text(yaml.safe_dump(values))
            cmd = ['ansible-playbook', '-i', 'localhost,', str(BASE/'render.yaml'), '-e', '@'+str(variables)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            docs = list(yaml.safe_load_all((folder/'query-eso-consumers.yaml').read_text()))
            self.assertEqual(len(docs), 15)
            self.assertFalse(any(d['kind'] in ['Secret', 'ClusterSecretStore', 'ClusterRole', 'Namespace'] for d in docs))
            expected = {'monitoring': {'query-backend-tls', 'query-backend-self-client', 'grafana-query-auth'},
                        'gateway': {'query-gateway-tls', 'query-backend-client', 'portal-query-auth', 'platform-query-auth'}}
            for scope, namespace in [('monitoring', 'metrics-adopter'), ('gateway', 'queries-adopter')]:
                resources = [d for d in docs if d['metadata']['namespace'] == namespace]
                store = next(d for d in resources if d['kind'] == 'SecretStore')['spec']['provider']['vault']
                self.assertEqual(store['server'], values['query_eso_server'])
                self.assertEqual(store['path'], 'runtime')
                self.assertNotIn('namespace', store['caProvider'])
                self.assertNotIn('namespace', store['auth']['kubernetes']['serviceAccountRef'])
                role = json.loads((folder/f'eso-example-{scope}.json').read_text())
                self.assertEqual(role['bound_service_account_namespaces'], [namespace])
                self.assertEqual(role['bound_service_account_names'], [f'eso-example-{scope}'])
                self.assertEqual(role['token_policies'], [f'eso-example-{scope}'])
                self.assertTrue(role['token_no_default_policy'])
                policy = (folder/f'eso-example-{scope}.hcl').read_text()
                self.assertNotIn('*', policy)
                self.assertNotIn('metadata/', policy)
                secrets = [d for d in resources if d['kind'] == 'ExternalSecret']
                self.assertEqual({d['metadata']['name'] for d in secrets}, expected[scope])
                for secret in secrets:
                    spec = secret['spec']; name = secret['metadata']['name']
                    self.assertEqual(spec['target']['deletionPolicy'], 'Retain')
                    self.assertEqual(spec['target']['creationPolicy'], 'Orphan')
                    self.assertNotIn('dataFrom', spec)
                    for field in spec['data']:
                        path = f'observability/cluster-a/{scope}/{name}'
                        self.assertEqual(field['remoteRef']['key'], path)
                        self.assertEqual(field['remoteRef']['property'], field['secretKey'])
                        self.assertIn(f'path "runtime/data/{path}"', policy)
                    if name == 'grafana-query-auth':
                        self.assertEqual({x['secretKey'] for x in spec['data']}, {'GRAFANA_QUERY_USER', 'GRAFANA_QUERY_PASSWORD', 'GRAFANA_QUERY_CA_PEM'})
            # Reject unsafe ACL path input before creating any candidate output.
            (folder/'query-eso-consumers.yaml').unlink()
            values['query_eso_record_root'] = 'observability/*'
            variables.write_text(yaml.safe_dump(values))
            self.assertNotEqual(subprocess.run(cmd, capture_output=True, text=True).returncode, 0)
            self.assertFalse((folder/'query-eso-consumers.yaml').exists())

if __name__ == '__main__': unittest.main()
