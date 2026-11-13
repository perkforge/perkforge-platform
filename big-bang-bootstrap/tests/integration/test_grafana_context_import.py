"""Opt-in native import test. Synthetic input, network-isolated disposable Grafana."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configuration.test_context_alerting import fixture, render
import yaml


@unittest.skipUnless(os.environ.get('RUN_GRAFANA_CONTEXT_IMPORT') == '1',
                     'set RUN_GRAFANA_CONTEXT_IMPORT=1; requires podman and pre-pulled official image')
class NativeGrafanaImport(unittest.TestCase):
    def test_native_contact_point_import(self):
        name = 'pf-alert-import-' + uuid.uuid4().hex[:12]
        # Official Grafana 13.2.1 manifest, pinned for repeatable native evidence.
        image = 'docker.io/grafana/grafana@sha256:1dec240d14e232597dce9bfa56dae55f4397b138cdc91e3ee92ac6b157e2fc49'
        def podman(*args, check=True):
            return subprocess.run(['podman', *args], check=check, capture_output=True,
                                  text=True, timeout=30)
        with tempfile.TemporaryDirectory(prefix='pf-alert-import-') as directory:
            path = Path(directory)
            path.chmod(0o755)
            provision = path / 'contact-points.yaml'
            provision.write_text(yaml.safe_dump(render([fixture()])))
            provision.chmod(0o644)  # synthetic fixture only; never production credentials
            try:
                podman('run', '-d', '--name', name, '--pull=never', '--network=none',
                       '--cap-drop=ALL', '--security-opt=no-new-privileges',
                       '-e', 'GF_SECURITY_ADMIN_PASSWORD=synthetic-test-password',
                       '-e', 'GF_ANALYTICS_REPORTING_ENABLED=false',
                       '-e', 'GF_ANALYTICS_CHECK_FOR_UPDATES=false',
                       '-e', 'GF_PLUGINS_PREINSTALL_DISABLED=true',
                       '-v', f'{provision}:/etc/grafana/provisioning/alerting/contexts.yaml:ro', image)
                result = None
                for _ in range(60):
                    result = podman('exec', name, 'wget', '-qO-',
                                    'http://admin:synthetic-test-password@127.0.0.1:3000/api/v1/provisioning/contact-points',
                                    check=False)
                    if result.returncode == 0:
                        break
                    time.sleep(1)
                self.assertEqual(result.returncode, 0, 'Grafana did not expose provisioning API')
                health = json.loads(podman('exec', name, 'wget', '-qO-',
                                          'http://127.0.0.1:3000/api/health').stdout)
                self.assertEqual(health['version'], '13.2.1')
                points = json.loads(result.stdout)
                expected = {r['uid']: r for r in render([fixture()])['contactPoints'][0]['receivers']}
                self.assertEqual({p['uid'] for p in points},
                                 {'ctx-portal-ntfy', 'ctx-portal-mattermost'})
                for point in points:
                    self.assertEqual(point['name'], 'context-portal')
                    self.assertEqual(point['type'], 'webhook')
                    self.assertEqual(point['provenance'], 'file')
                    self.assertFalse(point['disableResolveMessage'])
                    self.assertIn('payload', point['settings'])
                    self.assertEqual(point['settings']['payload'], expected[point['uid']]['settings']['payload'])
            finally:
                podman('rm', '-f', name, check=False)


if __name__ == '__main__':
    unittest.main()
