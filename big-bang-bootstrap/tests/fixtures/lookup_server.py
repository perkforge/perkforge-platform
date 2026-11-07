"""Loopback-only synthetic Kubernetes API for the real Helm lookup path.

This is an authorization MODEL, not proof of a live Kubernetes authorizer.
No real kubeconfig, credentials or Secret values are used.
"""
import base64
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
from urllib.parse import urlsplit


def secret_allowed(role, namespace, name, verb):
    if role['metadata']['namespace'] != namespace:
        return False
    return any('' in r['apiGroups'] and 'secrets' in r['resources']
               and verb in r['verbs']
               and (not r.get('resourceNames') or name in r['resourceNames'])
               for r in role['rules'])


def clusterrole_list_allowed(role):
    """Unnamed collection listing needs a rule without resourceNames/field selector."""
    return any('rbac.authorization.k8s.io' in r['apiGroups']
               and 'clusterroles' in r['resources'] and 'list' in r['verbs']
               and not r.get('resourceNames') for r in role['rules'])


@contextmanager
def lookup_server(role, clusterrole_lookup=False, secrets=None, helmrelease_lookup=False, monitoring_api=False, helmreleases=None):
    requests = []
    if secrets is None:
        secrets = {(role['metadata'].get('namespace', ''), 'keycloak-database-existing'): {
            'postgres-password': base64.b64encode(b'synthetic-test-password').decode()}}

    groups = []
    if clusterrole_lookup:
        groups.append(('rbac.authorization.k8s.io', ['v1']))
    if helmrelease_lookup:
        groups.append(('helm.toolkit.fluxcd.io', ['v2']))
    if monitoring_api:
        groups.append(('monitoring.coreos.com', ['v1', 'v1alpha1']))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            path = urlsplit(self.path).path
            requests.append(self.path if clusterrole_lookup else path)
            status = 200
            if path == '/version':
                body = {'major': '1', 'minor': '36', 'gitVersion': 'v1.36.5'}
            elif path == '/api':
                body = {'apiVersion': 'v1', 'kind': 'APIVersions', 'versions': ['v1'], 'serverAddressByClientCIDRs': []}
            elif path == '/apis':
                body = {'apiVersion': 'v1', 'kind': 'APIGroupList', 'groups': [
                    {'name': name,
                     'versions': [{'groupVersion': name + '/' + version, 'version': version} for version in versions],
                     'preferredVersion': {'groupVersion': name + '/' + versions[0], 'version': versions[0]}}
                    for name, versions in groups]}
            elif path == '/api/v1':
                body = {'apiVersion': 'v1', 'kind': 'APIResourceList', 'groupVersion': 'v1', 'resources': [
                    {'name': 'secrets', 'singularName': 'secret', 'namespaced': True,
                     'kind': 'Secret', 'verbs': ['get', 'list']}]}
            elif helmrelease_lookup and path == '/apis/helm.toolkit.fluxcd.io/v2':
                body = {'apiVersion': 'v1', 'kind': 'APIResourceList', 'groupVersion': 'helm.toolkit.fluxcd.io/v2',
                        'resources': [{'name': 'helmreleases', 'kind': 'HelmRelease', 'namespaced': True,
                                       'verbs': ['get', 'list']}]}
            elif monitoring_api and path in ['/apis/monitoring.coreos.com/v1', '/apis/monitoring.coreos.com/v1alpha1']:
                body = {'apiVersion': 'v1', 'kind': 'APIResourceList', 'groupVersion': path[len('/apis/'):],
                        'resources': [{'name': name, 'kind': kind, 'namespaced': True, 'verbs': ['get', 'list']}
                                      for name, kind in ([('servicemonitors', 'ServiceMonitor'), ('podmonitors', 'PodMonitor'),
                                                          ('prometheuses', 'Prometheus'), ('prometheusrules', 'PrometheusRule')]
                                                         if path.endswith('/v1') else
                                                         [('alertmanagerconfigs', 'AlertmanagerConfig'), ('scrapeconfigs', 'ScrapeConfig')])]}

            elif helmrelease_lookup and path.startswith('/apis/helm.toolkit.fluxcd.io/v2/namespaces/') and '/helmreleases/' in path:
                namespace = path.split('/')[5]
                name = path.split('/')[7]
                allowed = role['metadata']['namespace'] == namespace and any(
                    'helm.toolkit.fluxcd.io' in rule['apiGroups'] and 'helmreleases' in rule['resources']
                    and 'get' in rule['verbs']
                    and (not rule.get('resourceNames') or name in rule['resourceNames']) for rule in role['rules'])
                item = (helmreleases or {}).get((namespace, name))
                status = (200 if item else 404) if allowed else 403
                body = item if status == 200 else {
                    'apiVersion': 'v1', 'kind': 'Status', 'status': 'Failure',
                    'reason': 'NotFound' if allowed else 'Forbidden', 'code': status,
                    'message': 'HelmRelease not found' if allowed else 'HelmRelease GET forbidden by synthetic authorizer'}
            elif clusterrole_lookup and path == '/apis/rbac.authorization.k8s.io/v1':
                body = {'apiVersion': 'v1', 'kind': 'APIResourceList',
                        'groupVersion': 'rbac.authorization.k8s.io/v1', 'resources': [
                    {'name': 'clusterroles', 'singularName': 'clusterrole', 'namespaced': False,
                     'kind': 'ClusterRole', 'verbs': ['get', 'list']}]}
            elif clusterrole_lookup and path == '/apis/rbac.authorization.k8s.io/v1/clusterroles':
                if clusterrole_list_allowed(role):
                    body = {'apiVersion': 'rbac.authorization.k8s.io/v1', 'kind': 'ClusterRoleList',
                            'metadata': {}, 'items': []}
                else:
                    status = 403
                    body = {'apiVersion': 'v1', 'kind': 'Status', 'status': 'Failure',
                            'message': 'unnamed ClusterRole LIST forbidden by synthetic authorization model',
                            'reason': 'Forbidden', 'code': status}
            elif path.startswith('/api/v1/namespaces/') and '/secrets/' in path:
                parts = path.split('/')
                namespace, name = parts[4], parts[6]
                if secret_allowed(role, namespace, name, 'get') and (namespace, name) in secrets:
                    body = {'apiVersion': 'v1', 'kind': 'Secret',
                            'metadata': {'name': name, 'namespace': namespace},
                            'data': secrets[namespace, name]}
                elif secret_allowed(role, namespace, name, 'get'):
                    status = 404
                    body = {'apiVersion': 'v1', 'kind': 'Status', 'status': 'Failure', 'reason': 'NotFound', 'code': status}
                else:
                    status = 403
                    body = {'apiVersion': 'v1', 'kind': 'Status', 'status': 'Failure',
                            'message': 'named Secret GET forbidden by synthetic authorization model',
                            'reason': 'Forbidden', 'code': status}
            else:
                status = 404
                body = {'apiVersion': 'v1', 'kind': 'Status', 'status': 'Failure', 'reason': 'NotFound', 'code': status}
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:' + str(server.server_port), requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
