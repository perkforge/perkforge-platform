"""Verification only: private TokenRequest custody, Headlamp login/proxy and revocation."""
import base64
import datetime
import http.cookiejar
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def claims(token, metadata):
    parts = token.split('.')
    require(len(parts) == 3, 'invalid token shape')
    data = json.loads(base64.urlsafe_b64decode(parts[1] + '=' * (-len(parts[1]) % 4)))
    require(data['sub'] == metadata['principal'], 'unexpected token principal')
    require(data['kubernetes.io']['serviceaccount']['uid'] == metadata['sa_uid'], 'unexpected token account UID')
    require(0 < data['exp'] - data['iat'] <= 3600, 'issued lifetime exceeds approved hour')
    require(data['exp'] > time.time(), 'token expired before verification')
    timestamp = datetime.datetime.fromisoformat(metadata['expires'].replace('Z', '+00:00')).timestamp()
    require(abs(timestamp - data['exp']) < 2, 'expiry metadata mismatch')
    return data


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(opener, base, path, payload=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(base + path, data=None if payload is None else json.dumps(payload).encode(), headers=headers)
    try:
        with opener.open(req, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def verify(folder, mode, base='http://127.0.0.1:14466'):
    require(base == 'http://127.0.0.1:14466', 'unexpected forwarding address')
    folder = Path(folder)
    for p in (folder, folder / 'token.txt', folder / 'metadata.json'):
        stat = p.lstat()
        require(not p.is_symlink() and stat.st_uid == os.getuid(), 'unexpected custody ownership/type')
        require(stat.st_mode & 0o777 == (0o700 if p.is_dir() else 0o600), 'custody permissions exposed')
    token = (folder / 'token.txt').read_text().strip()
    metadata = json.loads((folder / 'metadata.json').read_text())
    claims(token, metadata)  # Scope/expiry checks, not signature proof; actual API verifies signature below.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    code, raw = request(opener, base, '/config', token=token)
    require(code == 200, 'Headlamp config unavailable')
    clusters = json.loads(raw)['clusters']
    require(len(clusters) == 1 and isinstance(clusters[0]['name'], str), 'unexpected configured cluster set')
    prefix = '/clusters/' + urllib.parse.quote(clusters[0]['name'], safe='')
    code, _ = request(opener, base, prefix + '/api/v1/namespaces?limit=1')
    require(code in (401, 403), 'unauthenticated Kubernetes read unexpectedly allowed')
    if mode == 'revoked':
        code, _ = request(opener, base, prefix + '/api/v1/namespaces?limit=1', token=token)
        require(code in (401, 403), 'temporary admin still authorized after cleanup')
        metadata['revoked'] = True
        (folder / 'metadata.json').write_text(json.dumps(metadata, indent=2))
        print('PASS temporary token no longer authorizes namespace read; custody marked revoked')
        return
    require(mode == 'access', 'unknown verification mode')
    code, html = request(opener, base, '/')
    require(code == 200 and b'<html' in html.lower(), 'Headlamp UI not served')
    code, _ = request(opener, base, prefix + '/set-token', {'token': token})
    require(code == 200, 'Headlamp token-login endpoint failed')
    # Cookie-backed API request exercises the browser login path, without token in URL/arguments.
    code, raw = request(opener, base, prefix + '/api/v1/namespaces?limit=1')
    require(code == 200 and json.loads(raw)['kind'] == 'NamespaceList', 'authenticated UI proxy read failed')
    code, raw = request(opener, base, prefix + '/apis/authentication.k8s.io/v1/selfsubjectreviews', {'apiVersion': 'authentication.k8s.io/v1', 'kind': 'SelfSubjectReview'})
    require(code in (200, 201), 'authenticated identity review failed')
    identity = json.loads(raw)['status']['userInfo']
    require(identity['username'] == metadata['principal'] and identity['uid'] == metadata['sa_uid'], 'proxy used unexpected identity')
    results = []
    for group, resource, verb, namespace in [('', 'secrets', 'get', 'headlamp'), ('', 'pods', 'delete', 'headlamp'), ('rbac.authorization.k8s.io', 'clusterrolebindings', 'create', None)]:
        attr = {'group': group, 'resource': resource, 'verb': verb}
        if namespace:
            attr['namespace'] = namespace
        code, raw = request(opener, base, prefix + '/apis/authorization.k8s.io/v1/selfsubjectaccessreviews', {'apiVersion': 'authorization.k8s.io/v1', 'kind': 'SelfSubjectAccessReview', 'spec': {'resourceAttributes': attr}})
        require(code in (200, 201) and json.loads(raw)['status']['allowed'], 'approved admin capability not present')
        results.append(attr)  # Permission review only; no Secret reads or destructive demonstration.
    (folder / 'verification.json').write_text(json.dumps({'uiServed': True, 'cookieLoginProxyVerified': True, 'principalVerified': True, 'adminCapabilityReviews': results, 'personalBrowserLoginObserved': False}, indent=2))
    (folder / 'verification.json').chmod(0o600)
    code, _ = request(opener, base, prefix + '/set-token', {'token': ''})
    require(code == 200, 'test session logout failed')
    print('PASS UI served, cookie login/proxy and dedicated administrator verified; no Secret values read or workload writes; personal browser not observed')


if __name__ == '__main__':
    os.umask(0o077)
    try:
        verify(sys.argv[1], sys.argv[2])
    except Exception as error:
        # Controlled message/class only; never response bodies, headers or token material.
        message = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        print('STOP Headlamp access verification: ' + message)
        sys.exit(1)
