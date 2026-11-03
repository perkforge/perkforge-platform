from pathlib import Path
import copy,importlib.util,unittest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('garage_plan',ROOT/'tests/fixtures/garage_plan.py');garage=importlib.util.module_from_spec(spec);spec.loader.exec_module(garage)
class GarageLayout(unittest.TestCase):
 def fixture(self):
  node='a'*64
  return node,{'layoutVersion':0,'nodes':[{'id':node,'isUp':True,'draining':False,'garageVersion':'2.2.0','dataPartition':{'available':31*1024**3,'total':31*1024**3}}]},{'version':0,'roles':[],'parameters':{},'partitionSize':0,'stagedRoleChanges':[],'stagedParameters':None}
 def test_new_stage_partial_resume_apply_then_repeat(self):
  node,status,layout=self.fixture();plan=garage.layout_plan(status,layout,node)
  self.assertEqual(plan['phase'],'stage');self.assertEqual(len(plan['operations']),1)
  role=plan['operations'][0]['body']['roles'][0];self.assertEqual(role['capacity'],28*1024**3)
  layout['stagedRoleChanges']=[role]
  plan=garage.layout_plan(status,layout,node);self.assertEqual(plan['phase'],'apply-after-preview');self.assertTrue(plan['preview_required']);self.assertEqual(plan['operations'][0]['body'],{'version':1})
  status['layoutVersion']=layout['version']=1;layout['roles']=[{**role,'usableCapacity':27*1024**3,'storedPartitions':256}];layout['stagedRoleChanges']=[]
  plan=garage.layout_plan(status,layout,node);self.assertEqual(plan['operations'],[]);self.assertFalse(plan['bucket_initialization_complete'])
 def test_foreign_staging_stale_identity_low_space_and_resize_refused(self):
  node,status,layout=self.fixture()
  cases=[]
  l=copy.deepcopy(layout);l['stagedRoleChanges']=[{'id':node,'remove':True}];cases.append((status,l,node))
  l=copy.deepcopy(layout);l['stagedParameters']={};cases.append((status,l,node))
  l=copy.deepcopy(layout);l['version']=1;cases.append((status,l,node))
  s=copy.deepcopy(status);s['nodes'][0]['dataPartition']['available']=1;cases.append((s,layout,node))
  s=copy.deepcopy(status);s['nodes'][0]['garageVersion']='2.1.0';cases.append((s,layout,node))
  cases.append((status,layout,node[:8]))
  for s,l,n in cases:
   with self.subTest(snapshot=l),self.assertRaises(ValueError):garage.layout_plan(s,l,n)
 def test_bucket_creation_partial_resume_grants_repeat_without_owner_privilege(self):
  key={'accessKeyId':'GKoffline','name':garage.TAG,'expired':False,'permissions':{'createBucket':False},'buckets':[]}
  receipt={};buckets=[]
  plan=garage.bucket_plan(key,buckets,receipt,'GKoffline');self.assertEqual(len(plan['operations']),6)
  for i,alias in enumerate(garage.BUCKETS):
   bucket_id=hex(i+1)[2:].zfill(64);receipt[alias]=bucket_id
   buckets.append({'id':bucket_id,'globalAliases':[alias],'websiteAccess':False,'keys':[]})
  plan=garage.bucket_plan(key,buckets,receipt,'GKoffline');self.assertEqual({op['path'] for op in plan['operations']},{'/v2/AllowBucketKey'})
  for b in buckets:
   b['keys']=[{'accessKeyId':'GKoffline','name':garage.TAG,'bucketLocalAliases':[],'permissions':garage.PERMISSIONS.copy()}]
   key['buckets'].append({'id':b['id'],'globalAliases':b['globalAliases'],'localAliases':[],'permissions':garage.PERMISSIONS.copy()})
  self.assertTrue(garage.bucket_plan(key,buckets,receipt,'GKoffline')['ready'])
  buckets[0]['keys'][0]['permissions']['owner']=True
  with self.assertRaises(ValueError):garage.bucket_plan(key,buckets,receipt,'GKoffline')
 def test_foreign_bucket_or_create_capable_key_is_refused(self):
  key={'accessKeyId':'GKoffline','name':garage.TAG,'expired':False,'permissions':{},'buckets':[]}
  with self.assertRaises(ValueError):garage.bucket_plan(key,[{'id':'foreign'}],{},'GKoffline')
  key['permissions']['createBucket']=True
  with self.assertRaises(ValueError):garage.bucket_plan(key,[],{},'GKoffline')
