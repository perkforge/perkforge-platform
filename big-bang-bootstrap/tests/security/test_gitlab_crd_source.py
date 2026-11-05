"""Synthetic public chart transport/extraction; never contacts a Kubernetes API."""
from pathlib import Path
import hashlib,io,json,os,subprocess,tarfile,tempfile,threading,unittest,yaml
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[2]
class CRDSource(unittest.TestCase):
 def test_checksum_private_cache_fresh_render_repeat_and_corruption_refusal(self):
  with tempfile.TemporaryDirectory(prefix='cnpg-source-fixture-') as directory:
   p=Path(directory);cache=p/'cache';cache.mkdir(mode=0o700);packages=p/'packages';pkg=packages/'cloudnative-pg';pkg.mkdir(parents=True)
   templates=[]
   for index in range(11):templates.append({'apiVersion':'apiextensions.k8s.io/v1','kind':'CustomResourceDefinition','metadata':{'name':f'test{index}.postgresql.cnpg.io'},'spec':{'group':'postgresql.cnpg.io'}})
   files={'cloudnative-pg/Chart.yaml':'apiVersion: v2\nname: cloudnative-pg\nversion: 0.29.1\n','cloudnative-pg/values.yaml':'crds: {create: false}\n','cloudnative-pg/templates/crds.yaml':'{{- if .Values.crds.create }}\n'+yaml.safe_dump_all(templates)+'{{- end }}\n'}
   stream=io.BytesIO()
   with tarfile.open(fileobj=stream,mode='w:gz') as archive:
    for name,text in files.items():
     data=text.encode();entry=tarfile.TarInfo(name);entry.size=len(data);archive.addfile(entry,io.BytesIO(data))
   payload=stream.getvalue();requests=[]
   class H(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
     requests.append(self.path);self.send_response(200);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
   server=ThreadingHTTPServer(('127.0.0.1',0),H);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    pin={'url':f'http://127.0.0.1:{server.server_port}/chart.tgz','sha256':hashlib.sha256(payload).hexdigest(),'chart_directory':'cloudnative-pg','chart_version':'0.29.1'}
    (pkg/'source-pin.yaml').write_text(yaml.safe_dump(pin));(pkg/'values.yaml').write_text('crds: {create: false}\n')
    wrapper=[{'hosts':'localhost','connection':'local','gather_facts':False,'vars':{'gitlab_foundation_cache':str(cache),'gitlab_package_directory':str(packages)},'tasks':[{'ansible.builtin.include_tasks':str(ROOT/'configuration/ansible/tasks/render-cnpg-crds.yaml')},{'ansible.builtin.assert':{'that':'gitlab_cnpg_crds | length == 11'}}]}]
    play=p/'fixture.yaml';play.write_text(yaml.safe_dump(wrapper));env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(p/'local'),'ANSIBLE_REMOTE_TEMP':str(p/'remote')}
    def run():return subprocess.run(['ansible-playbook','-i','localhost,',str(play)],env=env,capture_output=True,text=True,timeout=45)
    first=run();self.assertEqual(first.returncode,0,first.stdout+first.stderr);self.assertEqual(requests,['/chart.tgz']);self.assertEqual([x.name for x in cache.iterdir()],['cloudnative-pg-0.29.1.tgz'])
    second=run();self.assertEqual(second.returncode,0,second.stdout+second.stderr);self.assertIn('changed=0',second.stdout);self.assertEqual(requests,['/chart.tgz'])
    archive_path=cache/'cloudnative-pg-0.29.1.tgz';archive_path.write_bytes(b'corrupt');before=len(requests);failed=run();self.assertNotEqual(failed.returncode,0);self.assertEqual(len(requests),before);self.assertEqual(archive_path.read_bytes(),b'corrupt')
   finally:server.shutdown();server.server_close();thread.join(timeout=2)
