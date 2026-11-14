"""Pinned native Grafana file import only, not live Loki query/isolation proof."""
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.request
import yaml
from configuration.test_app_dashboards import render, ROOT


class NativeAppDashboards(unittest.TestCase):
    def test_native_file_provisioning(self):
        binary = os.environ.get('GRAFANA_VALIDATE_BIN')
        if not binary:
            self.skipTest('Set checksum-pinned GRAFANA_VALIDATE_BIN; no downloads')
        pin = yaml.safe_load((ROOT / 'configuration/observability/tenant-query/sources.yaml').read_text())['grafana']
        self.assertEqual(hashlib.sha256(Path(binary).read_bytes()).hexdigest(), pin['linux_amd64_binary_sha256'])
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            result = render(folder)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            provisioning = folder / 'provisioning/dashboards'
            provisioning.mkdir(parents=True)
            provider = yaml.safe_load((folder / 'out/helm-values.yaml').read_text())['upstream']['dashboardProviders']['perkforge-app-resources.yaml']
            # Fixture-only filesystem mount replacement, never a deployment edit.
            provider['providers'][0]['options']['path'] = str(folder / 'out')
            (provisioning / 'logs.yaml').write_text(yaml.safe_dump(provider))
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
            config = folder / 'grafana.ini'
            config.write_text(f'[server]\nhttp_addr=127.0.0.1\nhttp_port={port}\n[paths]\ndata={folder}/data\nlogs={folder}/logs\nplugins={folder}/plugins\nprovisioning={folder}/provisioning\n[security]\nadmin_user=fixture-admin\nadmin_password=synthetic-admin\n[analytics]\nreporting_enabled=false\ncheck_for_updates=false\ncheck_for_plugin_updates=false\n[plugins]\npreinstall_disabled=true\n')
            with (folder / 'native.log').open('w') as log:
                process = subprocess.Popen([binary, 'server', '--homepath', str(Path(binary).resolve().parents[1]), '--config', str(config)], stdout=log, stderr=subprocess.STDOUT)
                try:
                    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                    auth = 'Basic ' + base64.b64encode(b'fixture-admin:synthetic-admin').decode()
                    for _ in range(200):
                        if process.poll() is not None:
                            self.fail((folder / 'native.log').read_text()[-3000:])
                        try:
                            request = urllib.request.Request(f'http://127.0.0.1:{port}/api/dashboards/uid/pf-app-nextcloud', headers={'Authorization': auth})
                            with opener.open(request, timeout=2) as response:
                                dashboard = json.load(response)
                            break
                        except OSError:
                            time.sleep(.1)
                    else:
                        self.fail('Native dashboard import timed out')
                    self.assertTrue(dashboard['meta']['provisioned'])
                    self.assertEqual(len(dashboard['dashboard']['panels']),19)
                    self.assertEqual(dashboard['dashboard']['panels'][-1]['datasource']['uid'],'prometheus')
                    self.assertFalse(dashboard['dashboard']['editable'])
                finally:
                    process.terminate()
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)


if __name__ == '__main__': unittest.main()
