"""Inactive package rendering; optional network-none container startup smoke."""
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
import uuid
import yaml

BASE = Path(__file__).resolve().parents[2] / 'configuration/observability/tenant-query'


def inputs(folder):
    return dict(tenant_query_render_enabled=True, tenant_query_package_enabled=True,
                tenant_query_output_dir=str(folder), runtime_dir='/tmp/gateway',
                gateway_namespace='tenant-observability', gateway_tls_secret='query-gateway-tls', upstream_client_secret='query-backend-client',
                certificate_path='/etc/gateway/tls/tls.crt', private_key_path='/etc/gateway/tls/tls.key',
                upstream_ca_path='/etc/gateway/upstream/ca.crt', upstream_client_cert_path='/etc/gateway/upstream/tls.crt', upstream_client_key_path='/etc/gateway/upstream/tls.key',
                upstream_tls_name='localhost', metrics_upstream='https://127.0.0.1:9090',
                listen_address='0.0.0.0:8443', server_name='localhost',
                platform_query={'htpasswd_path': '/etc/gateway/auth/platform/htpasswd', 'auth_secret_name': 'platform-query-auth'},
                query_contexts=[{'id': 'portal', 'namespaces': ['tenant-portal'], 'proxy_port': 18081, 'health_port': 18091, 'htpasswd_path': '/etc/gateway/auth/portal/htpasswd', 'auth_secret_name': 'portal-query-auth'}])


def render(folder, values=None):
    var = folder / 'vars.yaml'; var.write_text(yaml.safe_dump(values or inputs(folder)))
    result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(BASE / 'render.yaml'), '-e', '@' + str(var)], capture_output=True, text=True)
    if result.returncode: raise AssertionError(result.stdout + result.stderr)
    return list(yaml.safe_load_all((folder / 'deployment.yaml').read_text()))


class TenantQueryPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.tmp.cleanup)
        cls.folder = Path(cls.tmp.name)
        cls.docs = render(cls.folder)

    def test_backend_config_is_offline_opt_in_and_matches_mount_contract(self):
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(BASE / 'render-backend.yaml'), '-e', 'backend_render_enabled=true', '-e', 'backend_output_dir=' + str(self.folder)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        config = yaml.safe_load((self.folder / 'backend-config.yaml').read_text())
        self.assertEqual(config['kind'], 'ConfigMap')
        self.assertEqual(config['metadata'], {'name': 'query-backend-config', 'namespace': 'monitoring'})
        text = config['data']['nginx.conf']
        for expected in ['listen 0.0.0.0:9443 ssl;', 'ssl_verify_client on;', 'proxy_pass http://127.0.0.1:9090;', 'ssl_client_certificate /etc/query-backend/tls/ca.crt;']:
            self.assertIn(expected, text)
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(BASE / 'render-backend.yaml'), '-e', 'backend_output_dir=' + directory], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((Path(directory) / 'backend-config.yaml').exists())

    def test_only_tls_service_and_loopback_query_scope(self):
        service = self.docs[2]; pod = self.docs[3]['spec']['template']['spec']
        self.assertEqual(service['spec']['type'], 'ClusterIP')
        self.assertEqual(service['spec']['ports'], [{'name': 'https', 'port': 8443, 'targetPort': 'https'}])
        proxy = pod['containers'][1]
        self.assertIn('-insecure-listen-address=127.0.0.1:18081', proxy['args'])
        self.assertIn('-label-value=tenant-portal', proxy['args'])
        expected = yaml.safe_load((self.folder / 'proxy-arguments.yaml').read_text())[0]['arguments']
        self.assertEqual([arg for arg in proxy['args'] if not arg.startswith('-internal-listen-address=')], expected)
        self.assertNotIn('ports', proxy)
        self.assertEqual(proxy['readinessProbe']['httpGet'], {'path': '/metrics', 'port': 18091})
        self.assertFalse(pod['automountServiceAccountToken'])
        self.assertTrue(pod['securityContext']['runAsNonRoot'])
        for container in pod['containers']:
            self.assertIn('@sha256:', container['image'])
            self.assertTrue(container['securityContext']['readOnlyRootFilesystem'])
            self.assertFalse(container['securityContext']['allowPrivilegeEscalation'])
        config = self.docs[1]['data']['nginx.conf']
        self.assertIn('listen 0.0.0.0:8443 ssl;', config)
        self.assertIn('proxy_ssl_verify on;', config)
        self.assertIn('auth_basic_user_file /etc/gateway/auth/platform/htpasswd;', config)

    def test_no_credentials_or_roles_and_policy_is_narrow(self):
        self.assertEqual([d['kind'] for d in self.docs], ['ServiceAccount', 'ConfigMap', 'Service', 'Deployment', 'NetworkPolicy', 'NetworkPolicy'])
        pod = self.docs[3]['spec']['template']['spec']
        secrets = [v['secret'] for v in pod['volumes'] if 'secret' in v]
        self.assertEqual(len(secrets), 4)
        self.assertTrue(all(s['defaultMode'] == 0o440 for s in secrets))
        policy = self.docs[4]['spec']
        self.assertEqual(policy['ingress'][0]['ports'], [{'protocol': 'TCP', 'port': 8443}])
        self.assertEqual(policy['egress'][0]['ports'], [{'protocol': 'TCP', 'port': 9090}])
        backend = self.docs[5]
        self.assertEqual(backend['metadata']['namespace'], 'monitoring')
        self.assertEqual(backend['spec']['ingress'][0]['from'][0]['namespaceSelector']['matchLabels']['kubernetes.io/metadata.name'], 'tenant-observability')
        self.assertTrue(all('namespaceSelector' in peer and 'podSelector' in peer for rule in policy['egress'] for peer in rule['to']))
        kustomization = yaml.safe_load((self.folder / 'kustomization.yaml').read_text())
        self.assertEqual(kustomization['resources'], ['deployment.yaml'])
        # Native offline Kustomize composition, no kubectl API command.
        built = subprocess.run(['kubectl', 'kustomize', str(self.folder)], capture_output=True, text=True, check=True)
        self.assertEqual(len(list(yaml.safe_load_all(built.stdout))), 6)

    def test_discovery_limits_definition_ownership_not_resource_labels(self):
        spec = yaml.safe_load((BASE / 'discovery-values.yaml').read_text())['monitoring']['values']['upstream']['prometheus']['prometheusSpec']
        expected = {'serviceMonitorNamespaceSelector', 'podMonitorNamespaceSelector', 'probeNamespaceSelector', 'scrapeConfigNamespaceSelector', 'ruleNamespaceSelector'}
        self.assertEqual(set(spec), expected)
        for selector in spec.values():
            self.assertEqual(selector, {'matchLabels': {'kubernetes.io/metadata.name': 'monitoring'}})
        self.assertNotIn('overrideHonorLabels', spec)
        self.assertNotIn('enforcedNamespaceLabel', spec)

    def test_package_rejects_shared_auth_secret_and_health_port_collision(self):
        for defect in ['secret', 'health', 'invalid-name', 'invalid-context']:
            with tempfile.TemporaryDirectory() as directory:
                folder = Path(directory); values = inputs(folder)
                if defect == 'secret': values['platform_query']['auth_secret_name'] = 'portal-query-auth'
                elif defect == 'health': values['query_contexts'][0]['health_port'] = 18081
                elif defect == 'invalid-name': values['gateway_tls_secret'] = 'invalid-'
                else:
                    values['query_contexts'][0]['id'] = 'portal-'
                    values['query_contexts'][0]['htpasswd_path'] = '/etc/gateway/auth/portal-/htpasswd'
                with self.assertRaises(AssertionError): render(folder, values)
                self.assertFalse((folder / 'deployment.yaml').exists())

    @unittest.skipUnless(os.environ.get('QUERY_MONITORING_CHART') and os.environ.get('HELM_VALIDATE_BIN'), 'provide verified monitoring chart and Helm')
    def test_native_discovery_overlay_changes_only_five_selectors(self):
        chart = Path(os.environ['QUERY_MONITORING_CHART'])
        self.assertEqual(yaml.safe_load((chart / 'Chart.yaml').read_text())['version'], '91.4.1-bb.1')
        overlay = yaml.safe_load((BASE / 'discovery-values.yaml').read_text())['monitoring']['values']
        values = self.folder / 'discovery-chart-values.yaml'; values.write_text(yaml.safe_dump(overlay))
        command = [os.environ['HELM_VALIDATE_BIN'], 'template', 'monitoring-monitoring', str(chart), '--namespace', 'monitoring', '--kube-version', '1.36.5', '--set', 'domain=fixture.invalid']
        def objects(args):
            rendered = subprocess.run(command + args, check=True, capture_output=True, text=True)
            return {(obj['kind'], obj['metadata'].get('namespace', ''), obj['metadata']['name']): obj for obj in yaml.safe_load_all(rendered.stdout) if obj}
        before, after = objects([]), objects(['-f', str(values)])
        self.assertEqual(set(before), set(after))
        changes = 0
        for identity in before:
            if identity[0] == 'Prometheus':
                changes += 1
                for selector, expected in overlay['upstream']['prometheus']['prometheusSpec'].items():
                    self.assertEqual(after[identity]['spec'][selector], expected)
                    after[identity]['spec'][selector] = before[identity]['spec'].get(selector)
                    if selector not in before[identity]['spec']: del after[identity]['spec'][selector]
            self.assertEqual(after[identity], before[identity], identity)
        self.assertEqual(changes, 1)

    @unittest.skipUnless(os.environ.get('QUERY_MONITORING_CHART') and os.environ.get('HELM_VALIDATE_BIN'), 'provide verified monitoring chart and Helm')
    def test_native_backend_overlay_keeps_reloader_http_and_loopback_probes(self):
        chart = Path(os.environ['QUERY_MONITORING_CHART'])
        self.assertEqual(yaml.safe_load((chart / 'Chart.yaml').read_text())['version'], '91.4.1-bb.1')
        overlay = yaml.safe_load((BASE / 'backend-values.yaml').read_text())['monitoring']['values']
        values = self.folder / 'backend-chart-values.yaml'; values.write_text(yaml.safe_dump(overlay))
        command = [os.environ['HELM_VALIDATE_BIN'], 'template', 'monitoring-monitoring', str(chart), '--namespace', 'monitoring', '--kube-version', '1.36.5', '--set', 'domain=fixture.invalid', '-f', str(values)]
        rendered = subprocess.run(command, check=True, capture_output=True, text=True)
        docs = [obj for obj in yaml.safe_load_all(rendered.stdout) if obj]
        prom = next(obj for obj in docs if obj['kind'] == 'Prometheus')
        self.assertTrue(prom['spec']['listenLocal'])
        self.assertFalse(prom['spec'].get('web'))
        backend = prom['spec']['containers'][0]
        self.assertEqual(backend['ports'], [{'name': 'backend-tls', 'containerPort': 9443}])
        self.assertNotEqual(backend['ports'][0]['containerPort'], 9090)
        self.assertTrue(backend['securityContext']['readOnlyRootFilesystem'])
        self.assertEqual(backend['securityContext']['capabilities']['drop'], ['ALL'])
        service = next(obj for obj in docs if obj['kind'] == 'Service' and obj['metadata']['name'] == prom['metadata']['name'])
        ports = {port['name']: port for port in service['spec']['ports']}
        self.assertEqual(ports['http-web']['targetPort'], 'backend-tls')
        self.assertNotIn('reloader-web', ports)
        self.assertFalse(any(obj['kind'] == 'ServiceMonitor' and obj['metadata']['name'] == prom['metadata']['name'] for obj in docs))
        monitor = yaml.safe_load((BASE / 'backend-self-monitor.yaml').read_text())
        for key, value in prom['spec'].get('serviceMonitorSelector', {}).get('matchLabels', {}).items():
            self.assertEqual(monitor['metadata']['labels'][key], value)
        self.assertFalse(prom['spec'].get('serviceMonitorSelector', {}).get('matchExpressions'))
        for key, value in monitor['spec']['selector']['matchLabels'].items():
            self.assertEqual(service['metadata']['labels'][key], value)
        endpoint, reloader = monitor['spec']['endpoints']
        self.assertEqual(endpoint['scheme'], 'https')
        self.assertIn('keySecret', endpoint['tlsConfig'])
        self.assertEqual(reloader['port'], 'http-web')
        self.assertEqual(reloader['path'], '/reloader/metrics')
        self.assertEqual(reloader['scheme'], 'https')
        self.assertEqual(reloader['tlsConfig'], endpoint['tlsConfig'])
        self.assertEqual(set(monitor['spec']['namespaceSelector']['matchNames']), {'monitoring'})
        self.assertFalse(any(obj['kind'] == 'Secret' and obj['metadata']['name'].startswith('query-backend') for obj in docs))

    @unittest.skipUnless(os.environ.get('RUN_QUERY_PACKAGE_NATIVE') == '1', 'opt-in network-none container smoke')
    def test_native_container_nonroot_start_and_internal_health(self):
        pod = self.docs[3]['spec']['template']['spec']; nginx, proxy = pod['containers']
        name = 'pf-query-' + uuid.uuid4().hex[:12]
        proxy_name = name + '-scope'
        def run(*args, check=True):
            return subprocess.run(args, check=check, capture_output=True, text=True, timeout=30)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory); folder.chmod(0o755)
            run('openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(folder / 'tls.key'), '-out', str(folder / 'tls.crt'), '-days', '1', '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost')
            (folder / 'tls.key').chmod(0o644)  # synthetic fixture only, no host-container UID trust claim
            (folder / 'ca.crt').write_text((folder / 'tls.crt').read_text())
            (folder / 'nginx.conf').write_text(self.docs[1]['data']['nginx.conf'])
            try:
                run('podman', 'run', '-d', '--name', name, '--pull=never', '--network=none', '--read-only', '--user', '1000:1000', '--cap-drop=ALL', '--security-opt=no-new-privileges', '--tmpfs', '/tmp/gateway:rw,mode=1777,size=32m', '-v', f'{folder}/nginx.conf:/etc/gateway/config/nginx.conf:ro', '-v', f'{folder}:/etc/gateway/tls:ro', '-v', f'{folder}:/etc/gateway/upstream:ro', '--entrypoint', '/usr/sbin/nginx', nginx['image'], *nginx['args'])
                run('podman', 'run', '-d', '--name', proxy_name, '--pull=never', '--network', 'container:' + name, '--read-only', '--user', '1000:1000', '--cap-drop=ALL', '--security-opt=no-new-privileges', '-v', f'{folder}:/etc/gateway/upstream:ro', proxy['image'], *proxy['args'])
                for _ in range(50):
                    result = run('podman', 'exec', name, '/usr/bin/curl', '--silent', '--fail', 'http://127.0.0.1:18091/metrics', check=False)
                    if result.returncode == 0 and 'go_gc_duration_seconds' in result.stdout: break
                    time.sleep(.1)
                else: self.fail('Native internal metrics/readiness listener did not start: ' + result.stderr + run('podman', 'logs', proxy_name, check=False).stderr + run('podman', 'logs', name, check=False).stderr)
                for container in [name, proxy_name]:
                    self.assertEqual(run('podman', 'inspect', '-f', '{{.State.Running}}', container).stdout.strip(), 'true')
            finally:
                run('podman', 'rm', '-f', proxy_name, check=False)
                run('podman', 'rm', '-f', name, check=False)


if __name__ == '__main__': unittest.main()
