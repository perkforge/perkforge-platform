"""Pinned render checks; no live installation, enrollment or runner acceptance."""
from pathlib import Path
import os,tomllib,unittest,yaml
from fixtures.collaboration import package_render
from fixtures.render_helpers import build,ordered_values,helm,child_values
ROOT=Path(__file__).resolve().parents[2]
class CoordinatedGitLab(unittest.TestCase):
 def test_lab_preserves_resources_except_webservice_oom_limit(self):
  _,base=package_render(ROOT,'gitlab')['gitlab']
  _,lab=package_render(ROOT,'gitlab',extra_values=(ROOT/'configuration/packages/gitlab/lab-values.yaml',))['gitlab']
  from collections import Counter
  self.assertEqual(Counter(x['kind'] for x in base),Counter(x['kind'] for x in lab))
  a={x['metadata']['name']:x for x in base if x['kind'] in ('Deployment','StatefulSet','HorizontalPodAutoscaler')};b={x['metadata']['name']:x for x in lab if x['kind'] in ('Deployment','StatefulSet','HorizontalPodAutoscaler')}
  self.assertEqual(set(a),set(b))
  for name,x in b.items():
   if x['kind']=='HorizontalPodAutoscaler':self.assertEqual((x['spec']['minReplicas'],x['spec']['maxReplicas']),(1,1))
   if x['kind'] in ('Deployment','StatefulSet'):
    def sizes(o):return {c['name']:c.get('resources',{}) for c in o['spec']['template']['spec']['containers']}
    expected=sizes(a[name])
    if 'webservice' in expected:
     self.assertEqual(expected['webservice']['limits']['memory'],'3G')
     expected['webservice']['limits']['memory']='4G'
     env={e['name']:e.get('value') for c in x['spec']['template']['spec']['containers'] if c['name']=='webservice' for e in c.get('env',[])}
     self.assertEqual(env['WORKER_PROCESSES'],'2')
    self.assertEqual(sizes(x),expected)
 def test_app_memory_fix_changes_only_limit_and_values_hashed_job_names(self):
  import re
  src=Path(os.environ['PREFLIGHT_SOURCES_DIR']);root=build(ROOT/'clusters/local-gitlab-app');parent=next(x for x in root if x['kind']=='HelmRelease' and x['metadata']['name']=='bigbang')
  outer=helm(src/'bigbang/chart','bigbang','bigbang',ordered_values(root,parent));values=child_values(outer,'gitlab')
  new=helm(src/'gitlab/chart','gitlab','gitlab',values)
  old=helm(src/'gitlab/chart','gitlab','gitlab',values,('--set','upstream.gitlab.webservice.resources.limits.memory=3G'))
  def stable(objects):
   import copy
   objects=copy.deepcopy(objects)
   for o in objects:
    if o['kind']=='Deployment':
     for c in o['spec']['template']['spec']['containers']:
      if c['name']=='webservice':c['resources']['limits']['memory']='CAP'
   return re.sub(r'(gitlab-(?:shared-secrets|migrations))-[0-9a-f]{7}',r'\1-VALUESHASH',yaml.safe_dump(objects))
  self.assertEqual(stable(old),stable(new))
 def test_runner_render_and_protected_secret_references(self):
  src=Path(os.environ['PREFLIGHT_SOURCES_DIR']);root=build(ROOT/'clusters/local');parent=next(x for x in root if x['kind']=='HelmRelease')
  values=ordered_values(root,parent)+[(ROOT/'configuration/packages/gitlab-runner/candidate-values.yaml').read_text()]
  outer=helm(src/'bigbang/chart','bigbang','bigbang',values,('--set','addons.gitlabRunner.enabled=true'))
  hr=next(x for x in outer if x['kind']=='HelmRelease' and x['metadata']['name']=='gitlab-runner');self.assertTrue(hr['spec']['suspend'])
  rendered=helm(src/'gitlab-runner/chart','gitlab-runner','gitlab-runner',child_values(outer,'gitlab-runner'))
  self.assertEqual({x['kind'] for x in rendered},{'Deployment','ConfigMap'})
  deploy=next(x for x in rendered if x['kind']=='Deployment');self.assertEqual(deploy['spec']['template']['spec']['imagePullSecrets'],[{'name':'private-registry'}]);self.assertEqual(deploy['spec']['replicas'],1);self.assertEqual(deploy['spec']['strategy']['type'],'Recreate')
  text=yaml.safe_dump(rendered);self.assertIn('gitlab-runner-auth',text);self.assertIn('gitlab-runner-public-ca',text)
  cm=next(x for x in rendered if x['kind']=='ConfigMap');config=tomllib.loads(cm['data']['config.template.toml'])
  k=config['runners'][0]['kubernetes'];self.assertFalse(k['privileged']);self.assertFalse(k['automount_service_account_token']);self.assertFalse(k['bearer_token_overwrite_allowed'])
  for key in ('namespace_overwrite_allowed','service_account_overwrite_allowed','pod_annotations_overwrite_allowed','pod_labels_overwrite_allowed'):self.assertEqual(k[key],'')
  self.assertEqual(k['namespace'],'gitlab-ci-platform');self.assertEqual(k['service_account'],'gitlab-ci-job');self.assertNotIn('volumes',k)
  self.assertNotIn('http://gitlab-webservice',text)
 def test_job_boundary_does_not_grant_manager_namespace_or_cluster_access(self):
  objects=build(ROOT/'configuration/packages/gitlab-runner/prerequisites')
  self.assertFalse(any(x['kind'].startswith('Cluster') for x in objects))
  roles=[x for x in objects if x['kind']=='Role' and x['metadata']['name']=='gitlab-runner-jobs'];self.assertTrue(roles)
  for role in roles:
   self.assertEqual(role['metadata']['namespace'],'gitlab-ci-platform')
   for rule in role['rules']:
    self.assertFalse(set(rule['verbs']) & {'*','bind','escalate','impersonate'});self.assertNotIn('serviceaccounts/token',rule['resources'])
  binding=next(x for x in objects if x['kind']=='RoleBinding');self.assertEqual(binding['subjects'][0]['namespace'],'gitlab-runner')
  sa=next(x for x in objects if x['kind']=='ServiceAccount' and x['metadata']['name']=='gitlab-ci-job');self.assertFalse(sa['automountServiceAccountToken'])
  deny=next(x for x in objects if x['kind']=='NetworkPolicy' and x['metadata']['name']=='default-deny');self.assertEqual(set(deny['spec']['policyTypes']),{'Ingress','Egress'})
 def test_provider_plan_is_non_deployable_and_accounts_for_storage(self):
  d=yaml.safe_load((ROOT/'configuration/packages/gitlab/data-services-review.yaml').read_text())
  self.assertFalse(d['enabled']);self.assertTrue(d['review_only']);self.assertFalse(d['choice_approved']);self.assertFalse(d['live_apply_implemented'])
  p=d['recommended_lab'];self.assertEqual(p['postgres']['supported_major_versions'],[17,18]);self.assertFalse(p['postgres']['application_superuser']);self.assertEqual(p['valkey']['eviction_policy'],'noeviction');self.assertTrue(p['valkey']['persistence_required'])
  from fixtures.resource_inventory import quantity
  amounts=[p['postgres']['storage']['size'],p['valkey']['storage']['size'],p['object_store']['data_storage']['size'],p['object_store']['metadata_storage']['size']]
  data=sum(map(quantity,amounts));self.assertEqual(data,quantity(p['persistence']['data_claim_total']))
  total=data+quantity(p['persistence']['gitaly_claim_additional']);self.assertEqual(total,quantity(p['persistence']['logical_total_before_backup']));self.assertEqual(2*total,quantity(p['persistence']['scheduled_replica_total_before_backup']))
  self.assertFalse(p['backup']['same_cluster_object_store_is_independent']);self.assertFalse(p['backup']['deletion_on_sso_rollback']);self.assertEqual(p['backup']['independent_destination'],'owner-encrypted-external-drive');self.assertFalse(p['backup']['device_access_authorized']);self.assertFalse(p['backup']['usable_capacity_verified']);self.assertFalse(p['backup']['restore']['real_restore_passed'])
  self.assertTrue(p['transport']['tls_required']);self.assertFalse(p['transport']['skip_verification'])
 def test_exact_data_candidates_render_with_persistence_and_scoped_privileges(self):
  src=Path(os.environ['PREFLIGHT_SOURCES_DIR']);path=ROOT/'configuration/packages/gitlab/data-services'
  pg=yaml.safe_load((path/'runtime/postgres.yaml').read_text())['spec'];self.assertFalse(pg['enableSuperuserAccess']);self.assertIn('@sha256:',pg['imageName']);self.assertIn('hostnossl all all all reject',pg['postgresql']['pg_hba'])
  cnpg=helm(src/'cnpg','platform-cnpg','cnpg-system',[(ROOT/'configuration/packages/cloudnative-pg/values.yaml').read_text()],('--include-crds',))
  self.assertFalse(any(x['kind']=='CustomResourceDefinition' for x in cnpg))
  foundation_crds=helm(src/'cnpg','platform-cnpg','cnpg-system',[(ROOT/'configuration/packages/cloudnative-pg/values.yaml').read_text()],('--include-crds','--set','crds.create=true'))
  self.assertEqual(sum(x['kind']=='CustomResourceDefinition' for x in foundation_crds),11)
  for x in cnpg:
   self.assertFalse(any(k.startswith('rbac.authorization.k8s.io/aggregate-to-') and v=='true' for k,v in x.get('metadata',{}).get('labels',{}).items()))
  role=next(x for x in cnpg if x['kind']=='Role');self.assertEqual(role['metadata']['namespace'],'cnpg-system')
  for x in cnpg:
   if x['kind']=='Deployment':self.assertIn('@sha256:',x['spec']['template']['spec']['containers'][0]['image'])
  vk=helm(src/'valkey','gitlab-valkey','gitlab',[(path/'valkey-values.yaml').read_text()])
  self.assertFalse(any(x['kind'] in ('Secret','ClusterRole','ClusterRoleBinding') for x in vk))
  pvc=next(x for x in vk if x['kind']=='PersistentVolumeClaim');self.assertEqual(pvc['spec']['storageClassName'],'longhorn');self.assertEqual(pvc['spec']['resources']['requests']['storage'],'2Gi');self.assertEqual(pvc['metadata']['annotations']['helm.sh/resource-policy'],'keep')
  text=yaml.safe_dump(vk);self.assertIn('gitlab-valkey-acl',text);self.assertIn('gitlab-valkey-tls',text);self.assertIn('7.2.15@sha256:',text);self.assertIn('noeviction',text)
  garage=build(path/'garage');self.assertFalse(any(x['kind'].endswith('Role') or x['kind'].endswith('RoleBinding') for x in garage))
  pod=next(x for x in garage if x['kind']=='StatefulSet')['spec']['template']['spec'];self.assertFalse(pod['automountServiceAccountToken']);self.assertNotIn('hostPath',yaml.safe_dump(pod))
  config=next(x for x in garage if x['kind']=='ConfigMap')['data']['garage.toml'];toml=tomllib.loads(config);self.assertNotIn('kubernetes_discovery',toml);self.assertEqual(toml['replication_factor'],1);self.assertEqual(toml['admin']['api_bind_addr'],'127.0.0.1:3903');self.assertIn('rpc_secret_file',toml)

 def test_runner_installer_cannot_bind_roles_or_mutate_job_namespace(self):
  objects=build(ROOT/'configuration/packages/gitlab-runner/prerequisites')
  role=next(x for x in objects if x['kind']=='Role' and x['metadata']['name']=='gitlab-runner-installer')
  self.assertEqual(role['metadata']['namespace'],'gitlab-runner')
  for r in role['rules']:
   self.assertFalse(set(r['verbs']) & {'*','bind','escalate','impersonate'})
   self.assertFalse(set(r['resources']) & {'roles','rolebindings','serviceaccounts/token','pods/exec'})
  sa=next(x for x in objects if x['kind']=='ServiceAccount' and x['metadata']['name']=='gitlab-runner-installer');self.assertEqual(sa['metadata']['namespace'],'bigbang');self.assertFalse(sa['automountServiceAccountToken'])
 def test_supported_libpq_environment_does_not_render_ca_only_override(self):
  overlay=ROOT/'configuration/packages/gitlab/postgres-verify-full-values.yaml'
  hr,objects=package_render(ROOT,'gitlab',extra_values=(overlay,))['gitlab'];self.assertTrue(hr['spec']['suspend'])
  text=yaml.safe_dump(objects);self.assertNotIn('sslmode: verify-ca',text);self.assertNotIn('postgresql-ssl-secrets',text)
  found=set()
  for obj in objects:
   if obj['kind'] not in ('Deployment','Job'):continue
   name=obj['metadata']['name']
   if not any(part in name for part in ('webservice','sidekiq','migrations','toolbox')):continue
   pod=obj['spec']['template']['spec'];vol=next(x for x in pod['volumes'] if x['name']=='gitlab-postgres-public-ca');self.assertEqual(vol['configMap']['items'],[{'key':'ca.crt','path':'ca.crt'}])
   for c in pod['containers'] + pod.get('initContainers',[]):
    if not any(m['name']=='gitlab-postgres-public-ca' for m in c.get('volumeMounts',[])):continue
    env={e['name']:e.get('value') for e in c.get('env',[])}
    self.assertEqual(env.get('PGSSLMODE'),'verify-full',(name,c['name']));self.assertEqual(env.get('PGSSLROOTCERT'),'/etc/gitlab-postgres-ca/ca.crt')
    mount=next(x for x in c['volumeMounts'] if x['name']=='gitlab-postgres-public-ca');self.assertTrue(mount['readOnly'])
   found.update(part for part in ('webservice','sidekiq','migrations','toolbox') if part in name)
  self.assertEqual(found,{'webservice','sidekiq','migrations','toolbox'})
 def test_public_ca_mount_avoids_read_only_parent_for_all_app_and_init_consumers(self):
  import re
  from pathlib import PurePosixPath
  src=Path(os.environ['PREFLIGHT_SOURCES_DIR']);root=build(ROOT/'clusters/local-gitlab-app');parent=next(x for x in root if x['kind']=='HelmRelease' and x['metadata']['name']=='bigbang')
  outer=helm(src/'bigbang/chart','bigbang','bigbang',ordered_values(root,parent));values=child_values(outer,'gitlab')
  new=helm(src/'gitlab/chart','gitlab','gitlab',values)
  old=helm(src/'gitlab/chart','gitlab','gitlab',[v.replace('/etc/gitlab-postgres-ca','/etc/gitlab/database-ca') for v in values])
  def consumers(objects):
   return [(o,c,m) for o in objects if o['kind'] in ('Deployment','Job') for c in o['spec']['template']['spec']['containers']+o['spec']['template']['spec'].get('initContainers',[]) for m in c.get('volumeMounts',[]) if m['name']=='gitlab-postgres-public-ca']
  def collisions(objects):
   return [(o['metadata']['name'],c['name']) for o,c,ca in consumers(objects) if any(m['name']!=ca['name'] and m.get('readOnly') and PurePosixPath(ca['mountPath']).is_relative_to(PurePosixPath(m['mountPath'])) for m in c['volumeMounts'])]
  self.assertEqual(len(consumers(new)),11)  # five app containers, four configure, two dependency init containers
  self.assertEqual(len(collisions(old)),7)  # actual old read-only parent collisions, including dependency init
  self.assertEqual(collisions(new),[])
  for o,c,m in consumers(new):
   self.assertEqual(m['mountPath'],'/etc/gitlab-postgres-ca');self.assertIs(m['readOnly'],True)
   env={e['name']:e.get('value') for e in c.get('env',[])}
   if c['name']!='configure':
    self.assertEqual(env['PGSSLMODE'],'verify-full');self.assertEqual(env['PGSSLROOTCERT'],m['mountPath']+'/ca.crt')
  def stable(value):
   if isinstance(value,str):return re.sub(r'(gitlab-(?:shared-secrets|migrations))-[0-9a-f]{7}',r'\1-VALUESHASH',value.replace('/etc/gitlab/database-ca','/etc/gitlab-postgres-ca'))
   if isinstance(value,list):return [stable(x) for x in value]
   if isinstance(value,dict):return {k:stable(v) for k,v in value.items()}
   return value
  self.assertEqual(stable(old),stable(new))  # no unrelated exact-render changes
 def test_acceptance_job_matches_protected_project_runner_contract(self):
  p=ROOT/'configuration/packages/gitlab-runner'
  d=yaml.safe_load((p/'registration-review.yaml').read_text());self.assertFalse(d['enabled']);self.assertTrue(d['review_only']);b=d['body'];self.assertEqual(b['runner_type'],'project_type');self.assertTrue(b['locked']);self.assertFalse(b['run_untagged']);self.assertEqual(b['access_level'],'ref_protected');self.assertFalse(d['credential_output']['print_token'])
  ci=yaml.safe_load((p/'acceptance/gitlab-ci.example.yaml').read_text());job=ci['runner-baseline'];self.assertEqual(job['tags'],b['tag_list']);self.assertIn('CI_COMMIT_REF_PROTECTED',ci['workflow']['rules'][0]['if']);self.assertEqual(ci['workflow']['rules'][-1],{'when':'never'})
  candidate=yaml.safe_load((p/'candidate-values.yaml').read_text())['addons']['gitlabRunner']['values']['upstream'];config=tomllib.loads(candidate['runners']['config']);self.assertIn(job['image'],config['runners'][0]['kubernetes']['allowed_images']);self.assertEqual(candidate['concurrent'],1)
  self.assertIn('test ! -e /var/run/secrets/kubernetes.io/serviceaccount/token',job['script']);self.assertEqual(job['artifacts']['paths'],['acceptance/result.txt'])
 def test_combined_lab_connections_keep_tls_and_separate_backup_gate(self):
  p=ROOT/'configuration/packages/gitlab';extras=tuple(p/n for n in ('lab-values.yaml','sso-values.yaml','postgres-verify-full-values.yaml','data-connections-values.yaml'))
  hr,objects=package_render(ROOT,'gitlab',extra_values=extras)['gitlab'];self.assertTrue(hr['spec']['suspend']);text=yaml.safe_dump(objects)
  for value in ('rediss://','gitlab-valkey-public-ca','gitlab-postgres-public-ca','gitlab-platform-public-ca','gitlab-object-store','gitlab-backup-staging','verify-full'):self.assertIn(value,text)
  self.assertNotIn('sslmode: verify-ca',text);self.assertFalse(any(x['kind']=='CronJob' for x in objects))
  configs='\n'.join(v for o in objects if o['kind']=='ConfigMap' for v in o.get('data',{}).values() if isinstance(v,str))
  self.assertIn('gitlab-artifacts',configs);self.assertIn('gitlab-lfs',configs);self.assertIn('gitlab-uploads',configs);self.assertIn('gitlab-packages',configs)

 def test_webservice_render_matches_isolated_runtime_evidence_digest(self):
  import json
  evidence=json.loads((ROOT/'tests/fixtures/gitlab-cng-runtime-evidence.json').read_text());self.assertTrue(all(evidence['results'].values()));self.assertFalse(evidence['isolation']['credentials_mounted'])
  _,objects=package_render(ROOT,'gitlab')['gitlab'];pod=next(x for x in objects if x['kind']=='Deployment' and 'webservice' in x['metadata']['name'])['spec']['template']['spec'];image=next(c['image'] for c in pod['containers'] if c['name']=='webservice');self.assertEqual(image.split('@')[1],evidence['image'].split('@')[1])

 def test_routes_match_actual_services_without_exposing_admin_or_plaintext(self):
  path=ROOT/'configuration/packages/gitlab'
  routes=build(path/'routing')
  _,rendered=package_render(ROOT,'gitlab')['gitlab']
  garage=build(path/'data-services/garage')
  services={x['metadata']['name']:x for x in [*rendered,*garage] if x['kind']=='Service'}
  ingresses=[x for x in routes if x['kind']=='Ingress']
  self.assertEqual(len(ingresses),2)
  for ingress in ingresses:
   self.assertEqual(ingress['metadata']['namespace'],'gitlab')
   annotations=ingress['metadata']['annotations']
   self.assertEqual(annotations['traefik.ingress.kubernetes.io/router.entrypoints'],'websecure')
   self.assertEqual(annotations['traefik.ingress.kubernetes.io/router.tls'],'true')
   spec=ingress['spec'];self.assertEqual(spec['tls'][0]['hosts'],[spec['rules'][0]['host']])
   backend=spec['rules'][0]['http']['paths'][0]['backend']['service']
   ports=services[backend['name']]['spec']['ports']
   self.assertIn(backend['port']['name'],{p['name'] for p in ports})
  policy=next(x for x in routes if x['kind']=='NetworkPolicy')['spec']
  self.assertEqual(policy['podSelector'],{'matchLabels':{'app':'gitlab-garage'}})
  self.assertEqual(policy['policyTypes'],['Ingress'])
  rule=policy['ingress'][0];self.assertEqual(rule['ports'],[{'protocol':'TCP','port':3900}])
  peer=rule['from'][0]
  self.assertEqual(peer['namespaceSelector']['matchLabels']['kubernetes.io/metadata.name'],'kube-system')
  self.assertEqual(peer['podSelector']['matchLabels']['app.kubernetes.io/name'],'rke2-traefik')
  # Both selectors must be in the SAME peer; separate peers would OR them.
  self.assertEqual(len(rule['from']),1)
  default=build(ROOT/'clusters/local')
  self.assertFalse(any(x['kind']=='Ingress' and x['metadata']['name'].startswith('gitlab') for x in default))

 def test_review_profile_preserves_existing_objects_and_keeps_new_releases_off(self):
  base=build(ROOT/'clusters/local-headlamp-sso');review=build(ROOT/'clusters/local-gitlab-review')
  def key(x):return (x['apiVersion'],x['kind'],x['metadata'].get('namespace'),x['metadata']['name'])
  original={key(x):x for x in base};actual={key(x):x for x in review}
  parent=next(x for x in review if x['kind']=='HelmRelease' and x['metadata']['name']=='bigbang')
  old=original[key(parent)]
  for k,x in original.items():
   if k!=key(parent):self.assertEqual(x,actual[k])
  refs=parent['spec']['valuesFrom'];self.assertEqual(refs[:len(old['spec']['valuesFrom'])],old['spec']['valuesFrom'])
  self.assertEqual([v['name'] for v in refs[len(old['spec']['valuesFrom']):]],['values-gitlab','values-gitlab-lab','values-gitlab-sso','values-gitlab-postgres-tls','values-gitlab-data','values-gitlab-runner'])
  import copy
  restored=copy.deepcopy(parent);restored['spec']['valuesFrom']=old['spec']['valuesFrom'];self.assertEqual(restored,old)
  self.assertEqual({x['kind'] for k,x in actual.items() if k not in original},{'ConfigMap'})
  values=ordered_values(review,parent)
  outer=helm(Path(os.environ['PREFLIGHT_SOURCES_DIR'])/'bigbang/chart','bigbang','bigbang',values)
  self.assertFalse(any(x['kind']=='HelmRelease' and x['metadata']['name'] in ('gitlab','gitlab-runner') for x in outer))

 def test_provider_sources_are_pinned_suspended_and_separate_from_app_installer(self):
  objects=build(ROOT/'configuration/packages/gitlab/data-services')
  releases=[x for x in objects if x['kind']=='HelmRelease']
  self.assertEqual(len(releases),2)
  expected={'platform-cnpg':('cloudnative-pg','0.29.1','platform-cnpg-installer'),'gitlab-valkey':('valkey','0.12.1','gitlab-data-installer')}
  cms={x['metadata']['name']:x for x in objects if x['kind']=='ConfigMap'}
  repos={x['metadata']['name']:x for x in objects if x['kind']=='HelmRepository'}
  for obj in releases:
   name=obj['metadata']['name'];chart,version,identity=expected[name];spec=obj['spec']
   self.assertEqual(obj['metadata']['namespace'],'bigbang');self.assertTrue(spec['suspend'])
   self.assertEqual(spec['targetNamespace'],'cnpg-system' if name=='platform-cnpg' else 'gitlab');self.assertEqual(spec['serviceAccountName'],identity)
   self.assertEqual(spec['chart']['spec']['chart'],chart);self.assertEqual(spec['chart']['spec']['version'],version)
   self.assertEqual(spec['install']['remediation']['retries'],0);self.assertFalse(spec['install']['createNamespace'])
   self.assertEqual(spec['upgrade']['crds'],'Skip')
   self.assertTrue(repos[name]['spec']['url'].startswith('https://'))
   values=yaml.safe_load(cms[spec['valuesFrom'][0]['name']]['data']['values.yaml'])
   source='cnpg' if name=='platform-cnpg' else 'valkey'
   rendered=helm(Path(os.environ['PREFLIGHT_SOURCES_DIR'])/source,name,spec['targetNamespace'],[yaml.safe_dump(values)],('--include-crds',))
   self.assertTrue(rendered)
  self.assertFalse(any(x['kind'].endswith('RoleBinding') for x in objects))

 def test_operator_authority_review_matches_pinned_cluster_objects_and_rules(self):
  path=ROOT/'configuration/packages/gitlab/data-services'
  review=yaml.safe_load((ROOT/'configuration/packages/cloudnative-pg/authority-review.yaml').read_text())
  rendered=helm(Path(os.environ['PREFLIGHT_SOURCES_DIR'])/'cnpg','platform-cnpg','cnpg-system',[(ROOT/'configuration/packages/cloudnative-pg/values.yaml').read_text()],('--include-crds','--set','crds.create=true'))
  kinds=('CustomResourceDefinition','ClusterRole','ClusterRoleBinding','MutatingWebhookConfiguration','ValidatingWebhookConfiguration')
  self.assertEqual(review['global_objects'],[{'kind':x['kind'],'name':x['metadata']['name']} for x in rendered if x['kind'] in kinds])
  self.assertEqual(review['runtime_cluster_rules'],[{'role':x['metadata']['name'],'rules':x['rules']} for x in rendered if x['kind']=='ClusterRole' and not x['metadata']['name'].endswith(('-view','-edit'))])
  self.assertFalse(review['installation_approved']);self.assertTrue(review['review_only']);self.assertEqual(review['watch_namespace'],'gitlab')
  self.assertFalse(review['aggregate_builtin_roles'])

 def test_shared_operator_watch_delegation_and_installer_boundaries(self):
  import tempfile
  path=ROOT/'configuration/packages/cloudnative-pg';objects=build(path)
  hr=next(x for x in objects if x['kind']=='HelmRelease');self.assertTrue(hr['spec']['suspend']);self.assertEqual(hr['spec']['targetNamespace'],'cnpg-system')
  values=yaml.safe_load(next(x for x in objects if x['kind']=='ConfigMap')['data']['values.yaml'])
  rendered=helm(Path(os.environ['PREFLIGHT_SOURCES_DIR'])/'cnpg','platform-cnpg','cnpg-system',[yaml.safe_dump(values)],('--include-crds',))
  with tempfile.TemporaryDirectory(prefix='cnpg-watch-fixture-') as directory:
   p=Path(directory);(p/'rendered.yaml').write_text(yaml.safe_dump_all(rendered));(p/'kustomization.yaml').write_text(yaml.safe_dump({'resources':['rendered.yaml'],'patches':hr['spec']['postRenderers'][0]['kustomize']['patches']}));patched=build(p)
  deployment=next(x for x in patched if x['kind']=='Deployment')
  env=deployment['spec']['template']['spec']['containers'][0]['env'];self.assertEqual([x for x in env if x['name']=='WATCH_NAMESPACE'],[{'name':'WATCH_NAMESPACE','value':'gitlab'}])
  foundation=list(yaml.safe_load_all((path/'prerequisites.yaml').read_text()))
  database_role=next(x for x in foundation if x['kind']=='Role' and x['metadata']['name']=='platform-cnpg-databases')
  runtime_role=next(x for x in rendered if x['kind']=='Role');self.assertEqual(database_role['rules'],runtime_role['rules']);self.assertEqual(database_role['metadata']['namespace'],'gitlab')
  binding=next(x for x in foundation if x['kind']=='RoleBinding' and x['metadata']['name']=='platform-cnpg-databases');self.assertEqual(binding['subjects'],[{'kind':'ServiceAccount','name':'platform-cnpg','namespace':'cnpg-system'}])
  installer=next(x for x in foundation if x['kind']=='ClusterRole')
  for rule in installer['rules']:
   self.assertNotIn('*',rule['verbs']);self.assertNotIn('*',rule['resources']);self.assertNotIn('cluster-admin',rule.get('resourceNames',[]))
   if set(rule['verbs']) & {'bind','escalate'}:self.assertEqual(set(rule['resourceNames']),{'platform-cnpg','platform-cnpg-view','platform-cnpg-edit'})
  self.assertFalse(any(x['kind'].endswith('RoleBinding') for x in objects))

 def test_dormant_activation_stages_preserve_review_off_and_order_crd_readiness(self):
  src=Path(os.environ['PREFLIGHT_SOURCES_DIR']);names={}
  for stage in ('review','providers','data','app','runner'):
   objects=build(ROOT/('clusters/local-gitlab-'+stage));parent=next(x for x in objects if x['kind']=='HelmRelease' and x['metadata']['name']=='bigbang');outer=helm(src/'bigbang/chart','bigbang','bigbang',ordered_values(objects,parent));names[stage]={x['metadata']['name'] for x in outer if x['kind']=='HelmRelease'}
   self.assertEqual('gitlab' in names[stage],stage in ('app','runner'));self.assertEqual('gitlab-runner' in names[stage],stage=='runner')
   if stage=='providers':
    self.assertFalse(any(x['apiVersion'].startswith('postgresql.cnpg.io/') for x in objects))
    for n in ('platform-cnpg','gitlab-valkey'):self.assertFalse(next(x for x in objects if x['kind']=='HelmRelease' and x['metadata']['name']==n)['spec']['suspend'])
   if stage=='data':
    self.assertTrue(any(x['kind']=='Cluster' and x['metadata']['name']=='gitlab-postgres' for x in objects))
    ingresses=[x for x in objects if x['kind']=='Ingress' and x['metadata']['namespace']=='gitlab'];self.assertEqual({x['spec']['rules'][0]['host'] for x in ingresses},{'gitlab.perkforge.home.arpa','gitlab-objects.perkforge.home.arpa'})
   if stage in ('app','runner'):
    release=next(x for x in outer if x['kind']=='HelmRelease' and x['metadata']['name']=='gitlab');self.assertFalse(release['spec']['suspend'])
    rendered=helm(src/'gitlab/chart','gitlab','gitlab',child_values(outer,'gitlab'));text=yaml.safe_dump(rendered);self.assertIn('gitlab.perkforge.home.arpa',text);self.assertIn('gitlab-postgres-rw.gitlab.svc.cluster.local',text);self.assertIn('PGSSLMODE',text)
  self.assertEqual(names['review'],names['providers']);self.assertEqual(names['providers'],names['data'])

 def test_operator_cannot_mutate_template_crds_and_foundation_pin_matches_fixture(self):
  path=ROOT/'configuration/packages/cloudnative-pg';values=yaml.safe_load((path/'values.yaml').read_text());self.assertFalse(values['crds']['create'])
  hr=next(x for x in build(path) if x['kind']=='HelmRelease');self.assertEqual(hr['spec']['install']['crds'],'Skip');self.assertEqual(hr['spec']['upgrade']['crds'],'Skip')
  source=yaml.safe_load((path/'source-pin.yaml').read_text());pins=yaml.safe_load((ROOT/'tests/fixtures/source-pins.yaml').read_text())['cnpg'];self.assertEqual((source['url'],source['sha256']),(pins['url'],pins['sha256']))
  installer=next(x for x in yaml.safe_load_all((path/'prerequisites.yaml').read_text()) if x['kind']=='ClusterRole')
  self.assertFalse(any('customresourcedefinitions' in rule['resources'] for rule in installer['rules']))

 def test_gitlab_source_delegation_does_not_depend_on_rancher_or_allow_data_pruning(self):
  objects=list(yaml.safe_load_all((ROOT/'configuration/packages/gitlab/data-services/providers/prerequisites.yaml').read_text()))
  writer=next(x for x in objects if x['kind']=='Role' and x['metadata']['name']=='gitlab-provider-source-writer')
  self.assertTrue(any('helmrepositories' in r['resources'] and 'create' in r['verbs'] for r in writer['rules']))
  cleanup=next(r for r in writer['rules'] if 'delete' in r['verbs']);self.assertEqual(cleanup['resources'],['configmaps']);self.assertEqual(set(cleanup['resourceNames']),{'values-gitlab-activation','values-gitlab-runner-activation'})
  data=next(x for x in objects if x['kind']=='Role' and x['metadata']['name']=='gitlab-data-gitops')
  self.assertFalse(any('delete' in r['verbs'] or 'secrets' in r['resources'] for r in data['rules']))

 def test_data_and_app_namespace_blocks_tenant_ingress_but_allows_real_operator(self):
  policies={x['metadata']['name']:x['spec'] for x in build(ROOT/'configuration/packages/gitlab/data-services/runtime') if x['kind']=='NetworkPolicy'}
  self.assertEqual(policies['gitlab-default-deny-ingress'],{'podSelector':{},'policyTypes':['Ingress']})
  internal=policies['gitlab-internal-ingress'];self.assertEqual(internal['ingress'],[{'from':[{'podSelector':{}}]}]);self.assertEqual(internal['podSelector']['matchExpressions'],[{'key':'app','operator':'NotIn','values':['gitlab-garage']}])
  operator=policies['gitlab-postgres-from-operator'];self.assertEqual(operator['podSelector']['matchLabels'],{'cnpg.io/cluster':'gitlab-postgres'});self.assertEqual({p['port'] for p in operator['ingress'][0]['ports']},{5432,8000})
  peer=operator['ingress'][0]['from'];self.assertEqual(len(peer),1);self.assertEqual(peer[0]['namespaceSelector']['matchLabels'],{'kubernetes.io/metadata.name':'cnpg-system'})
  values=(ROOT/'configuration/packages/cloudnative-pg/values.yaml').read_text();rendered=helm(Path(os.environ['PREFLIGHT_SOURCES_DIR'])/'cnpg','platform-cnpg','cnpg-system',[values]);labels=next(x for x in rendered if x['kind']=='Deployment')['spec']['template']['metadata']['labels'];self.assertTrue(peer[0]['podSelector']['matchLabels'].items()<=labels.items())
  _,app=package_render(ROOT,'gitlab')['gitlab'];web=policies['gitlab-web-from-traefik'];self.assertTrue(any(web['podSelector']['matchLabels'].items()<=x['spec']['template']['metadata']['labels'].items() for x in app if x['kind']=='Deployment'));self.assertEqual(web['ingress'][0]['ports'],[{'protocol':'TCP','port':8181}])
