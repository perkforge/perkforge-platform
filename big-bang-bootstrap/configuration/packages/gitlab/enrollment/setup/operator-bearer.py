"""Strict local token verification; no network or credential writes."""
import json,os,re,stat,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from verify_group_paths import safe
def read_bearer(path,now=None):
 safe(path,limit=4096)
 before=os.lstat(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  s=os.fstat(fd)
  if (s.st_dev,s.st_ino)!=(before.st_dev,before.st_ino) or not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600 or s.st_nlink!=1 or s.st_size>4096:raise ValueError()
  raw=os.read(fd,4097).decode().strip()
 finally:os.close(fd)
 if raw.startswith('{'):
  def unique(pairs):
   d={}
   for k,v in pairs:
    if k in d:raise ValueError()
    d[k]=v
   return d
  d=json.loads(raw,object_pairs_hook=unique)
  if set(d)!={'access_token','expires_at'} or type(d['expires_at']) not in (int,float):raise ValueError()
  current=time.time() if now is None else now
  if not 15 < d['expires_at']-current <= 3600:raise ValueError()
  raw=d['access_token']
 if not isinstance(raw,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{8,4000}',raw):raise ValueError()
 return raw
