"""Offline contracts for the opt-in local rollout. No live or native S3 acceptance claim."""
from copy import deepcopy
import importlib.util
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'configuration/packages/velero'
spec = importlib.util.spec_from_file_location('velero_guard', PACKAGE / 'filter_plugins/velero_guard.py')
guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
Gi = 1024 ** 3


def storage_fixture():
    fs = {'filesystems': [{'fstype':'xfs','options':'rw,prjquota','target':'/disk','uuid':'fixture-uuid',
                          'source':'/dev/fixture','size':1000*Gi,'avail':990*Gi}]}
    project = 'fsxattr.xflags = 0x200\nfsxattr.projid = 42\n'
    enforcement = 'Project quota state\nAccounting: ON\nEnforcement: ON\n'
    quota = f'#42 0 0 {100*Gi//1024} 0 0\n'
    node = {'spec': {'disks': {'one': {'path':'/disk','allowScheduling':True,'storageReserved':400*Gi}}},
            'status':{'diskStatus':{'one':{'storageMaximum':1000*Gi,'storageScheduled':100*Gi,'diskUUID':'disk-id'}}}}
    settings = {'items': [{'metadata':{'name':'storage-over-provisioning-percentage'},'value':'100'},
                          {'metadata':{'name':'storage-minimal-available-percentage'},'value':'25'}]}
    inputs = {'velero_storage_mount':'/disk','velero_storage_uuid':'fixture-uuid','velero_storage_path':'/disk/velero-backups',
              'velero_project_id':42,'velero_quota_bytes':100*Gi,'velero_restore_headroom_bytes':20*Gi,
              'velero_store_capacity_bytes':80*Gi,'velero_metadata_budget_bytes':20*Gi,
              'velero_longhorn_disk_name':'one','velero_longhorn_disk_path':'/disk'}
    return [fs, project, enforcement, quota, node, settings, deepcopy(fs), {'diskUUID':'disk-id'}, inputs]


def transfer_fixture():
    source = {'metadata':{'namespace':'source','name':'payload','uid':'source-pvc-uid'},'spec':{'volumeName':'old-pv'}}
    target = {'metadata':{'namespace':'target','name':'payload','uid':'new-pvc-uid'},'spec':{'volumeName':'new-pv'},'status':{'phase':'Bound'}}
    backup = {'kind':'Backup','metadata':{'uid':'backup-uid','name':'backup'},'status':{'phase':'Completed'}}
    restore = {'kind':'Restore','metadata':{'uid':'restore-uid','name':'restore'},'spec':{'namespaceMapping':{'source':'target'}},'status':{'phase':'Completed'}}
    upload = {'metadata':{'namespace':'velero','labels':{'velero.io/backup-uid':'backup-uid','velero.io/pvc-uid':'source-pvc-uid'},
                           'ownerReferences':[{'uid':'backup-uid','name':'backup','kind':'Backup','apiVersion':'velero.io/v1'}]},
              'spec':{'sourceNamespace':'source','sourcePVC':'payload','snapshotType':'CSI','csiSnapshot':{'driver':'driver.longhorn.io'},'backupStorageLocation':'local'},
              'status':{'phase':'Completed','snapshotID':'copied-snapshot','progress':{'bytesDone':8388608,'totalBytes':8388608}}}
    download = {'metadata':{'namespace':'velero','labels':{'velero.io/restore-uid':'restore-uid'},
                             'ownerReferences':[{'uid':'restore-uid','name':'restore','kind':'Restore','apiVersion':'velero.io/v1'}]},
                'spec':{'targetVolume':{'namespace':'target','pvc':'payload','pv':''},'sourceNamespace':'source','snapshotID':'copied-snapshot','backupStorageLocation':'local'},
                'status':{'phase':'Completed','progress':{'bytesDone':8388608,'totalBytes':8388608}}}
    return backup, restore, source, target, upload, download


class VeleroDeployment(unittest.TestCase):
    def test_default_and_check_modes_contact_no_api(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory); binary = path/'bin'; binary.mkdir()
            marker = path/'unexpected'
            for name in ('kubectl','curl','ssh','git','openssl'):
                f=binary/name; f.write_text('#!/bin/sh\necho called > "$API_MARKER"\nexit 99\n'); f.chmod(0o700)
            env = {**os.environ,'PATH':str(binary)+os.pathsep+os.environ['PATH'],'API_MARKER':str(marker),
                   'ANSIBLE_LOCAL_TEMP':str(path/'ansible'),'KUBECONFIG':'/dev/null'}
            for play,flag in (('install.yaml','velero_install_apply'),('bootstrap-store.yaml','velero_garage_run'),('exercise.yaml','velero_exercise_run'),('recovery.yaml','velero_recovery_run')):
                for extra in ([],['--check','-e',json.dumps({flag:True})]):
                    with self.subTest(play=play,extra=extra):
                        result=subprocess.run(['ansible-playbook','-i','localhost,',str(PACKAGE/play),*extra],env=env,text=True,capture_output=True,timeout=30)
                        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                        self.assertIn('changed=0',result.stdout)
                        self.assertFalse(marker.exists())

    def test_native_exercise_success_and_wrong_uid_failure(self):
        for bad_uid in (False, True):
            with self.subTest(bad_uid=bad_uid), tempfile.TemporaryDirectory() as directory:
                path=Path(directory);path.chmod(0o700)
                config=path/'kubeconfig';config.write_text('synthetic fixture, never a credential');config.chmod(0o600)
                binary=path/'kubectl';binary.write_text((ROOT/'tests/fixtures/velero_kubectl.py').read_text());binary.chmod(0o700)
                state=path/'state.json';state.write_text(json.dumps({'inject_wrong_uid':bad_uid,'Pod|velero-store|velero-store-0':{'kind':'Pod','metadata':{'name':'velero-store-0','namespace':'velero-store','uid':'store-before','labels':{'app':'velero-store'},'ownerReferences':[{'kind':'StatefulSet','name':'velero-store'}]}}}))
                values={'velero_exercise_run':True,'velero_exercise_scope':'velero-disposable-copy-v1','velero_exercise_id':'abc123',
                        'velero_exercise_storage_class':'longhorn','velero_exercise_node':'worker-fixture','velero_kubectl':str(binary),
                        'velero_kubeconfig':str(config),'velero_context':'fixture','velero_api':'https://fixture.internal:6443',
                        'velero_cluster_uid':'cluster-fixture-uid','velero_state_dir':str(path)}
                inputs=path/'inputs.json';inputs.write_text(json.dumps(values))
                env={**os.environ,'VELERO_FAKE_STATE':str(state),'ANSIBLE_LOCAL_TEMP':str(path/'ansible')}
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(PACKAGE/'exercise.yaml'),'-e','@'+str(inputs)],env=env,text=True,capture_output=True,timeout=70)
                if bad_uid:
                    self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertIn('velero_copied_transfers',result.stdout)
                    self.assertNotIn('"delete"',Path(str(state)+'.calls').read_text())
                    self.assertFalse((path/'exercise-abc123-result.json').exists())
                else:
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    receipt=json.loads((path/'exercise-abc123-result.json').read_text())
                    self.assertTrue(receipt['copied_byte_roundtrip'])
                    self.assertFalse(receipt['application_recovery_verified'])
                    self.assertEqual(json.loads(state.read_text())['Pod|velero-store|velero-store-0']['metadata']['uid'],'store-reopened')

    def test_owned_match_normalizes_storage_and_rejects_authority_drift(self):
        desired={'kind':'PersistentVolume','metadata':{'name':'store','labels':{'perkforge.io/owner':'velero-platform-v1'}},'spec':{'capacity':{'storage':str(2*Gi)}}}
        actual=deepcopy(desired);actual['spec']['capacity']['storage']='2Gi'
        self.assertTrue(guard.owned_matches(actual,desired))
        actual['spec']['capacity']['storage']='3Gi'
        self.assertFalse(guard.owned_matches(actual,desired))
        actual=deepcopy(desired);actual['metadata']['labels']={}
        self.assertFalse(guard.owned_matches(actual,desired))

    def test_native_tenant_backup_paused_schedule_and_isolated_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);path.chmod(0o700)
            config=path/'kubeconfig';config.write_text('synthetic only');config.chmod(0o600)
            binary=path/'kubectl';binary.write_text((ROOT/'tests/fixtures/velero_kubectl.py').read_text());binary.chmod(0o700)
            state=path/'state.json';state.write_text(json.dumps({
                'Namespace||tenant-source':{'apiVersion':'v1','kind':'Namespace','metadata':{'name':'tenant-source','uid':'source-namespace'}},
                'Namespace||tenant-target':{'apiVersion':'v1','kind':'Namespace','metadata':{'name':'tenant-target','uid':'target-namespace'}},
                'PersistentVolumeClaim|tenant-source|payload':{'apiVersion':'v1','kind':'PersistentVolumeClaim','metadata':{'name':'payload','namespace':'tenant-source','uid':'old-pvc'},'spec':{'volumeName':'old-pv'},'status':{'phase':'Bound'}},
                'Kustomization|flux-system|fixture-owner':{'kind':'Kustomization','metadata':{'name':'fixture-owner','namespace':'flux-system'},'spec':{'suspend':True}}}))
            command={'container':'app','command':['/bin/true'],'onError':'Fail','timeout':'30s'}
            hook={'name':'quiesce','includedNamespaces':['tenant-source'],'labelSelector':{'matchLabels':{'app':'fixture'}},'pre':[{'exec':command}],'post':[{'exec':command}]}
            post={'name':'validate','includedNamespaces':['tenant-target'],'labelSelector':{'matchLabels':{'app':'fixture'}},'postHooks':[{'exec':{'container':'app','command':['/bin/true'],'onError':'Fail','execTimeout':'30s','waitTimeout':'2m'}}]}
            values={'velero_recovery_run':True,'velero_recovery_scope':'velero-backup-v1','velero_recovery_action':'backup',
                    'velero_recovery_name':'tenant-backup','velero_source_namespace':'tenant-source','velero_target_namespace':'tenant-target',
                    'velero_backup_name':'tenant-backup','velero_backup_hooks':[hook],'velero_restore_hooks':[post],'velero_rollback_window_hours':24,
                    'velero_recovery_versions':{'app_image_digest':'sha256:'+'a'*64,'chart_artifact_digest':'sha256:'+'b'*64,'app_git_commit':'c'*40,'platform_git_commit':'d'*40,'enrollment_git_commit':'e'*40,'database_version':'17.6','schema_version':'20261107'},
                    'velero_restore_owners':[{'kind':'kustomizations.kustomize.toolkit.fluxcd.io','name':'fixture-owner','namespace':'flux-system'}],
                    'velero_kubectl':str(binary),'velero_kubeconfig':str(config),'velero_context':'fixture','velero_api':'https://fixture.internal:6443',
                    'velero_cluster_uid':'cluster-fixture-uid','velero_state_dir':str(path)}
            inputs=path/'inputs.json';env={**os.environ,'VELERO_FAKE_STATE':str(state),'ANSIBLE_LOCAL_TEMP':str(path/'ansible')}
            command=['ansible-playbook','-i','localhost,',str(PACKAGE/'recovery.yaml'),'-e','@'+str(inputs)]
            for action,name in [('backup','tenant-backup'),('paused-schedule','tenant-schedule'),('restore','tenant-restore')]:
                values.update(velero_recovery_action=action,velero_recovery_name=name,velero_recovery_scope='velero-'+action+'-v1',velero_schedule_cron='0 */6 * * *')
                if action=='restore':
                    # A native scheduled point inherits its PVC/version annotations. It has no local receipt.
                    current=json.loads(state.read_text());schedule=current['Schedule|velero|tenant-schedule']
                    point={'apiVersion':'velero.io/v1','kind':'Backup','metadata':{'name':'scheduled-point','namespace':'velero','uid':'scheduled-backup-uid','annotations':schedule['metadata']['annotations']},'spec':schedule['spec']['template'],'status':{'phase':'Completed','errors':0}}
                    current['Backup|velero|scheduled-point']=point;state.write_text(json.dumps(current));values['velero_backup_name']='scheduled-point'
                inputs.write_text(json.dumps(values));result=subprocess.run(command,env=env,text=True,capture_output=True,timeout=75)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            recorded=json.loads(state.read_text())
            self.assertTrue(recorded['Schedule|velero|tenant-schedule']['spec']['paused'])
            self.assertTrue(recorded['Kustomization|flux-system|fixture-owner']['spec']['suspend'])
            restored=recorded['Restore|velero|tenant-restore']['spec']
            for resource in ('ingresses.networking.k8s.io','networkpolicies.networking.k8s.io','services','cronjobs.batch'):
                self.assertNotIn(resource,restored['includedResources'])
            self.assertEqual(recorded['NetworkPolicy|tenant-target|velero-restore-isolation']['spec']['ingress'],[])
            self.assertFalse(json.loads((path/'restore-tenant-restore.json').read_text())['functional_service'])

    def test_native_selector_promotion_repeat_and_intervening_app_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);path.chmod(0o700);package=path/'velero';shutil.copytree(PACKAGE,package,ignore=shutil.ignore_patterns('__pycache__'))
            binary=path/'kubectl';binary.write_text((ROOT/'tests/fixtures/velero_kubectl.py').read_text());binary.chmod(0o700)
            state=path/'state.json';state.write_text(json.dumps({'target_commit':'a'*40,
                'HelmRelease|bigbang|harbor':{'kind':'HelmRelease','metadata':{'name':'harbor','namespace':'bigbang','generation':2},'spec':{},'status':{'observedGeneration':2,'conditions':[{'type':'Ready','status':'True'}]}},
                'GitRepository|flux-system|cluster-config':{'kind':'GitRepository','metadata':{'uid':'source-uid','name':'cluster-config','namespace':'flux-system','resourceVersion':'1'},'spec':{'url':'https://github.com/perkforge/perkforge-platform.git','ref':{'tag':'v1.0.0'},'interval':'1m'}},
                'Kustomization|flux-system|cluster-root':{'kind':'Kustomization','metadata':{'uid':'root-uid','name':'cluster-root','namespace':'flux-system','resourceVersion':'1'},'spec':{'sourceRef':{'kind':'GitRepository','name':'cluster-config'},'path':'./big-bang-bootstrap/clusters/local-harbor-app','serviceAccountName':'platform-reconciler','prune':False,'interval':'1m'}}}))
            values={'vk':[str(binary)],'velero_state_dir':str(path),'velero_root_name':'cluster-root','velero_previous_tag':'v1.0.0','velero_release_tag':'v1.0.1','velero_release_commit':'a'*40,'velero_previous_path':'./big-bang-bootstrap/clusters/local-harbor-app'}
            harness=package/'fixture.yaml';harness.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'vars':values,'tasks':[{'ansible.builtin.include_tasks':'deployment/read-selectors.yaml'},{'ansible.builtin.include_tasks':'deployment/promote.yaml'}]}]))
            env={**os.environ,'VELERO_FAKE_STATE':str(state),'ANSIBLE_LOCAL_TEMP':str(path/'ansible')};command=['ansible-playbook','-i','localhost,',str(harness)]
            original=json.loads(state.read_text())
            for failure in ('unready','stale'):
                failed=deepcopy(original);status=failed['HelmRelease|bigbang|harbor']['status']
                if failure=='unready':status['conditions'][0]['status']='False'
                else:status['observedGeneration']=1
                state.write_text(json.dumps(failed));denied=subprocess.run(command,env=env,text=True,capture_output=True,timeout=25)
                self.assertNotEqual(denied.returncode,0);self.assertNotIn('\"patch\"',Path(str(state)+'.calls').read_text())
            state.write_text(json.dumps(original))
            result=subprocess.run(command,env=env,text=True,capture_output=True,timeout=45);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            promoted=json.loads(state.read_text());self.assertEqual(promoted['GitRepository|flux-system|cluster-config']['spec']['ref']['tag'],'v1.0.1')
            self.assertEqual(promoted['Kustomization|flux-system|cluster-root']['spec']['path'],'./big-bang-bootstrap/clusters/local-velero')
            result=subprocess.run(command,env=env,text=True,capture_output=True,timeout=30);self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertIn('changed=0',result.stdout)
            # An app or source configuration change after capture is never silently overwritten.
            promoted['Kustomization|flux-system|cluster-root']['spec']['path']='./big-bang-bootstrap/clusters/local-newer-app'
            state.write_text(json.dumps(promoted));before=Path(str(state)+'.calls').read_text().count('"patch"')
            result=subprocess.run(command,env=env,text=True,capture_output=True,timeout=25);self.assertNotEqual(result.returncode,0)
            self.assertEqual(Path(str(state)+'.calls').read_text().count('"patch"'),before)

    def test_native_runtime_values_and_foundation_render(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory); package=path/'velero'
            shutil.copytree(PACKAGE,package,ignore=shutil.ignore_patterns('__pycache__'))
            ca=path/'public-ca';ca.write_text('SYNTHETIC PUBLIC CA')
            values={'velero_runtime_enabled':True,'velero_kubelet_root':'/var/lib/kubelet','velero_data_nodes':['worker-fixture'],
                    'velero_store_hostname':'backups.internal','velero_store_bucket':'backups','velero_store_prefix':'cluster/fixture',
                    'velero_storage_node':'worker-fixture','velero_storage_path':'/disk/velero-backups','velero_quota_bytes':20*Gi,
                    'velero_store_client_cidrs':['192.0.2.6/32'],'velero_api_cidrs':['192.0.2.4/32'],'velero_store_cidrs':['192.0.2.5/32'],'velero_api_port':6443,
                    'velero_secret_files':{'ca_cert':str(ca)}}
            play=[{'hosts':'localhost','connection':'local','gather_facts':False,'vars':values,'tasks':[
                {'ansible.builtin.include_tasks':'deployment/runtime-values.yaml'},
                {'ansible.builtin.copy':{'dest':str(path/'runtime.json'),'content':'{{ velero_desired_runtime | to_json }}'}},
                {'ansible.builtin.template':{'src':'templates/foundation.yaml.j2','dest':str(path/'foundation.yaml')}}]}]
            harness=package/'fixture.yaml';harness.write_text(yaml.safe_dump(play))
            result=subprocess.run(['ansible-playbook','-i','localhost,',str(harness)],text=True,capture_output=True,timeout=30,
                                  env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(path/'ansible')})
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            runtime=json.loads((path/'runtime.json').read_text());objects=list(yaml.safe_load_all((path/'foundation.yaml').read_text()))
            node=next(x for x in objects if x['kind']=='ConfigMap' and x['metadata']['name']=='velero-node-agent')
            config=json.loads(node['data']['config.json']);self.assertEqual(config['loadConcurrency']['globalConfig'],1)
            self.assertEqual(config['loadAffinity'][0]['nodeSelector']['matchExpressions'][0]['values'],['worker-fixture'])
            backend=yaml.safe_load(runtime['data']['backend.yaml']);self.assertEqual(backend['storageNode'],'worker-fixture')
            addon=yaml.safe_load(runtime['data']['velero.yaml'])['addons']['velero'];self.assertTrue(addon['enabled'])
            self.assertEqual(addon['flux']['storageNamespace'],'velero')
            location=addon['values']['upstream']['configuration']['backupStorageLocation'][0]
            self.assertEqual(location['config']['insecureSkipTLSVerify'],'false');self.assertNotIn('checksumAlgorithm',location['config'])
            self.assertEqual(addon['values']['upstream']['schedules'],{})
            if not os.environ.get('VELERO_CHART_SOURCE') or not os.environ.get('PREFLIGHT_SOURCES_DIR') or not shutil.which('helm'):
                self.skipTest('native Ansible passed; exact Helm comparison requires pinned fixture inputs')
            from fixtures.render_helpers import helm,build,ordered_values,child_values
            base=build(ROOT/'clusters/local-harbor-app');release=next(x for x in base if x['kind']=='HelmRelease' and x['metadata']['name']=='bigbang')
            bigbang=Path(os.environ['PREFLIGHT_SOURCES_DIR'])/'bigbang/chart'
            vals=ordered_values(base,release);old=helm(bigbang,'bigbang','bigbang',vals);new=helm(bigbang,'bigbang','bigbang',vals+[runtime['data']['velero.yaml']])
            key=lambda x:(x['kind'],x['metadata'].get('namespace',''),x['metadata']['name'])
            indexed={key(x):x for x in new}
            for obj in old:self.assertEqual(indexed[key(obj)],obj,key(obj))
            vendor=helm(Path(os.environ['VELERO_CHART_SOURCE'])/'chart','velero','velero',child_values(new,'velero'),[arg for kind in ('VolumeSnapshot','VolumeSnapshotClass','VolumeSnapshotContent') for arg in ('--api-versions','snapshot.storage.k8s.io/v1/'+kind)])
            self.assertFalse(any(x['kind'] in ('Role','ClusterRole','RoleBinding','ClusterRoleBinding','ServiceAccount','CustomResourceDefinition','Schedule','Secret','ServiceMonitor','PrometheusRule') for x in vendor))
            # The exact wrapper emits the generic EBS class; the source postrenderer removes only that object.
            vsc=next(x for x in vendor if x['kind']=='VolumeSnapshotClass');self.assertEqual(vsc['metadata']['name'],'csi-volumesnapshotclass')
            ds=next(x for x in vendor if x['kind']=='DaemonSet');self.assertEqual(ds['spec']['template']['spec']['serviceAccountName'],'velero-server')
            self.assertFalse(any('hostPath' in volume for volume in ds['spec']['template']['spec']['volumes']))
            self.assertIn('--node-agent-configmap=velero-node-agent',ds['spec']['template']['spec']['containers'][0]['args'])
            store=helm(PACKAGE/'backend-chart','velero-store','velero-store',[runtime['data']['backend.yaml']])
            self.assertFalse(any(x['kind'] in ('PersistentVolume','PersistentVolumeClaim','Secret','ClusterRole','ClusterRoleBinding') for x in store))
            cfg=next(x for x in store if x['kind']=='ConfigMap')['data']['garage.toml']
            for setting in ('db_engine = "sqlite"','metadata_fsync = true','data_fsync = true','metadata_auto_snapshot_interval = "1h"','metadata_snapshots_dir = "/data/meta-snapshots"'):self.assertIn(setting,cfg)
            sts=next(x for x in store if x['kind']=='StatefulSet');self.assertFalse(sts['spec']['template']['spec']['automountServiceAccountToken'])
            self.assertEqual(sts['spec']['template']['spec']['nodeSelector'],{'kubernetes.io/hostname':'worker-fixture','kubernetes.io/arch':'amd64'})
            self.assertEqual(sts['spec']['template']['spec']['securityContext']['fsGroupChangePolicy'],'OnRootMismatch')
            self.assertEqual(sts['spec']['template']['spec']['containers'][0]['image'],'docker.io/dxflrs/garage:v2.5.0@sha256:23b16d34e0348d9aca9b960a7429a7e6d494974b5288bfb8f6c3ab856895f71e')

    def test_native_garage_single_bucket_bootstrap_and_uncertain_write(self):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from security.test_gitlab_garage_reconcile import FakeAPI
        class StoreAPI(FakeAPI):
            def __call__(self,name,body=None):
                result=super().__call__(name,body)
                if name=='GetClusterStatus':result['nodes'][0]['garageVersion']='v2.5.0'
                if name=='AllowBucketKey':
                    for bucket in self.buckets.values():
                        for grant in bucket['keys']:grant['name']='perkforge-velero-data-v1'
                return result
        api=StoreAPI()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):self.reply()
            def do_POST(self):self.reply()
            def reply(self):
                if self.headers.get('Authorization')!='Bearer synthetic-admin-token':self.send_error(403);return
                body=json.loads(self.rfile.read(int(self.headers['Content-Length']))) if self.command=='POST' else None
                try:result=api(self.path.removeprefix('/v2/'),body)
                except TimeoutError:self.send_error(503);return
                data=json.dumps(result).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory);state=path/'private';state.mkdir(mode=0o700)
                for name,value in [('admin','synthetic-admin-token'),('id','GK'+'b'*24),('key','c'*64)]:
                    f=path/name;f.write_text(value);f.chmod(0o600)
                values={'velero_garage_run':True,'velero_garage_scope':'velero-garage-init-v1','velero_garage_allow_first_layout':True,
                        'velero_garage_url':f'http://127.0.0.1:{server.server_port}','velero_garage_node':api.node,
                        'velero_garage_state_directory':str(state),'velero_garage_admin_file':str(path/'admin'),
                        'velero_garage_key_id_file':str(path/'id'),'velero_garage_key_secret_file':str(path/'key'),
                        'velero_store_bucket':'platform-backup','velero_store_capacity_bytes':20*Gi}
                inputs=path/'vars.json';inputs.write_text(json.dumps(values))
                command=['ansible-playbook','-i','localhost,',str(PACKAGE/'bootstrap-store.yaml'),'-e','@'+str(inputs)]
                env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(path/'ansible')}
                first=subprocess.run(command,env=env,text=True,capture_output=True,timeout=90)
                self.assertEqual(first.returncode,0,first.stdout+first.stderr)
                self.assertEqual(len(api.buckets),1);self.assertEqual(len(api.keys),1)
                self.assertEqual(api.keys[0]['name'],'perkforge-velero-data-v1')
                second=subprocess.run(command,env=env,text=True,capture_output=True,timeout=35)
                self.assertEqual(second.returncode,0,second.stdout+second.stderr);self.assertIn('changed=0',second.stdout)
                self.assertNotIn('c'*64,first.stdout+second.stdout)
                receipt=json.loads((state/'garage-bootstrap.json').read_text());self.assertIsNone(receipt['pending'])
                # Response loss after a real fixture mutation must stop, never blindly duplicate.
                api=StoreAPI();api.fail='CreateBucket';other=path/'uncertain';other.mkdir(mode=0o700)
                values['velero_garage_state_directory']=str(other);inputs.write_text(json.dumps(values))
                failed=subprocess.run(command,env=env,text=True,capture_output=True,timeout=90)
                self.assertNotEqual(failed.returncode,0);self.assertEqual(len(api.buckets),1)
                receipt=json.loads((other/'garage-bootstrap.json').read_text());self.assertEqual(receipt['pending']['operation'],'CreateBucket')
                before=len(api.calls);retry=subprocess.run(command,env=env,text=True,capture_output=True,timeout=25)
                self.assertNotEqual(retry.returncode,0);self.assertEqual(len(api.calls),before)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)

    def test_exact_garage_native_shape_and_version_evidence(self):
        spec=importlib.util.spec_from_file_location('velero_garage',PACKAGE/'filter_plugins/velero_garage.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        fixture=ROOT/'tests/fixtures/velero_native'
        shape=json.loads((fixture/'garage-admin-shapes.json').read_text())
        expected={k:shape['layout']['roles'][0][k] for k in ('id','zone','capacity','tags')}
        receipt={'key_imported':True,'buckets':{'velero-probe':shape['infos'][0]['id']}}
        args=[shape['status'],shape['layout'],shape['keys'],shape['key'],shape['infos'],receipt,expected['id'],shape['key']['accessKeyId'],expected,['velero-probe']]
        self.assertEqual(module.garage_verdict(*args),{'phase':'ready','missing':[],'ungranted':[]})
        shape['status']['nodes'][0]['garageVersion']='v2.2.0'
        with self.assertRaises(ValueError):module.garage_verdict(*args)
        evidence=json.loads((fixture/'evidence.json').read_text())
        self.assertEqual(evidence['garage']['version'],'2.5.0')
        self.assertEqual(evidence['garage']['metadata_engine'],'sqlite')
        self.assertEqual(evidence['garage']['retained_native_metadata_snapshots'],2)
        self.assertEqual(evidence['aws_plugin']['checksum_algorithm'],'default CRC32')
        self.assertEqual(evidence['native_bootstrap']['repeat_changes'],0)

    def test_storage_requires_quota_identity_capacity_and_existing_commitments(self):
        self.assertTrue(guard.storage_safe(*storage_fixture()))
        cases=[]
        x=storage_fixture();x[8]['velero_metadata_budget_bytes']=0;cases.append(x)
        x=storage_fixture();x[8]['velero_store_capacity_bytes']=100*Gi;cases.append(x)
        x=storage_fixture();x[0]['filesystems'][0]['options']='rw,noquota';cases.append(x)
        x=storage_fixture();x[2]='Project quota state\nAccounting: ON\nEnforcement: OFF';cases.append(x)
        x=storage_fixture();x[6]['filesystems'][0]['uuid']='other-disk';cases.append(x)
        x=storage_fixture();x[7]['diskUUID']='wrong-longhorn-disk';cases.append(x)
        x=storage_fixture();x[8]['velero_storage_path']='/disk/replicas/velero-backups';cases.append(x)
        x=storage_fixture();x[8]['velero_storage_path']='/disk/velero-backups/../replicas';cases.append(x)
        x=storage_fixture();x[4]['spec']['disks']['other']={'path':'/disk/velero-backups'};cases.append(x)
        x=storage_fixture();x[4]['spec']['disks']['one']['storageReserved']=200*Gi;cases.append(x)
        x=storage_fixture();x[0]['filesystems'][0]['avail']=100*Gi;cases.append(x)
        # Regression: physical free bytes do not erase Longhorn's scheduled replica promises.
        x=storage_fixture();x[8]['velero_quota_bytes']=700*Gi;x[3]=f'#42 0 0 {700*Gi//1024} 0 0';x[4]['spec']['disks']['one']['storageReserved']=970*Gi;cases.append(x)
        for x in cases:
            with self.subTest(case=x):self.assertFalse(guard.storage_safe(*x))

    def test_transfer_verification_binds_exact_uids_pvc_coverage_and_repository_snapshot(self):
        b,r,s,t,u,d=transfer_fixture()
        self.assertTrue(guard.copied_transfers(b,[u],[s]))
        self.assertTrue(guard.copied_transfers(r,[d],[s],[t],[u]))
        for edit in ('label','owner','pvc','phase','bytes','snapshot','duplicate','missing'):
            b,r,s,t,u,d=transfer_fixture(); transfers=[u]
            if edit=='label':u['metadata']['labels']['velero.io/backup-uid']='old'
            if edit=='owner':u['metadata']['ownerReferences'][0]['uid']='old'
            if edit=='pvc':u['metadata']['labels']['velero.io/pvc-uid']='old'
            if edit=='phase':b['status']['phase']='PartiallyFailed'
            if edit=='bytes':u['status']['progress']['bytesDone']=0
            if edit=='snapshot':u['status']['snapshotID']=''
            if edit=='duplicate':transfers.append(deepcopy(u))
            if edit=='missing':transfers=[]
            with self.subTest(edit=edit):self.assertFalse(guard.copied_transfers(b,transfers,[s]))
        for edit in ('uid','volume','snapshot','namespace','bound','partial'):
            b,r,s,t,u,d=transfer_fixture()
            if edit=='uid':t['metadata']['uid']=s['metadata']['uid']
            if edit=='volume':t['spec']['volumeName']=s['spec']['volumeName']
            if edit=='snapshot':d['spec']['snapshotID']='old'
            if edit=='namespace':d['spec']['targetVolume']['namespace']='source'
            if edit=='bound':t['status']['phase']='Pending'
            if edit=='partial':r['status']['phase']='PartiallyFailed'
            with self.subTest(edit=edit):self.assertFalse(guard.copied_transfers(r,[d],[s],[t],[u]))

    def test_runtime_rbac_has_no_global_secret_or_rbac_writes(self):
        # Template portions before the installer loop are valid YAML without expansion
        source=(PACKAGE/'templates/foundation.yaml.j2').read_text()
        runtime=source[source.index('# Runtime global'):source.index('{% for name')]
        objects=list(yaml.safe_load_all(runtime))
        cluster=next(x for x in objects if x['kind']=='ClusterRole')
        for rule in cluster['rules']:
            self.assertNotIn('*',rule['apiGroups']);self.assertNotIn('*',rule['resources']);self.assertNotIn('*',rule['verbs'])
            self.assertNotIn('secrets',rule['resources'])
            self.assertNotIn('rbac.authorization.k8s.io',rule['apiGroups'])
            if set(rule['verbs'])-{'get','list','watch'}:
                self.assertTrue(set(rule['resources'])<={'persistentvolumes','volumesnapshotcontents'})
        access=(PACKAGE/'templates/namespace-access.yaml.j2').read_text()
        self.assertNotIn('cluster-admin',access)
        self.assertNotIn('serviceaccounts',access)

    def test_new_root_preserves_existing_resources_and_only_adds_opt_in_store(self):
        def render(name):
            return list(yaml.safe_load_all(subprocess.check_output(['kubectl','kustomize',str(ROOT/'clusters'/name)],text=True)))
        key=lambda x:(x['kind'],x['metadata'].get('namespace',''),x['metadata']['name'])
        old={key(x):x for x in render('local-harbor-app')}
        new={key(x):x for x in render('local-velero')}
        self.assertEqual(set(new)-set(old),{('HelmRelease','bigbang','velero-store')})
        for k,v in old.items():
            actual=deepcopy(new[k])
            if k==('HelmRelease','bigbang','bigbang'):
                self.assertEqual(actual['spec']['valuesFrom'][-1],{'kind':'ConfigMap','name':'velero-runtime-values','valuesKey':'velero.yaml','optional':False})
                actual['spec']['valuesFrom'].pop()
                actual['spec']['postRenderers'][0]['kustomize']['patches'].pop()
            self.assertEqual(actual,v,k)
