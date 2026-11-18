"""Pinned native processing fixture; synthetic only, not live ingestion acceptance."""
import json, os, socket, subprocess, tempfile, time, unittest
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]
CASES = [
 ('GET /callback?token=sample&x=1', 'GET /callback?token=REDACTED'),
 ('x=1&password=sample', 'x=1&password=REDACTED'),
 ('[secret=sample]', '[secret=REDACTED'),
 ('password=sample', 'password=REDACTED'),
 ('TOKEN: sample', 'TOKEN: REDACTED'),
 ('secret = sample', 'secret = REDACTED'),
 ('api_key=sample', 'api_key=REDACTED'),
 ('api-key=sample', 'api-key=REDACTED'),
 ('password="two words"', 'password="REDACTED"'),
 ("secret='two words'", "secret='REDACTED'"),
 ('{"password":"sample","ok":42}', '{"password":"REDACTED","ok":42}'),
 ('{"TOKEN" : "sample", "api_key":"sample"}', '{"TOKEN" : "REDACTED", "api_key":"REDACTED"}'),
 ('{"secret":"a\\\"b\\\\c"}', '{"secret":"REDACTED"}'),
 ('Authorization: Bearer abc.def-ghi', 'Authorization: Bearer REDACTED'),
 ('authorization=Basic YWJjZA==', 'authorization=Basic REDACTED'),
 ('{"Authorization":"Bearer abc.def"}', '{"Authorization":"Bearer REDACTED"}'),
 ('password=first,token=second;secret=third', 'password=REDACTED,token=REDACTED;secret=REDACTED'),
 ('password=""', 'password="REDACTED"'),
 ('password=two words', 'password=REDACTED words'),  # Deliberate ambiguity limit.
 ('token_count=4 secretary=ok some_api_key=public', 'token_count=4 secretary=ok some_api_key=public'),
 ('request_id=abc /api/key timestamp=2026-11-18', 'request_id=abc /api/key timestamp=2026-11-18'),
 ('{"token":null,"secret":false}', '{"token":null,"secret":false}'),
 ('password="unterminated words', 'password="unterminated words'),
 ('benign_message=hello', 'benign_message=hello'),
]
class RedactionNative(unittest.TestCase):
 def test_source_generated_stages_match(self):
  stage=yaml.safe_load((ROOT/'configuration/observability/candidate-values.yaml').read_text())['alloy']['values']['upstream']['podLogsViaKubernetesApi']['extraLogProcessingStages']
  for phase in ('phase-a','phase-b'):
   generated=yaml.safe_load((ROOT/f'configuration/observability/log-boundary/{phase}/boundary-values.yaml').read_text())['alloy']['values']['upstream']['podLogsViaKubernetesApi']['extraLogProcessingStages']
   self.assertTrue(generated.startswith(stage))
 def test_native_explicit_formats(self):
  binary=os.environ.get('ALLOY_VALIDATE_BIN')
  if not binary:self.skipTest('Set ALLOY_VALIDATE_BIN to verified Alloy v1.18.0/a435563')
  stage=yaml.safe_load((ROOT/'configuration/observability/candidate-values.yaml').read_text())['alloy']['values']['upstream']['podLogsViaKubernetesApi']['extraLogProcessingStages']
  with tempfile.TemporaryDirectory(prefix='pf-redaction-native-') as d:
   p=Path(d);env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'HOME':d,'KUBECONFIG':'/dev/null'}
   v=subprocess.run([binary,'--version'],env=env,capture_output=True,text=True,check=True,timeout=10)
   self.assertIn('version v1.18.0 ',v.stdout);self.assertIn('revision: a435563',v.stdout)
   (p/'input.log').write_text('\n'.join(x[0] for x in CASES)+'\n')
   config='logging { level = "info"\n format = "json" }\nloki.source.file "fixture" {\n targets = [{__path__ = '+json.dumps(str(p/'input.log'))+', job = "synthetic"}]\n forward_to = [loki.process.fixture.receiver]\n}\nloki.process "fixture" {\n'+stage+' forward_to = [loki.echo.fixture.receiver]\n}\nloki.echo "fixture" {}\n'
   (p/'config.alloy').write_text(config)
   v=subprocess.run([binary,'validate',str(p/'config.alloy')],env=env,capture_output=True,text=True,timeout=15);self.assertEqual(v.returncode,0,v.stderr)
   with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
   with (p/'output').open('w') as out:
    proc=subprocess.Popen([binary,'run','--disable-reporting',f'--server.http.listen-addr=127.0.0.1:{port}','--storage.path='+str(p/'state'),str(p/'config.alloy')],env=env,stdout=out,stderr=subprocess.STDOUT)
    try:
     for _ in range(100):
      if (p/'output').read_text().count('received log entry') >= len(CASES):break
      if proc.poll() is not None:break
      time.sleep(.1)
    finally:
     proc.terminate()
     try:proc.wait(timeout=10)
     except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
   self.assertEqual(proc.returncode,0)
   entries=[]
   for line in (p/'output').read_text().splitlines():
    try:event=json.loads(line)
    except json.JSONDecodeError:continue
    if event.get('msg')=='received log entry':entries.append(event['entry'])
   self.assertEqual(entries,[x[1] for x in CASES])
   for (original,_),actual in zip(CASES,entries):
    if original.startswith('{'):json.loads(actual)
if __name__=='__main__':unittest.main()
