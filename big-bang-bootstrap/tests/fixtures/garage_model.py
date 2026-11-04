"""Bounded bootstrap engine. Transport and durable private receipt are injected.
Call only under separately approved live scope; fixtures use an in-memory API.
No removal, rotation, adoption, resize, repair or backup operation exists here.
"""
import hashlib,re
from garage_plan import layout_plan,bucket_plan,TAG

def reconcile(api,receipt,save,node_id,key_id,key_secret,allow_first_layout=False):
 fingerprint=hashlib.sha256((node_id+'\0'+key_id+'\0'+key_secret).encode()).hexdigest()
 if not re.fullmatch('GK[a-fA-F0-9]{24}',key_id) or not re.fullmatch('[a-fA-F0-9]{64}',key_secret):raise ValueError('invalid existing application key material')
 if receipt:
  if receipt['scope']!='gitlab-garage-init-v1' or receipt['fingerprint']!=fingerprint or receipt['pending']:raise ValueError('receipt mismatch or uncertain mutation; explicit recovery required')
 else:
  # Object tables cannot be queried before the first layout. Establish only a
  # validated new layout; never adopt a pre-staged or ready unreceipted store.
  initial=layout_plan(api('GetClusterStatus'),api('GetClusterLayout'),node_id)
  if initial['phase']!='stage':raise ValueError('unreceipted existing layout')
  receipt.update(scope='gitlab-garage-init-v1',fingerprint=fingerprint,pending=None,key_imported=False,buckets={});save(receipt)
 changed=0
 def mutate(operation,body,readback):
  nonlocal changed
  receipt['pending']={'operation':operation,'alias':body.get('globalAlias')};save(receipt)
  result=api(operation,body)
  readback(result) # Any failure leaves durable pending, never an automatic retry.
  receipt['pending']=None;save(receipt);changed+=1
 for _ in range(20):
  status=api('GetClusterStatus');layout=api('GetClusterLayout')
  plan=layout_plan(status,layout,node_id)
  if plan['phase']!='ready':
   if not allow_first_layout:raise ValueError('explicit first-layout approval required')
   operation=plan['operations'][0]
   if plan['phase']=='stage':
    def staged(_):
     if layout_plan(api('GetClusterStatus'),api('GetClusterLayout'),node_id)['phase']!='apply-after-preview':raise ValueError('staging readback mismatch')
    mutate('UpdateClusterLayout',operation['body'],staged);continue
   preview=api('PreviewClusterLayoutChanges',{})
   if 'error' in preview or 'newLayout' not in preview:raise ValueError('preview failed')
   projected_status={**status,'layoutVersion':1}
   if layout_plan(projected_status,preview['newLayout'],node_id)['phase']!='ready':raise ValueError('preview scope differs')
   def applied(_):
    if layout_plan(api('GetClusterStatus'),api('GetClusterLayout'),node_id)['phase']!='ready':raise ValueError('layout readback failed')
   mutate('ApplyClusterLayout',{'version':1},applied);continue
  keys=api('ListKeys')
  if any(k['id']!=key_id or k['name']!=TAG for k in keys) or len(keys)>1:raise ValueError('foreign key detected')
  if not keys:
   if receipt['key_imported']:raise ValueError('owned key removed; no automatic recreation')
   def imported(_):
    current=api('GetKeyInfo?id='+key_id)
    if current['accessKeyId']!=key_id or current['name']!=TAG or current['expired'] or current['permissions'].get('createBucket',False) or current['buckets']:raise ValueError('import readback mismatch')
    receipt['key_imported']=True
   mutate('ImportKey',{'accessKeyId':key_id,'secretAccessKey':key_secret,'name':TAG},imported);continue
  if not receipt['key_imported']:raise ValueError('unreceipted key; no adoption')
  listing=api('ListBuckets')
  if len(listing)!=len(receipt['buckets']) or {b['id'] for b in listing}!=set(receipt['buckets'].values()):raise ValueError('unreceipted or missing bucket')
  infos=[api('GetBucketInfo?id='+b['id']) for b in listing]
  plan=bucket_plan(api('GetKeyInfo?id='+key_id),infos,receipt['buckets'],key_id)
  if plan['ready']:return {'changed':changed,'ready':True,'backup_verified':False}
  operation=plan['operations'][0];name=operation['path'].split('/')[-1];body=operation['body']
  if name=='CreateBucket':
   alias=body['globalAlias']
   def created(result):
    bucket_id=result['id']
    if not re.fullmatch('[a-f0-9]{64}',bucket_id):raise ValueError('invalid returned bucket ID')
    current=api('GetBucketInfo?id='+bucket_id)
    if current['id']!=bucket_id or current['globalAliases']!=[alias] or current['keys'] or current['websiteAccess']:raise ValueError('bucket create readback mismatch')
    receipt['buckets'][alias]=bucket_id
   mutate(name,body,created)
  else:
   def granted(_):
    current=api('GetBucketInfo?id='+body['bucketId'])
    expected={'accessKeyId':key_id,'name':TAG,'bucketLocalAliases':[],'permissions':body['permissions']}
    if current['keys']!=[expected]:raise ValueError('grant readback mismatch')
    key=api('GetKeyInfo?id='+key_id)
    matching=[b for b in key['buckets'] if b['id']==body['bucketId']]
    if len(matching)!=1 or matching[0]['permissions']!=body['permissions']:raise ValueError('key grant readback mismatch')
   mutate(name,body,granted)
 raise ValueError('bounded bootstrap operation budget exceeded')
