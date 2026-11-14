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
import urllib.error
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
            (folder/'staged').mkdir()
            for source in (folder/'out').glob('*.json'):source.rename(folder/'staged'/source.name)
            provisioning = folder / 'provisioning/dashboards'
            provisioning.mkdir(parents=True)
            provider = yaml.safe_load((folder / 'out/helm-values.yaml').read_text())['upstream']['dashboardProviders']['perkforge-app-resources.yaml']
            # Fixture-only filesystem mount replacement, never a deployment edit.
            provider['providers'][0]['options']['path'] = str(folder / 'out')
            (folder / 'provider-staged.yaml').write_text(yaml.safe_dump(provider))
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
                        try:
                            opener.open(f'http://127.0.0.1:{port}/api/health',timeout=1).close();break
                        except OSError:time.sleep(.1)
                    def api(method,path,body=None,authorization=auth):
                        req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,headers={'Authorization':authorization,'Content-Type':'application/json'},data=None if body is None else json.dumps(body).encode(),method=method)
                        try:
                            with opener.open(req,timeout=5) as response:return response.status,json.load(response)
                        except urllib.error.HTTPError as e:return e.code,{}
                    self.assertEqual(api('POST','/api/admin/users',{'name':'Fixture Viewer','login':'viewer','password':'fixture-viewer-password'})[0],200)
                    viewer='Basic '+base64.b64encode(b'viewer:fixture-viewer-password').decode()
                    self.assertEqual(api('GET','/api/search',authorization=viewer)[0],200)
                    code,folder_info=api('GET','/api/folders/pf-platform-apps')
                    if code==404:self.assertEqual(api('POST','/api/folders',{'uid':'pf-platform-apps','title':'Platform Applications'})[0],200)
                    self.assertEqual(api('GET','/api/search?folderUIDs=pf-platform-apps&type=dash-db')[1],[])
                    before_acl=api('GET','/api/folders/pf-platform-apps/permissions')[1]
                    current_user=api('GET','/api/user')[1]
                    self.assertTrue(any(x.get('userId')==current_user['id'] and x['permission']==4 for x in before_acl))
                    self.assertEqual(api('POST','/api/folders/pf-platform-apps/permissions',{'items':[{'role':'Admin','permission':4}]})[0],200)
                    creator_id=api('GET','/api/user')[1]['id']
                    # API-created folders include the authenticated creator Admin grant.
                    # Only now publish the already rendered dashboard files to the native watched directory.
                    (provisioning/'logs.yaml').write_text((folder/'provider-staged.yaml').read_text())
                    for source in (folder/'staged').glob('*.json'):
                        (folder/'out'/source.name).write_bytes(source.read_bytes())
                    self.assertEqual(api('POST','/api/admin/provisioning/dashboards/reload',{})[0],200)
                    for _ in range(400):
                        try:code,dashboard=api('GET','/api/dashboards/uid/pf-app-nextcloud')
                        except OSError:time.sleep(.1);continue
                        if code==200:break
                        time.sleep(.1)
                    else:self.fail('Native restricted dashboard import timed out')
                    self.assertTrue(dashboard['meta']['provisioned'])
                    self.assertEqual(len(dashboard['dashboard']['panels']),19)
                    self.assertFalse(dashboard['dashboard']['editable'])
                    self.assertIn(api('GET','/api/dashboards/uid/pf-app-nextcloud',authorization=viewer)[0],[403,404])
                    self.assertEqual(api('GET','/api/search?query=Resources',authorization=viewer),(200,[]))
                    self.assertEqual(api('POST','/api/admin/users',{'name':'Fresh Viewer','login':'fresh','password':'fixture-fresh-password'})[0],200)
                    fresh='Basic '+base64.b64encode(b'fresh:fixture-fresh-password').decode()
                    self.assertIn(api('GET','/api/dashboards/uid/pf-app-nextcloud',authorization=fresh)[0],[403,404])
                    self.assertEqual(api('GET','/api/search?query=Resources',authorization=fresh),(200,[]))
                    self.assertEqual(api('GET','/api/dashboards/uid/pf-app-nextcloud')[0],200)
                finally:
                    process.terminate()
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)


if __name__ == '__main__': unittest.main()
