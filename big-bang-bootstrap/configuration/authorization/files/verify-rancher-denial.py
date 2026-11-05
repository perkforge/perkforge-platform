#!/usr/bin/env python3
"""One approved disposable identity, native Rancher PKCE denial verification only.
Ansible owns identity lifecycle. Never prints response bodies or credentials.
"""
import base64
import importlib.util
import json
from http.cookies import SimpleCookie
from email.utils import parsedate_to_datetime
import os
from pathlib import Path
import secrets
import signal
import sys
import time
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit

spec = importlib.util.spec_from_file_location('factor', Path(__file__).with_name('verify-factor-browser.py'))
factor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(factor)
require = factor.require
Stop = factor.Stop


def denial_response(response):
    """Pinned v2.15.2 CheckAccess rejects with Unauthorized/unauthorized.
    Token-exchange errors, redirects, generic 403s and server errors are not proof.
    """
    body = response.json()
    require(response.status_code == 401 and isinstance(body, dict)
            and body.get('code') == 'Unauthorized' and body.get('message') == 'unauthorized',
            'expected native access-policy denial')
    # The pinned server expires R_PKCE_VERIFIER during code exchange. That is
    # cleanup, not an issued session; every other cookie is inconclusive.
    header = response.headers.get('Set-Cookie', '')
    cookies = SimpleCookie()
    cookies.load(header)
    require(not header or bool(cookies), 'parse cookie response')
    for name, cookie in cookies.items():
        require(name == 'R_PKCE_VERIFIER' and not cookie.value and cookie['expires']
                and parsedate_to_datetime(cookie['expires']).timestamp() < time.time(), 'no issued cookie')
    require(not any(c.value for c in response.cookies)
            and not any(k in body for k in ('token', 'access_token', 'refresh_token')), 'no session issued')


class RancherBrowser(factor.Browser):
    def fetch(self, url, method='GET', data=None):
        for _ in range(10):
            require(urlsplit(url)[:2] == self.origin and urlsplit(url).scheme == 'https', 'HTTPS identity origin')
            r = self.s.request(method, url, data=data, allow_redirects=False, timeout=20)
            if r.status_code in (301, 302, 303, 307, 308):
                target = urljoin(url, r.headers['Location'])
                q = parse_qs(urlsplit(target).query)
                if urlsplit(target)[:3] == urlsplit(self.c['rancher_origin'] + '/verify-auth')[:3]:
                    require(q.get('state') == [self.state] and len(q.get('code', [])) == 1
                            and 'error' not in q, 'exact successful callback and state')
                    self.callback = q
                    self.page = None
                    return
                if r.status_code not in (307, 308):
                    method, data = 'GET', None
                url = target
                continue
            require(r.status_code in (200, 400), 'identity form status')
            self.current, self.page = r.url, factor.Forms(r.text)
            return
        raise Stop('redirect bound')

    def start(self):
        self.state = base64.urlsafe_b64encode(json.dumps({'nonce': secrets.token_urlsafe(24),
            'to': 'vue', 'provider': 'genericoidc'}).encode()).decode().rstrip('=')
        r = self.s.get(self.c['rancher_origin'] + '/v1-oidc/genericoidc?' + urlencode({
            'state': self.state, 'scope': 'openid profile email'}), allow_redirects=False, timeout=20)
        require(r.status_code == 302, 'Rancher PKCE redirect')
        target = r.headers.get('Location', '')
        q = parse_qs(urlsplit(target).query)
        require(urlsplit(target)[:3] == urlsplit(self.base + '/realms/perkforge/protocol/openid-connect/auth')[:3]
                and q.get('client_id') == ['rancher'] and q.get('response_type') == ['code']
                and q.get('redirect_uri') == [self.c['rancher_origin'] + '/verify-auth']
                and q.get('state') == [self.state] and q.get('code_challenge_method') == ['S256']
                and len(q.get('code_challenge', [''])[0]) == 43, 'pinned Rancher redirect contract')
        require(any(c.name == 'R_PKCE_VERIFIER' and bool(c.value)
                    and (c.domain.lstrip('.') == urlsplit(self.c['rancher_origin']).hostname)
                    for c in self.s.cookies), 'Rancher-owned PKCE cookie')
        self.fetch(target)
        require(self.page and 'kc-form-login' in self.page.forms, 'fresh password challenge')


def private_json(path):
    st = path.lstat()
    require(path.is_file() and not path.is_symlink() and st.st_uid == os.getuid()
            and st.st_mode & 0o777 == 0o600, 'owner-only private input')
    return json.loads(path.read_text())


def run(config):
    require(config['url'] == 'https://keycloak.perkforge.home.arpa/auth'
            and config['rancher_origin'] == 'https://rancher.perkforge.home.arpa', 'reviewed origins')
    secret = private_json(Path(config['private_file']))
    require(secret['username'] == config['username'] and config['username'].startswith('mfa-check-')
            and len(config['username']) == 22 and config['uid'] != 'UNCONFIGURED', 'disposable identity')
    # Account-console enrollment already proved this exact UID; use a fresh TOTP period.
    require(secret.get('tokens') and secret.get('seed'), 'completed test-only enrollment')
    counter = int(time.time()) // config['policy']['period']
    if counter <= secret['last_counter']:
        time.sleep(config['policy']['period'] - time.time() % config['policy']['period'] + 1)
    b = RancherBrowser(config)
    try:
        b.start()
        b.password(secret['password'])
        require(b.page and 'kc-otp-login-form' in b.page.forms, 'fresh test-factor challenge')
        b.submit('kc-otp-login-form', {'otp': factor.otp(secret['seed'], config['policy'])})
        require(b.callback is not None, 'IdP authenticated before Rancher denial')
        # Record the attempt before sending it. A lost response/process interruption
        # must not erase evidence or silently imply that no session was issued.
        incident = Path(config['evidence_dir']) / 'private' / 'rancher-inconclusive.json'
        fd = os.open(incident, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as out:
            json.dump({'status': 'pending-or-uncertain', 'testUID': config['uid']}, out)
            out.flush()
            os.fsync(out.fileno())
        try:
            r = b.s.post(config['rancher_origin'] + '/v1-public/login', json={
                'type': 'genericOIDCProvider', 'description': 'PerkForge disposable denial check',
                'responseType': 'cookie', 'code': b.callback['code'][0]}, allow_redirects=False, timeout=20)
            factor.save_private(incident, {'status': r.status_code, 'testUID': config['uid'],
                'cookies': [{'name': c.name, 'value': c.value, 'domain': c.domain, 'path': c.path}
                            for c in b.s.cookies if c.domain.lstrip('.') == urlsplit(config['rancher_origin']).hostname]})
            denial_response(r)
        except Exception:
            raise Stop('inconclusive native response; exact test-session review required') from None
        incident.unlink()
        result = {'passed': True, 'idpAuthenticationCompleted': True, 'nativeUnauthorized': True,
                  'noSessionIssued': True, 'attempts': 1, 'humanIdentityUsed': False}
        path = Path(config['evidence_dir']) / 'rancher-denial.json'
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as out:
            json.dump(result, out, indent=2)
        print(json.dumps(result))
    finally:
        b.close()


if __name__ == '__main__':
    def deadline(*_):
        raise Stop('phase deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(180)
    try:
        run(private_json(Path(sys.argv[1])))
    except Exception as error:
        print('STOP Rancher denial check: ' + type(error).__name__)
        sys.exit(1)
