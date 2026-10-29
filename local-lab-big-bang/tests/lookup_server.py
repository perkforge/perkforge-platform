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


@contextmanager
def lookup_server(role):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            path = urlsplit(self.path).path
            requests.append(path)
            status = 200
            if path == '/version':
                body = {'major': '1', 'minor': '36', 'gitVersion': 'v1.36.5'}
            elif path == '/api':
                body = {'apiVersion': 'v1', 'kind': 'APIVersions', 'versions': ['v1'], 'serverAddressByClientCIDRs': []}
            elif path == '/apis':
                body = {'apiVersion': 'v1', 'kind': 'APIGroupList', 'groups': []}
            elif path == '/api/v1':
                body = {'apiVersion': 'v1', 'kind': 'APIResourceList', 'groupVersion': 'v1', 'resources': [
                    {'name': 'secrets', 'singularName': 'secret', 'namespaced': True,
                     'kind': 'Secret', 'verbs': ['get', 'list']}]}
            elif path.startswith('/api/v1/namespaces/') and '/secrets/' in path:
                parts = path.split('/')
                namespace, name = parts[4], parts[6]
                if secret_allowed(role, namespace, name, 'get') and name == 'keycloak-database-existing':
                    body = {'apiVersion': 'v1', 'kind': 'Secret',
                            'metadata': {'name': name, 'namespace': namespace},
                            'data': {'postgres-password': base64.b64encode(b'synthetic-test-password').decode()}}
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
