"""Local process/session protocol checks; no live credentials or native calls."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / 'configuration/packages/gitlab/enrollment/setup/operator-session.py'
spec = importlib.util.spec_from_file_location('operator_session', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Wrapper(unittest.TestCase):
    def test_default_inert(self):
        p = subprocess.run([sys.executable, '-B', str(SOURCE)], capture_output=True, timeout=5)
        self.assertEqual(p.returncode, 0)
        self.assertIn(b'INERT', p.stdout)

    def test_artifact_atomic_and_foreign_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / 'bearer.json')
            a = m.Artifact(path)
            a.write('token-one', time.time() + 60)
            old_inode = os.stat(path).st_ino
            a.write('token-two', time.time() + 60)
            self.assertNotEqual(old_inode, os.stat(path).st_ino)
            self.assertEqual(json.loads(Path(path).read_text())['access_token'], 'token-two')
            replacement = Path(td) / 'foreign'
            replacement.write_text('foreign')
            replacement.chmod(0o600)
            os.replace(replacement, path)
            with self.assertRaises(m.Blocked):
                a.remove()
            self.assertEqual(Path(path).read_text(), 'foreign')
            with self.assertRaises(FileExistsError):
                m.Artifact(path).write('not-adopted', time.time() + 60)

    def exercise(self, refresh_failure=False, logout_failure=False):
        with tempfile.TemporaryDirectory() as td:
            d = {'mode': 'prepare', 'token_file': str(Path(td) / 'access.json'),
                 'username_file': 'unused', 'password_file': 'unused',
                 'owned_receipt': 'unused', 'reader_inputs': 'unused'}
            state = {'logout': False, 'refreshes': 0}
            class Session:
                refresh = 'old-refresh'
                def __init__(self, _):
                    pass
                def token(self, fields):
                    if fields['grant_type'] == 'refresh_token':
                        state['refreshes'] += 1
                        if refresh_failure:
                            raise m.Blocked('SyntheticRefreshFailure')
                    return 'synthetic-token', time.time() + 60, 0
                def logout(self):
                    state['logout'] = True
                    return not logout_failure
            children = []
            real_popen = subprocess.Popen
            def launch(*args, **kwargs):
                p = real_popen(*args, **kwargs)
                children.append(p)
                return p
            duration = 20 if refresh_failure else 0.2
            started = time.monotonic()
            with patch.object(m, 'Session', Session), patch.object(m.guard, 'validate'), \
                 patch.object(m, 'private_bytes', return_value='synthetic'), \
                 patch.object(m, 'argv', return_value=[sys.executable, '-c', f'import time; time.sleep({duration})']), \
                 patch.object(m.subprocess, 'Popen', side_effect=launch):
                if refresh_failure or logout_failure:
                    with self.assertRaises(m.Blocked):
                        m.run(d)
                else:
                    m.run(d)
            self.assertTrue(state['logout'])
            self.assertGreater(state['refreshes'], 0)
            self.assertFalse(Path(d['token_file']).exists())
            self.assertIsNotNone(children[0].poll())
            self.assertLess(time.monotonic() - started, 5)

    def test_refresh_failure_stops_child_and_logs_out(self):
        self.exercise(refresh_failure=True)

    def test_success_requires_logout(self):
        self.exercise(logout_failure=True)
        self.exercise()

    def test_refresh_replaces_memory_token_and_ttl_is_conservative(self):
        s = object.__new__(m.Session)
        s.refresh = 'prior-refresh'
        with patch.object(s, 'post', return_value={'access_token': 'synthetic-access',
                          'refresh_token': 'replacement-refresh', 'expires_in': 60, 'token_type': 'Bearer'}):
            start = time.time()
            token, expiry, interval = s.token({'grant_type': 'refresh_token', 'refresh_token': s.refresh})
        self.assertEqual(s.refresh, 'replacement-refresh')
        self.assertEqual(token, 'synthetic-access')
        self.assertLessEqual(expiry, time.time() + 60)
        self.assertGreaterEqual(expiry, start + 60)
        self.assertEqual(interval, 20)


if __name__ == '__main__':
    unittest.main()
