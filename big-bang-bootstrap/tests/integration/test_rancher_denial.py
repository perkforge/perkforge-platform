"""Offline native protocol and inert playbook checks; never live acceptance."""
import contextlib
import io
from urllib.parse import parse_qs, urlencode, urlsplit
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
import requests
import yaml

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / 'configuration/authorization'
spec = importlib.util.spec_from_file_location('denial', AUTH/'files/verify-rancher-denial.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def response(status=401, body=None, headers=None):
    r = Mock(status_code=status, headers=headers or {}, cookies=[])
    r.json.return_value = body if body is not None else {'code': 'Unauthorized', 'message': 'unauthorized'}
    return r


class RancherDenial(unittest.TestCase):
    def test_pinned_explicit_denial(self):
        m.denial_response(response())

    def test_expiring_pkce_cookie_is_cleanup_not_a_session(self):
        m.denial_response(response(headers={'Set-Cookie': 'R_PKCE_VERIFIER=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly'}))

    def test_other_auth_failures_are_not_policy_denials(self):
        for r in (response(403), response(500), response(302), response(200),
                  response(body={'code': 'Unauthorized', 'message': 'invalid code'}),
                  response(body={'error': 'invalid_grant'})):
            with self.subTest(status=r.status_code), self.assertRaises(m.Stop):
                m.denial_response(r)

    def test_any_session_or_token_blocks_pass(self):
        for r in (response(headers={'Set-Cookie': 'R_SESS=synthetic-only; HttpOnly'}),
                  response(headers={'Set-Cookie': 'R_PKCE_VERIFIER=not-expired'}),
                  response(body={'code': 'Unauthorized', 'message': 'unauthorized', 'token': 'synthetic-only'})):
            with self.assertRaises(m.Stop):
                m.denial_response(r)

    def browser(self):
        return m.RancherBrowser({'url': 'https://identity.invalid/auth', 'ca': 'public-ca',
                                'redirect': 'https://identity.invalid/account/',
                                'rancher_origin': 'https://rancher.invalid'})

    def test_foreign_form_action_never_receives_password(self):
        b = self.browser()
        with patch.object(b.s, 'request') as request:
            with self.assertRaises(m.Stop):
                b.fetch('https://foreign.invalid/steal', 'POST', {'password': 'synthetic-only'})
            request.assert_not_called()
        b.close()

    def test_callback_state_mismatch_never_reaches_native_login(self):
        b = self.browser()
        r = response(302, headers={'Location': 'https://rancher.invalid/verify-auth?code=fixture&state=foreign'})
        with patch.object(b.s, 'request', return_value=r), self.assertRaises(m.Stop):
            b.fetch('https://identity.invalid/auth')
        self.assertIsNone(b.callback)
        b.close()

    def test_matching_external_callback_is_not_followed(self):
        b = self.browser()
        r = response(302, headers={'Location': 'https://rancher.invalid/verify-auth?code=fixture&state='+b.state})
        with patch.object(b.s, 'request', return_value=r) as request:
            b.fetch('https://identity.invalid/auth')
            self.assertEqual(request.call_count, 1)
        self.assertEqual(b.callback['code'], ['fixture'])
        b.close()

    def test_missing_pkce_cookie_refuses_identity_request(self):
        b = self.browser()
        with patch.object(b.s, 'get', return_value=response(302, headers={'Location': 'https://foreign.invalid/'})), patch.object(b, 'fetch') as fetch:
            with self.assertRaises(m.Stop):
                b.start()
            fetch.assert_not_called()
        b.close()

    def test_private_input_permissions_and_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'test.json'; p.write_text('{}');p.chmod(0o644)
            with self.assertRaises(m.Stop):m.private_json(p)
            p.chmod(0o600);self.assertEqual(m.private_json(p), {})
            q = Path(d)/'link';q.symlink_to(p)
            with self.assertRaises(m.Stop):m.private_json(q)

    def test_default_and_check_mode_are_inert(self):
        with tempfile.TemporaryDirectory() as d:
            env = {**os.environ, 'ANSIBLE_LOCAL_TEMP': d+'/local', 'ANSIBLE_REMOTE_TEMP': d+'/remote'}
            for args in ([], ['-e', 'rancher_denial_apply=true', '--check']):
                result = subprocess.run(['ansible-playbook', '-i', str(ROOT/'configuration/ansible/inventory.yaml'),
                    str(AUTH/'rancher-denial-acceptance.yaml'), *args], env=env, text=True, capture_output=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertIn('changed=0', result.stdout)

    def test_lifecycle_keeps_exact_uid_guard_and_cleanup_on_failure(self):
        source = (AUTH/'rancher-denial-acceptance.yaml').read_text()
        data = yaml.safe_load(source)
        self.assertFalse(data[0]['vars']['rancher_denial_apply'])
        self.assertIn('always:', source)
        self.assertIn('tasks/factor-owned.yaml', source)
        self.assertIn('factor_uid == factor_cleanup_found.json[0].id', source)
        self.assertIn("{{ factor_api }}/users/{{ factor_uid }}/logout", source)
        self.assertIn('rancher-inconclusive.json', source)
        self.assertNotIn('credentials/{{ factor_old_otp_id }}', source)
        self.assertNotIn('tokens.management.cattle.io', source)
        self.assertIn('no_log: true', source)


class NativeTransaction(unittest.TestCase):
    def exercise(self, native):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d); (base/'private').mkdir(mode=0o700)
            private = base/'private/test.json'
            password = 'synthetic-password-only-32-characters'
            private.write_text(json.dumps({'username': 'mfa-check-012345abcdef', 'password': password,
                'seed': 'JBSWY3DPEHPK3PXP', 'last_counter': 0, 'tokens': {'access_token': 'fixture-only'}}))
            private.chmod(0o600)
            config = {'url': 'https://keycloak.perkforge.home.arpa/auth',
                'rancher_origin': 'https://rancher.perkforge.home.arpa', 'ca': 'public-ca',
                'redirect': 'https://keycloak.perkforge.home.arpa/auth/realms/perkforge/account/',
                'username': 'mfa-check-012345abcdef', 'uid': 'fixture-test-uid',
                'private_file': str(private), 'evidence_dir': str(base),
                'policy': {'period': 30, 'digits': 6, 'algorithm': 'HmacSHA1'}}
            session = Mock(cookies=requests.cookies.RequestsCookieJar())
            if isinstance(native, Exception):
                session.post.side_effect = native
            else:
                session.post.return_value = native
            state = {}
            def initial(url, **kwargs):
                state['value'] = parse_qs(urlsplit(url).query)['state'][0]
                session.cookies.set('R_PKCE_VERIFIER', 'synthetic-only', domain='rancher.perkforge.home.arpa', path='/')
                query = urlencode({'client_id':'rancher','response_type':'code',
                    'redirect_uri':config['rancher_origin']+'/verify-auth', 'state':state['value'],
                    'code_challenge_method':'S256','code_challenge':'x'*43})
                return response(302, headers={'Location':config['url']+'/realms/perkforge/protocol/openid-connect/auth?'+query})
            session.get.side_effect = initial
            def forms(method, url, **kwargs):
                if method == 'GET':
                    html = '<form id="kc-form-login" action="/auth/password"></form>'
                elif url.endswith('/password'):
                    self.assertEqual(kwargs['data']['password'], password)
                    html = '<form id="kc-otp-login-form" action="/auth/otp"></form>'
                else:
                    self.assertEqual(len(kwargs['data']['otp']),6)
                    return response(302, headers={'Location':config['rancher_origin']+'/verify-auth?'+urlencode({'state':state['value'],'code':'synthetic-code'})})
                r=response(200);r.url=url;r.text=html;return r
            session.request.side_effect = forms
            output = io.StringIO()
            with patch.object(m.factor.requests, 'Session', return_value=session), contextlib.redirect_stdout(output):
                try:
                    m.run(config)
                    stopped = False
                except m.Stop:
                    stopped = True
            self.assertNotIn(password, output.getvalue())
            self.assertNotIn('synthetic-code', output.getvalue())
            self.assertTrue(session.verify == 'public-ca' and session.trust_env is False)
            self.assertEqual(session.post.call_count,1)
            self.assertEqual(session.post.call_args.args[0],config['rancher_origin']+'/v1-public/login')
            incident=base/'private/rancher-inconclusive.json'
            if stopped:
                self.assertTrue(incident.exists())
                self.assertEqual(incident.stat().st_mode & 0o777,0o600)
                self.assertFalse((base/'rancher-denial.json').exists())
            else:
                self.assertTrue(json.loads((base/'rancher-denial.json').read_text())['noSessionIssued'])
                self.assertFalse(incident.exists())
            self.assertTrue(private.exists())  # only Ansible owns lifecycle cleanup
            session.close.assert_called_once()
            return stopped

    def test_native_deny_after_actual_password_factor_callback_sequence(self):
        self.assertFalse(self.exercise(response()))

    def test_unexpected_admission_fails_and_preserves_private_transaction(self):
        self.assertTrue(self.exercise(response(201, body={'type':'token'})))

    def test_server_error_is_inconclusive_not_a_denial_pass(self):
        self.assertTrue(self.exercise(response(500, body={'code':'ServerError'})))

    def test_lost_native_response_retains_pending_marker_for_review(self):
        self.assertTrue(self.exercise(requests.Timeout('synthetic timeout')))
