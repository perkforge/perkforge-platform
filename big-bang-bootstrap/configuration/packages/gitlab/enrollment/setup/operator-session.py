#!/usr/bin/env python3
"""Bounded operator authentication for two fixed native setup helpers only.

Default inert. No realm lifetime changes. Refresh tokens stay in memory; the
private access-token artifact is replaced atomically and removed on exit.
An interrupted/failed helper may have partial effects: retain its receipts and
require manual review, never automatically retry. Lost refresh responses can
make logout uncertain; success is never reported without verified logout.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import ssl
import stat
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('session_guard', HERE / 'validate-kc-reader.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class Blocked(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Blocked('RedirectDenied')


def private_bytes(path):
    guard.safe(path, limit=4096)
    before = os.lstat(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        s = os.fstat(fd)
        if ((s.st_dev, s.st_ino) != (before.st_dev, before.st_ino)
                or not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid()
                or stat.S_IMODE(s.st_mode) != 0o600 or s.st_nlink != 1
                or s.st_size > 4096):
            raise Blocked('UnsafeCredential')
        raw = os.read(fd, 4097)
        if not raw or len(raw) > 4096:
            raise Blocked('InvalidCredentialSize')
        return raw.decode().strip()
    finally:
        os.close(fd)


def selection(path):
    d = guard.read(path)
    keys = {'mode', 'origin', 'ca_file', 'username_file', 'password_file',
            'token_file', 'owned_receipt', 'reader_inputs'}
    if d.get('mode') == 'activate':
        keys |= {'bao_token', 'custody_receipt', 'custody_inputs'}
    if set(d) != keys or d.get('mode') not in ('prepare', 'activate'):
        raise Blocked('InvalidSelection')
    for key, value in d.items():
        pattern = (r'https://[A-Za-z0-9.-]+(?::[0-9]+)?(?:/auth)?' if key == 'origin'
                   else r'(?:prepare|activate)' if key == 'mode'
                   else r'/[A-Za-z0-9_./-]+')
        if not isinstance(value, str) or not re.fullmatch(pattern, value):
            raise Blocked('NonliteralSelection')
    paths = [v for k, v in d.items() if k not in ('origin', 'mode')]
    if len(set(paths)) != len(paths):
        raise Blocked('OverlappingPaths')
    for key in ('username_file', 'password_file'):
        guard.safe(d[key], limit=4096)
    guard.safe(d['ca_file'], private=False, limit=262144)
    guard.safe(d['token_file'], optional=True, limit=4096)
    if os.path.lexists(d['token_file']):
        raise Blocked('ExistingTokenArtifact')
    reader = guard.read(d['reader_inputs'])
    if reader.get('kc_reader_origin') != d['origin'] or reader.get('kc_reader_ca_file') != d['ca_file']:
        raise Blocked('TargetMismatch')
    return d


class Artifact:
    def __init__(self, path):
        self.path = path
        self.inode = None

    def check(self):
        guard.safe(self.path, limit=4096)
        s = os.lstat(self.path)
        if (s.st_dev, s.st_ino) != self.inode:
            raise Blocked('ArtifactReplaced')

    def write(self, token, expires_at):
        raw = json.dumps({'access_token': token, 'expires_at': expires_at}).encode()
        if len(raw) > 4096:
            raise Blocked('OversizeAccessToken')
        guard.safe(self.path, optional=self.inode is None, limit=4096)
        tmp = None
        if self.inode is None:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            s = os.fstat(fd)
            self.inode = (s.st_dev, s.st_ino)
        else:
            self.check()
            fd, tmp = tempfile.mkstemp(prefix='.operator-access-', dir=str(Path(self.path).parent))
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
                s = os.fstat(f.fileno())
            if tmp:
                self.check()
                os.replace(tmp, self.path)
                tmp = None
                self.inode = (s.st_dev, s.st_ino)
            directory = os.open(str(Path(self.path).parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if tmp is not None:
                os.unlink(tmp)

    def remove(self):
        if self.inode is not None:
            self.check()
            os.unlink(self.path)
            self.inode = None


class Session:
    def __init__(self, d):
        self.url = d['origin'] + '/realms/master/protocol/openid-connect/'
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=d['ca_file'])))
        self.refresh = None

    def post(self, endpoint, fields):
        request = urllib.request.Request(self.url + endpoint,
            data=urllib.parse.urlencode(fields).encode(), method='POST',
            headers={'Content-Type': 'application/x-www-form-urlencoded'})
        with self.opener.open(request, timeout=5) as response:
            raw = response.read(16385)
            if len(raw) > 16384:
                raise Blocked('OversizeSessionResponse')
            if endpoint == 'logout':
                if response.status != 204:
                    raise Blocked('LogoutUnverified')
                return None
            if response.status != 200:
                raise Blocked('SessionUnverified')
            return json.loads(raw)

    def token(self, fields):
        started = time.time()
        d = self.post('token', {'client_id': 'admin-cli', **fields})
        # Retain any returned replacement refresh token for cleanup even if a
        # subsequent access-token/TTL check fails.
        if isinstance(d.get('refresh_token'), str) and 1 <= len(d['refresh_token']) <= 8192:
            self.refresh = d['refresh_token']
        token = d.get('access_token')
        ttl = d.get('expires_in')
        if (not self.refresh or not isinstance(token, str)
                or not re.fullmatch(r'[A-Za-z0-9_.-]{8,3800}', token)
                or type(ttl) is not int or not 30 <= ttl <= 3600
                or d.get('token_type', '').lower() != 'bearer'):
            raise Blocked('InvalidSessionResponse')
        return token, started + ttl, min(20, ttl / 3)

    def logout(self):
        if self.refresh is None:
            return False
        self.post('logout', {'client_id': 'admin-cli', 'refresh_token': self.refresh})
        self.refresh = None
        return True


def argv(d):
    if d['mode'] == 'prepare':
        return ['bash', str(HERE / 'run-kc-reader.sh'), '--apply', d['token_file'],
                d['owned_receipt'], d['reader_inputs']]
    return [sys.executable, str(HERE / 'activate-keycloak.py'), 'apply', d['token_file'],
            d['bao_token'], d['owned_receipt'], d['custody_receipt'], d['custody_inputs']]


def stop(child):
    if child is None:
        return
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    # Include descendants even if the immediate launcher already exited.
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait(timeout=1)


def run(d):
    session = Session(d)
    artifact = Artifact(d['token_file'])
    child = None
    success = False
    logout_ok = False
    cleanup_ok = False
    deadline = time.monotonic() + 285  # Reserve bounded termination/logout time.
    try:
        # Native helpers validate protected input shape before any bootstrap
        # credential read. This temporary placeholder cannot authenticate.
        artifact.write('inert-placeholder', time.time() + 60)
        guard.validate(d['token_file'], d['owned_receipt'], d['reader_inputs'], '--validate')
        if d['mode'] == 'activate':
            spec = importlib.util.spec_from_file_location('session_activation', HERE / 'activate-keycloak.py')
            activation = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(activation)
            selected = activation.validate(d['token_file'], d['bao_token'], d['owned_receipt'],
                                           d['custody_receipt'], d['custody_inputs'])
            if selected['reader_inputs'] != d['reader_inputs']:
                raise Blocked('ActivationReaderMismatch')
        token, expires, interval = session.token({'grant_type': 'password',
            'username': private_bytes(d['username_file']), 'password': private_bytes(d['password_file'])})
        artifact.write(token, expires)
        token = None
        next_refresh = time.monotonic() + interval
        child = subprocess.Popen(argv(d), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
        while child.poll() is None:
            if time.monotonic() >= deadline:
                raise Blocked('SessionDeadline')
            if time.monotonic() >= next_refresh:
                token, expires, interval = session.token({'grant_type': 'refresh_token', 'refresh_token': session.refresh})
                artifact.write(token, expires)
                token = None
                next_refresh = time.monotonic() + interval
            time.sleep(0.1)
        success = child.returncode == 0
    finally:
        # Main's hard timer includes slow/dribbling HTTP responses, not only the
        # polling loop. Give cleanup its own bounded reserve (total <=300s).
        if signal.getsignal(signal.SIGALRM) == alarm_handler:
            signal.alarm(10)
        try:
            stop(child)
        finally:
            try:
                logout_ok = session.logout()
            finally:
                artifact.remove()
                cleanup_ok = True
    if not success or not logout_ok or not cleanup_ok:
        raise Blocked('HelperOrCleanupUnverified')


def alarm_handler(signum, frame):
    raise Blocked('SessionDeadline')


def main():
    if len(sys.argv) < 2 or sys.argv[1] != 'apply':
        print('INERT: explicit operator-session apply required')
        return 0
    def interrupted(signum, frame):
        raise Blocked('Interrupted')
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, interrupted)
    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(285)
    try:
        if len(sys.argv) != 3:
            raise Blocked('InvalidArguments')
        run(selection(sys.argv[2]))
        print('{"stage":"HelperCompletedSessionClosed"}')
        return 0
    except Exception:
        print('{"stage":"ManualReviewRequired","category":"OperatorSessionOrHelperUnverified"}')
        return 1
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    raise SystemExit(main())
