"""Real Ansible, synthetic HTTPS KV and fake kubectl; no live APIs."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler
import json
import os
import subprocess
from security import test_mattermost_context as fixture
import yaml

class GuardedUpdate(fixture.MattermostFixture):
    def test_same_record_cas_payload_and_stale_hash_denial(self):
        self.play=fixture.ROOT/'big-bang-bootstrap/configuration/observability/platform-alerts/update-mattermost.yaml'
        prior={'apiVersion':1,'groups':[{'name':'preserved'}],'contactPoints':[{'name':'platform-resource-ntfy','receivers':[{'uid':'pf-platform-resource-ntfy','private':'retained'}]}]}
        old=yaml.safe_dump(prior); hook=self.origin+'/hooks/'+'h'*26
        desired=json.loads(json.dumps(prior)); desired['contactPoints'][0]['receivers'].append({'uid':'pf-platform-resource-mattermost','type':'webhook','settings':{'url':hook,'tlsConfig':{'insecureSkipVerify':False},'payload':{'template':'{"text":"portal: firing; 1 grouped alert(s)."}'}}})
        new=yaml.safe_dump(desired); (self.d/'alerting.yaml').write_text(new)
        (self.d/'hook').write_text(hook)
        state=self.d/'kv.json'; state.write_text(json.dumps({'version':4,'text':old,'writes':0}))
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def reply(self,code,obj):
                self.send_response(code); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(json.dumps(obj).encode())
            def do_GET(self):
                x=json.loads(state.read_text())
                if self.path=='/v1/sys/health': return self.reply(200,{'cluster_id':'bao-id','sealed':False})
                assert self.path=='/v1/platform/data/fixture/portal'
                self.reply(200,{'data':{'data':{'alerting.yaml':x['text']},'metadata':{'version':x['version']}}})
            def do_POST(self):
                assert self.path=='/v1/platform/data/fixture/portal'
                x=json.loads(state.read_text()); body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                assert body['options']['cas']==x['version'] and list(body['data'])==['alerting.yaml']
                x.update(version=x['version']+1,text=body['data']['alerting.yaml'],writes=x['writes']+1); state.write_text(json.dumps(x)); self.reply(200,{})
        self.server.RequestHandlerClass=Handler
        binary=self.d/'kubectl'; binary.write_text('''#!/usr/bin/env python3
import json,sys,base64
from pathlib import Path
a=sys.argv[1:]
if a[:3]==['get','namespace','kube-system']: print('cluster-id')
elif 'get' in a and 'externalsecret' in a:
 print(json.dumps({'spec':{'target':{'name':'grafana-platform-alerts'},'secretStoreRef':{'name':'eso-platform-alerts'},'data':[{'secretKey':'alerting.yaml','remoteRef':{'key':'fixture/portal','property':'alerting.yaml'}}]}}))
elif 'get' in a and 'secret' in a:
 x=json.loads(Path(__file__).with_name('kv.json').read_text());print(json.dumps({'data':{'alerting.yaml':base64.b64encode(x['text'].encode()).decode()}}))
else: assert 'annotate' in a or 'wait' in a
'''); binary.chmod(0o700)
        values=dict(platform_mattermost_update=True,platform_mattermost_update_approved=True,platform_mattermost_enabled=True,grafana_ntfy_context='platform',grafana_ntfy_secret='grafana-platform-alerts',grafana_ntfy_monitoring_namespace='monitoring',grafana_ntfy_record='fixture/portal',grafana_ntfy_previous_sha256=hashlib.sha256(old.encode()).hexdigest(),grafana_ntfy_bao_server=self.origin,grafana_ntfy_bao_cluster_id='bao-id',grafana_ntfy_cluster_uid='cluster-id',grafana_ntfy_bao_ca_file=str(self.d/'ca'),grafana_ntfy_bao_token_file=str(self.d/'token'),grafana_ntfy_output_dir=str(self.d),grafana_mattermost_hook_url_file=str(self.d/'hook'),grafana_mattermost_ca_file=str(self.d/'ca'),grafana_mattermost_triage_url='https://grafana.example.invalid/alerting/list')
        def run(changes={}):
            result=subprocess.run(['ansible-playbook','-i','localhost,',str(self.play),'-e',json.dumps(values|changes)],env={**os.environ,'PATH':str(self.d)+':'+os.environ['PATH'],'KUBECONFIG':'/dev/null'},capture_output=True,text=True,timeout=40)
            self.assertNotIn(hook,result.stdout+result.stderr); self.assertNotIn('fixture-secret-token',result.stdout+result.stderr); return result
        r=run({'grafana_ntfy_previous_sha256':'0'*64}); self.assertNotEqual(r.returncode,0); self.assertEqual(json.loads(state.read_text())['writes'],0)
        r=run(); self.assertEqual(r.returncode,0,r.stdout+r.stderr); self.assertEqual(json.loads(state.read_text())['writes'],1)
        current=yaml.safe_load(json.loads(state.read_text())['text']);self.assertEqual(current['groups'],prior['groups']);self.assertEqual(current['contactPoints'][0]['receivers'][0],prior['contactPoints'][0]['receivers'][0]);self.assertNotIn('channel',current['contactPoints'][0]['receivers'][1]['settings']['payload']['template'])
        r=run(); self.assertEqual(r.returncode,0,r.stdout+r.stderr); self.assertEqual(json.loads(state.read_text())['writes'],1)
        current=yaml.safe_load(json.loads(state.read_text())['text']);self.assertEqual(current['groups'],prior['groups']);self.assertEqual(current['contactPoints'][0]['receivers'][0],prior['contactPoints'][0]['receivers'][0]);self.assertNotIn('channel',current['contactPoints'][0]['receivers'][1]['settings']['payload']['template'])
