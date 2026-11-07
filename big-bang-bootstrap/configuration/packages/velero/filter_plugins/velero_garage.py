"""Verify only the dedicated one-node, one-bucket store; never adopt GitLab state."""
import re

def garage_layout_verdict(status,layout,node,expected):
 if not re.fullmatch('[a-f0-9]{64}',node) or len(status['nodes'])!=1:raise ValueError('node identity')
 n=status['nodes'][0]
 if n['id']!=node or n['isUp'] is not True or n['draining'] is not False or n['garageVersion'] not in ('2.2.0','v2.2.0'):raise ValueError('node health/version')
 if (not isinstance(layout['version'],int) or isinstance(layout['version'],bool)) or layout['version']!=status['layoutVersion'] or layout.get('stagedParameters') is not None:raise ValueError('layout drift')
 staged=layout['stagedRoleChanges']
 if layout['roles']:
  if layout['version']!=1 or len(layout['roles'])!=1 or staged or {k:layout['roles'][0][k] for k in expected}!=expected:raise ValueError('existing layout mismatch')
  phase='ready'
 else:
  space=n['dataPartition']
  if layout['version']!=0 or space is None or space['total']<expected['capacity']+2*1024**3 or space['available']<expected['capacity']:raise ValueError('initial layout space/version')
  if staged and staged!=[expected]:raise ValueError('foreign staging')
  phase='apply' if staged else 'stage'
 return phase

def garage_verdict(status,layout,keys,key,infos,receipt,node,key_id,expected,buckets):
 phase=garage_layout_verdict(status,layout,node,expected)
 if phase!='ready':
  if keys is not None or key or infos or receipt['key_imported'] is not False or receipt['buckets']:raise ValueError('pre-layout store must have a pristine receipt; no object snapshot')
  return {'phase':phase,'missing':list(buckets),'ungranted':[]}
 if not isinstance(keys,list):raise ValueError('ready layout requires real object snapshot')
 if len(keys)>1 or any(k['id']!=key_id or k['name']!='perkforge-velero-data-v1' for k in keys):raise ValueError('foreign key')
 if bool(keys)!=receipt['key_imported']:raise ValueError('unreceipted/missing key')
 owned=receipt['buckets']
 if set(owned)-set(buckets) or len(set(owned.values()))!=len(owned):raise ValueError('invalid receipt')
 indexed={b['id']:b for b in infos}
 if len(indexed)!=len(infos) or set(indexed)!=set(owned.values()):raise ValueError('unreceipted/missing bucket')
 ungranted=[]
 if keys:
  if key.get('secretAccessKey') is not None or key['accessKeyId']!=key_id or key['name']!='perkforge-velero-data-v1' or key['expired'] is not False or key.get('expiration') is not None or key['permissions'].get('createBucket',False) is not False:raise ValueError('unexpected key authority')
  kb={b['id']:b for b in key['buckets']}
  if len(kb)!=len(key['buckets']) or set(kb)-set(indexed):raise ValueError('unexpected key bucket')
  permissions={'read':True,'write':True,'owner':False}
  for alias,identifier in owned.items():
   b=indexed[identifier]
   if b['globalAliases']!=[alias] or b['websiteAccess'] is not False:raise ValueError('foreign alias/website')
   if len(b['keys'])>1:raise ValueError('extra key grant')
   for grant in b['keys']:
    if grant!={'accessKeyId':key_id,'name':'perkforge-velero-data-v1','bucketLocalAliases':[],'permissions':permissions}:raise ValueError('expanded grant')
   if bool(b['keys'])!=bool(kb.get(identifier)):raise ValueError('inconsistent grant readback')
   if identifier in kb and (kb[identifier]['globalAliases']!=[alias] or kb[identifier]['localAliases'] or kb[identifier]['permissions']!=permissions):raise ValueError('expanded key authority')
   if not b['keys']:ungranted.append(alias)
 elif infos:raise ValueError('buckets without owned key')
 return {'phase':phase,'missing':[b for b in buckets if b not in owned],'ungranted':ungranted}
class FilterModule:
 def filters(self):return {"velero_garage_layout_verdict":garage_layout_verdict,"velero_garage_verdict":garage_verdict}
