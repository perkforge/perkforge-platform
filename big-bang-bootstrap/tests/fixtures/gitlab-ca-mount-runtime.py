"""Explicit offline opt-in: cached exact CNG image, no credentials/network/pulls."""
import json,subprocess,tempfile
from pathlib import Path
IMAGE='registry1.dso.mil/gitlab/gitlab-org/build/cng/gitlab-webservice-ee:v19.4.2-ubi'
DIGEST='sha256:023ca782c03d12ca653e86bcb1b6bb03ba175a0ee29cef95f8bc425f8055e9c3'
r=subprocess.run(['podman','image','inspect',IMAGE,'--format','{{json .RepoDigests}}'],capture_output=True,text=True,timeout=15)
assert r.returncode==0,'Exact image must already be cached; this fixture never pulls'
assert any(x.endswith('@'+DIGEST) for x in json.loads(r.stdout))
with tempfile.TemporaryDirectory(prefix='gitlab-ca-mount-') as d:
 p=Path(d);p.chmod(0o755);(p/'config').mkdir(mode=0o755);(p/'ca').mkdir(mode=0o755)
 (p/'config/example').write_text('synthetic configuration only\n');(p/'ca/ca.crt').write_text('synthetic public certificate placeholder\n')
 def run(mount):
  args=['podman','run','--rm','--pull=never','--network=none','--read-only','--user=0','--entrypoint=/bin/sh','--volume',str(p/'config')+':/etc/gitlab:ro,Z','--volume',str(p/'ca')+':'+mount+':ro,Z','--env','PGSSLMODE=verify-full','--env','PGSSLROOTCERT='+mount+'/ca.crt',IMAGE,'-ec','test "$PGSSLMODE" = verify-full; test -r "$PGSSLROOTCERT"; if touch /etc/gitlab/forbidden 2>/dev/null; then exit 42; fi; if touch "$(dirname "$PGSSLROOTCERT")/forbidden" 2>/dev/null; then exit 43; fi; echo readonly-mount-check-passed']
  if mount=='/etc/gitlab/database-ca':
   # Podman can precreate nested destinations on the bind source, unlike the
   # observed kubelet/runc path. Test the underlying read-only mkdir directly.
   i=args.index('--volume',args.index('--volume')+1);del args[i:i+2]
   args[-1]='mkdir /etc/gitlab/database-ca'
  return subprocess.run(args,capture_output=True,text=True,timeout=30)
 old=run('/etc/gitlab/database-ca');new=run('/etc/gitlab-postgres-ca')
 assert old.returncode!=0 and 'read-only file system' in old.stderr.lower(),'Read-only directory creation failure not reproduced: '+old.stderr
 assert new.returncode==0 and 'readonly-mount-check-passed' in new.stdout,'Sibling mount did not pass: '+new.stderr
 print(json.dumps({'image_digest':DIGEST,'network':'none','pull':'never','credentials_mounted':False,'root_filesystem_read_only':True,'read_only_parent_rejects_nested_directory_creation':True,'new_sibling_mount_readable':True,'configuration_and_ca_mounts_remain_read_only':True},indent=2))
