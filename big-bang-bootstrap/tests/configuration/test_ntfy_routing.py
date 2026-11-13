"""Offline route/trust scope only; not live CNI or delivery proof."""
import json
from pathlib import Path
import unittest
import jinja2
import yaml

class NtfyRouting(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[2] / 'configuration/packages/ntfy/routing.yaml.j2'
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        env.filters['to_json'] = json.dumps
        self.docs = list(yaml.safe_load_all(env.from_string(path.read_text()).render(
            ntfy_namespace='fixture', ntfy_backend_server_name='ntfy.fixture.svc',
            ntfy_backend_ca_secret='backend-ca', ntfy_hostname='notify.example.test',
            ntfy_ingress_tls_secret='frontend-tls', ntfy_ingress_namespace='ingress',
            ntfy_ingress_app='controller')))

    def test_verified_https_both_hops(self):
        transport, service, ingress, _ = self.docs
        self.assertFalse(transport['spec']['insecureSkipVerify'])
        self.assertEqual(transport['spec']['serverName'], 'ntfy.fixture.svc')
        self.assertEqual(transport['spec']['rootCAs'], [{'secret':'backend-ca'}])
        annotations = service['metadata']['annotations']
        self.assertEqual(annotations['traefik.ingress.kubernetes.io/service.serversscheme'], 'https')
        self.assertEqual(annotations['traefik.ingress.kubernetes.io/service.serverstransport'], 'fixture-ntfy-tls@kubernetescrd')
        self.assertEqual(ingress['spec']['tls'][0]['hosts'], ['notify.example.test'])
        self.assertEqual(ingress['metadata']['annotations']['traefik.ingress.kubernetes.io/router.entrypoints'], 'websecure')
        self.assertEqual(ingress['spec']['rules'][0]['http']['paths'][0]['backend']['service']['port']['number'], 8443)

    def test_ingress_peer_is_and_and_egress_denied(self):
        spec = self.docs[3]['spec']
        self.assertEqual(spec['policyTypes'], ['Ingress','Egress'])
        self.assertEqual(spec['egress'], [])
        self.assertEqual(len(spec['ingress']), 1)
        peers = spec['ingress'][0]['from']
        self.assertEqual(len(peers), 1)
        self.assertEqual(set(peers[0]), {'namespaceSelector','podSelector'})
        self.assertEqual(spec['ingress'][0]['ports'], [{'protocol':'TCP','port':8443}])
        self.assertEqual(spec['podSelector']['matchLabels'], {'app.kubernetes.io/name':'ntfy'})
