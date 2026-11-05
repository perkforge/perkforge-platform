#!/usr/bin/env python3
"""Explicit cached-image CNG transport check; no pull, login or live database."""
import argparse,json,os
from pathlib import Path
import shutil,subprocess,tempfile
IMAGE='registry1.dso.mil/gitlab/gitlab-org/build/cng/gitlab-webservice-ee@sha256:023ca782c03d12ca653e86bcb1b6bb03ba175a0ee29cef95f8bc425f8055e9c3'
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true',help='run a disposable offline container from the already cached exact image');args=parser.parse_args()
 if not args.run:
  print(json.dumps({'executed':False,'reason':'explicit --run required; no tools or APIs contacted'}));return 0
 if not all(shutil.which(x) for x in ('podman','openssl')):raise RuntimeError('existing Podman/OpenSSL required; no installation or pull attempted')
 subprocess.run(['podman','image','exists',IMAGE],check=True,timeout=15)
 with tempfile.TemporaryDirectory(prefix='gitlab-cng-transport-') as directory:
  p=Path(directory)
  def openssl(*a):subprocess.run(['openssl',*a],cwd=p,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=15)
  for name in ('ca','other'):openssl('req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=Offline '+name,'-keyout',name+'.key','-out',name+'.crt')
  openssl('req','-newkey','rsa:2048','-nodes','-subj','/CN=postgres.fixture.invalid','-keyout','server.key','-out','server.csr')
  (p/'extensions').write_text('subjectAltName=DNS:postgres.fixture.invalid\nextendedKeyUsage=serverAuth\n')
  openssl('x509','-req','-in','server.csr','-CA','ca.crt','-CAkey','ca.key','-CAcreateserial','-out','server.crt','-days','1','-extfile','extensions')
  shutil.copy2(Path(__file__).with_name('gitlab-cng-tls.rb'),p/'check.rb')
  for f in p.iterdir():f.chmod(0o600)
  command=['podman','run','--rm','--pull=never','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--userns=keep-id','--user',f'{os.getuid()}:{os.getgid()}','--memory=1g','--cpus=1','--pids-limit=128','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--volume',str(p)+':/fixture:ro','--workdir','/srv/gitlab','--entrypoint','/bin/sh',IMAGE,'-c','bundle exec ruby /fixture/check.rb /fixture']
  result=subprocess.run(command,capture_output=True,text=True,timeout=90)
  if result.returncode:
   try:
    failed=json.loads(result.stdout.strip().splitlines()[-1]);summary=json.dumps({'results':failed.get('results',{}),'diagnostics':failed.get('diagnostics',{}),'runtime':{k:failed.get(k) for k in ('gitlab_version','active_record','pg','libpq')}})
   except (ValueError,IndexError):summary='no JSON result'
   raise RuntimeError('CNG fixture failed; '+summary+'; '+result.stderr[-3000:])
  evidence=json.loads(result.stdout.strip().splitlines()[-1]);evidence['image']=IMAGE;evidence['scope']='isolated ActiveRecord/PG TLS, not full GitLab/database/application acceptance'
  print(json.dumps(evidence,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
