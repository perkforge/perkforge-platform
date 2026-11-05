"""Offline first-layout planner for pinned Garage 2.2.0 GET representations.
No API transport or writes. Each proposed mutation needs fresh review and readback;
never initialize, adopt, resize or reconfigure an existing foreign store.
"""
import re
CAPACITY=28*1024**3  # 32Gi PVC minus 4Gi filesystem/operational headroom.
TAG='perkforge-gitlab-data-v1'

def layout_plan(status,layout,node_id):
 if not re.fullmatch('[a-f0-9]{64}',node_id):raise ValueError('full reviewed node ID required')
 if len(status['nodes'])!=1:raise ValueError('expected one dedicated Garage node')
 node=status['nodes'][0]
 if node['id']!=node_id or node['isUp'] is not True or node['draining'] is not False or node['garageVersion'] not in ('2.2.0','v2.2.0'):raise ValueError('node identity/version/health mismatch')
 if layout['version']!=status['layoutVersion'] or type(layout['version']) is not int:raise ValueError('stale or invalid layout version')
 desired={'id':node_id,'zone':'gitlab-local','capacity':CAPACITY,'tags':[TAG]}
 staged=layout['stagedRoleChanges']
 if layout.get('stagedParameters') is not None:raise ValueError('unexpected staged parameter change')
 if layout['roles']:
  if layout['version']!=1 or len(layout['roles'])!=1 or staged:raise ValueError('existing layout differs')
  if {k:layout['roles'][0][k] for k in desired}!=desired:raise ValueError('refuse layout adoption or resizing')
  return {'phase':'ready','operations':[],'bucket_initialization_complete':False}
 if layout['version']!=0:raise ValueError('only new version-zero stores can initialize')
 space=node['dataPartition']
 if space is None or space['total']<CAPACITY+2*1024**3 or space['available']<CAPACITY:raise ValueError('insufficient initial data space')
 if not staged:
  return {'phase':'stage','operations':[{'method':'POST','path':'/v2/UpdateClusterLayout','body':{'roles':[desired]}}],'bucket_initialization_complete':False}
 # GET stagedRoleChanges has the same assigned role fields plus optional values;
 # accept only this exact change, never blanket-apply somebody else's staging.
 if staged!=[desired]:raise ValueError('foreign staged layout change')
 return {'phase':'apply-after-preview','operations':[{'method':'POST','path':'/v2/ApplyClusterLayout','body':{'version':1}}],'preview_required':True,'bucket_initialization_complete':False}

BUCKETS=('gitlab-lfs','gitlab-artifacts','gitlab-uploads','gitlab-packages','gitlab-backup-staging','gitlab-restore-staging')
PERMISSIONS={'read':True,'write':True,'owner':False}

def bucket_plan(key_info,bucket_infos,receipt,access_key_id):
 """Plan missing buckets/grants only; require an owner-held ID receipt to resume.
 GET key info must be collected WITHOUT showSecretKey. Creation responses must be
 privately recorded before resuming; an uncertain create cannot be auto-adopted.
 This function never imports, creates or emits a credential.
 """
 if key_info.get('secretAccessKey') is not None:raise ValueError('secret-free GET representation required')
 if key_info['accessKeyId']!=access_key_id or key_info['name']!=TAG or key_info['expired'] is not False or key_info.get('expiration') is not None or key_info['permissions'].get('createBucket',False) is not False:raise ValueError('dedicated non-creating unexpired key required')
 if set(receipt)-set(BUCKETS) or len(set(receipt.values()))!=len(receipt):raise ValueError('invalid bucket ownership receipt')
 indexed={b['id']:b for b in bucket_infos}
 if len(indexed)!=len(bucket_infos) or set(indexed)!=set(receipt.values()):raise ValueError('unreceipted bucket or stale ownership receipt')
 key_buckets={b['id']:b for b in key_info['buckets']}
 if len(key_buckets)!=len(key_info['buckets']) or set(key_buckets)-set(indexed):raise ValueError('unexpected key bucket access')
 operations=[]
 # Validate all existing objects BEFORE emitting any proposed mutation.
 for alias,bucket_id in receipt.items():
  bucket=indexed[bucket_id]
  if bucket['globalAliases']!=[alias] or bucket['websiteAccess'] is not False:raise ValueError('foreign alias or website exposure')
  for key in bucket['keys']:
   if key['accessKeyId']!=access_key_id or key['name']!=TAG or key['bucketLocalAliases'] or key['permissions']!=PERMISSIONS:raise ValueError('unexpected bucket key/ownership')
  grants=key_buckets.get(bucket_id)
  if grants and (grants['globalAliases']!=[alias] or grants['localAliases'] or grants['permissions']!=PERMISSIONS):raise ValueError('unexpected effective key permissions')
  if bool(bucket['keys'])!=bool(grants):raise ValueError('inconsistent bucket/key snapshot; reread')
 for alias in BUCKETS:
  if alias not in receipt:
   operations.append({'method':'POST','path':'/v2/CreateBucket','body':{'globalAlias':alias},'record_returned_id_before_resume':True})
  elif not indexed[receipt[alias]]['keys']:
   operations.append({'method':'POST','path':'/v2/AllowBucketKey','body':{'bucketId':receipt[alias],'accessKeyId':access_key_id,'permissions':PERMISSIONS.copy()}})
 return {'operations':operations,'ready':not operations,'credentials_created':False,'independent_backup':False}
