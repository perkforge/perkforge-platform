#!/usr/bin/env python3
"""One-shot custody coordinator; native configuration remains in Ansible."""
import argparse,fcntl,hashlib,importlib.util,json,os,re,stat,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent

def module(name,file):
 spec=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=module('bootstrap','bootstrap-gitlab.py');guard=module('kc_guard','validate-kc-reader.py')
contract=module('identity_context_contract','../identity_context.py')
Blocked=base.Blocked

class Custody(base.Bao):
 def __init__(self,d,token):
  self.selected=contract.derive(guard.read(d['reader_inputs'])['kc_reader_context'])
  super().__init__(d,token)
 def selection(self):
  return self.selected
 def authority(self):
  selected=self.selection();policy=selected['bootstrap_policy']
  d=self.call('auth/token/lookup-self')['data']
  if d.get('policies')!=[policy] or d.get('identity_policies',[]) or d.get('renewable') is not False or d.get('period',0) or not 900<=d.get('ttl',0)<=3600:raise Blocked('UnapprovedCustodyAuthority')
  actual=self.call('sys/policies/acl/'+policy)['data']['policy']
  if hashlib.sha256(actual.encode()).digest()!=hashlib.sha256(contract.policy_text(selected['context']).encode()).digest():raise Blocked('CustodyPolicyDrift')
 def preflight(self):
  self.authority()
  if self.call('platform/metadata/'+self.selection()['record'],missing=True) is not None:raise Blocked('ExistingCustodyRequiresReview')

def validate(kc_token,bao_token,owned,receipt,inputs,existing=False):
 d=guard.read(inputs)
 patterns={'scope':r'keycloak-reader-custody-v1','setup_id':r'[a-f0-9]{64}','bao_origin':r'https://[A-Za-z0-9.-]+(?::[0-9]+)?','ca_file':r'/[A-Za-z0-9_./-]+','reader_inputs':r'/[A-Za-z0-9_./-]+','foreign_group_id':guard.UUID}
 if not isinstance(d,dict) or set(d)!=set(patterns)|{'run'} or d['run'] is not True:raise Blocked('InvalidSelection')
 if any(not isinstance(d[k],str) or not re.fullmatch(v,d[k]) for k,v in patterns.items()):raise Blocked('NonliteralSelection')
 base.safe(bao_token,limit=4096);base.safe(d['ca_file'],private=False,limit=262144);base.safe(receipt,optional=True)
 if os.path.lexists(receipt) and not existing:raise Blocked('ExistingAttemptRequiresReview')
 guard.validate(kc_token,owned,d['reader_inputs'],'--validate');selection=guard.read(d['reader_inputs']);r=guard.read(owned)
 if selection['kc_reader_allow_enable_permissions'] is not False:raise Blocked('ExistingPermissionsRequired')
 contract.derive(selection['kc_reader_context'])
 if r['stage']!='PendingCustody' or r['permissions_observed_enabled'] is not True or any(not re.fullmatch(guard.UUID,r[k]) for k in ('reader_client_id','service_account_id','permissions_client_id','policy_id','permission_id')):raise Blocked('OwnedDisabledSetupRequired')
 if d['foreign_group_id'] in r['group_ids'].values():raise Blocked('ForeignProbeRequired')
 return d

def run_play(kc_token,bao_token,owned,receipt,inputs,d):
 # All configuration/API writes stay in the native Ansible play. Secrets never
 # pass in argv or stdout; only protected file paths and fixed source variables.
 env=os.environ.copy();env['PERKFORGE_GROUP_LOCK_OWNER']=str(os.getpid())
 argv=['ansible-playbook','-i','localhost,',str(HERE/'keycloak-custody.yaml'),'-e','@'+d['reader_inputs'],'-e','@'+inputs]
 for key,value in {'kc_setup_token_file':kc_token,'kc_setup_receipt_file':owned,'kc_setup_inputs_file':d['reader_inputs'],'custody_token_file':bao_token,'custody_receipt_file':receipt,'custody_inputs_file':inputs}.items():argv+=['-e',key+'='+value]
 p=subprocess.run(argv,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=240)
 if p.returncode:raise Blocked('NativeActivationFailed')

def lock(path):
 base.safe(path,optional=True,limit=0)
 fd=os.open(path,os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK|(os.O_CREAT|os.O_EXCL if not os.path.lexists(path) else 0),0o600)
 s=os.fstat(fd)
 if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600 or s.st_nlink!=1 or s.st_size:os.close(fd);raise Blocked('UnsafeLock')
 fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);return fd

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='inert');p.add_argument('paths',nargs='*');a=p.parse_args();fds=[]
 if a.mode not in ('validate','apply','locked-preflight'):print('INERT');return 0
 try:
  if len(a.paths)!=5:raise Blocked('InvalidPaths')
  kc,bao,owned,receipt,inputs=a.paths;d=validate(*a.paths,existing=a.mode=='locked-preflight')
  selected=contract.derive(guard.read(d['reader_inputs'])['kc_reader_context'])
  if a.mode=='locked-preflight':
   guard.verify(kc,owned,require_locked=True);guard.verify(bao,receipt,require_locked=True)
   r=guard.read(receipt)
   if r.get('setup_id')!=d['setup_id'] or r.get('stage')!='ActivationRequested' or r.get('context')!=selected['context'] or r.get('context_digest')!=selected['digest']:raise Blocked('ForeignAttempt')
   Custody(d,bao).preflight();print('Owned custody preflight verified');return 0
  if a.mode=='validate':print('Validated; zero native requests');return 0
  for path in (owned+'.lock',receipt+'.lock'):fds.append(lock(path))
  d=validate(*a.paths);Custody(d,bao).preflight()
  base.save(receipt,{'schema':1,'context':selected['context'],'context_digest':selected['digest'],'setup_id':d['setup_id'],'stage':'ActivationRequested','client_id':guard.read(owned)['reader_client_id']},first=True)
  run_play(kc,bao,owned,receipt,inputs,d)
  r=guard.read(receipt)
  if r.get('stage')!='ReaderAccessVerified':raise Blocked('ActivationUnverified')
  print(json.dumps({'stage':'ReaderAccessVerified','runtime_deployed':False}));return 0
 except Exception:
  print('{"stage":"ManualReviewRequired","category":"SelectionCustodyOrActivationUnverified","runtime_deployed":false}');return 1
 finally:
  for fd in reversed(fds):os.close(fd)
if __name__=='__main__':raise SystemExit(main())
