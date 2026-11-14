"""Native pinned Alloy, synthetic loopback-only API input; no production logs."""
import json,os,socket,subprocess,tempfile,time,unittest,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
class HistoryCutoff(unittest.TestCase):
 def test_old_history_excluded_without_reinterpreting_fresh_application_bytes(self):
  binary=os.environ.get('ALLOY_TEST_BINARY')
  if not binary:self.skipTest('Explicit pinned Alloy binary required')
  active=(ROOT/'configuration/observability/log-boundary/phase-a/boundary-values.yaml').read_text()
  self.assertIn('older_than = "168h"',active);self.assertIn('replacement = "api_plain"',active)
  self.assertIn('v1.18.0',subprocess.check_output([binary,'--version'],text=True))
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);http,metrics=port(),port()
   # Same native parser guards as the pinned chart. Final discovery rule sets
   # api_plain after annotation mapping; it cannot be supplied by app payload.
   stages='''stage.match {
 selector = "{tmp_container_runtime=~\\"containerd|cri-o|\\"}"
 stage.cri {}
}
stage.match {
 selector = "{tmp_container_runtime=\\"docker\\"}"
 stage.docker {}
}
stage.label_drop { values = ["tmp_container_runtime"] }
stage.drop {
 older_than = "168h"
 drop_counter_reason = "outside_loki_ingestion_window"
}'''
   cfg=f'''loki.source.api "test" {{
 use_incoming_timestamp = true
 http {{
  listen_address = "127.0.0.1"
  listen_port = {http}
 }}
 forward_to = [loki.process.test.receiver]
}}
loki.process "test" {{
 {stages}
 forward_to = [loki.echo.test.receiver]
}}
loki.echo "test" {{}}
''';(p/'config.alloy').write_text(cfg)
   with (p/'output').open('w') as output:
    proc=subprocess.Popen([binary,'run','--disable-reporting','--server.http.listen-addr=127.0.0.1:'+str(metrics),'--storage.path='+str(p/'state'),str(p/'config.alloy')],stdout=output,stderr=output)
    try:
     for _ in range(100):
      if proc.poll() is not None:self.fail((p/'output').read_text())
      try:
       with socket.create_connection(('127.0.0.1',http),timeout=.1):break
      except OSError:time.sleep(.05)
     now=time.time_ns();hour=3600*10**9
     lines=['SYNTHETIC_FRESH','2000-01-01T00:00:00Z stdout F SYNTHETIC_CRI_SHAPED','{"log":"SYNTHETIC_DOCKER_SHAPED","stream":"stdout","time":"2000-01-01T00:00:00Z"}','SYNTHETIC_INSIDE_BOUND','SYNTHETIC_OLD_HISTORY','SYNTHETIC_OUTSIDE_BOUND']
     stamps=[now,now+1,now+2,now-168*hour+5*10**9,now-192*hour,now-168*hour-5*10**9]
     body=json.dumps({'streams':[{'stream':{'namespace':'tenant-portal','tmp_container_runtime':'api_plain'},'values':[[str(ts),line] for ts,line in zip(stamps,lines)]}]}).encode()
     req=urllib.request.Request(f'http://127.0.0.1:{http}/loki/api/v1/push',data=body,headers={'Content-Type':'application/json'})
     with urllib.request.urlopen(req,timeout=5) as r:self.assertIn(r.status,[200,204])
     for _ in range(100):
      text=(p/'output').read_text()
      if 'SYNTHETIC_INSIDE_BOUND' in text:break
      time.sleep(.05)
     for line in lines[:4]:self.assertIn(line.replace('"','\\"') if line.startswith('{') else line,text)
     for line in lines[4:]:self.assertNotIn(line,text)
     with urllib.request.urlopen(f'http://127.0.0.1:{metrics}/metrics') as r:prom=r.read().decode()
     matching=[l for l in prom.splitlines() if l.startswith('loki_process_dropped_lines_total{') and 'outside_loki_ingestion_window' in l]
     self.assertEqual(len(matching),1);self.assertTrue(matching[0].endswith(' 2'),matching)
    finally:proc.terminate();proc.wait(timeout=10)
