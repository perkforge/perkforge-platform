"""Offline contracts for the opt-in local rollout. No live or native S3 acceptance claim."""
from copy import deepcopy
import importlib.util
import hashlib
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
            for play,flag in (('install.yaml','velero_install_apply'),('bootstrap-store.yaml','velero_garage_run'),('exercise.yaml','velero_exercise_run')):
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



    def test_native_install_remaining_path_create_and_repeat(self):
        import base64
        import configparser
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);package=path/'velero'
            shutil.copytree(PACKAGE,package,ignore=shutil.ignore_patterns('__pycache__'))
            binary=path/'kubectl';binary.write_text((ROOT/'tests/fixtures/velero_kubectl.py').read_text());binary.chmod(0o700)
            state=path/'state.json';state.write_text('{}');private=path/'private';private.mkdir(mode=0o700)
            files={name:str(private/name) for name in ['access_key','admin','ca_cert','registry','repository_password','rpc','secret_key','tls_cert','tls_key']}
            contents={'access_key':'GK'+'a'*24,'admin':'a'*32,'registry':json.dumps({'auths':{}}),
                      'repository_password':'b'*32,'rpc':'c'*64,'secret_key':'d'*64}
            for name,content in contents.items():Path(files[name]).write_text(content)
            cert=subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','2',
                '-subj','/CN=velero-store.velero-store.svc.cluster.local','-addext',
                'subjectAltName=DNS:velero-store.velero-store.svc.cluster.local',
                '-keyout',files['tls_key'],'-out',files['tls_cert']],capture_output=True,text=True)
            self.assertEqual(cert.returncode,0,cert.stderr)
            Path(files['ca_cert']).write_text(Path(files['tls_cert']).read_text())
            for file in files.values():Path(file).chmod(0o600)
            values={**yaml.safe_load((PACKAGE/'deployment/defaults.yaml').read_text()),
                'velero_schedule_namespaces':[], 'velero_data_nodes':['worker-fixture'],
                'velero_api_cidrs':['192.0.2.4/32'],'velero_kubelet_root':'/var/lib/kubelet',
                'velero_store_bucket':'backups','velero_store_prefix':'cluster/fixture',
                'velero_secret_files':files,'vk':[str(binary)]}
            tasks=yaml.safe_load((PACKAGE/'deployment/install-run.yaml').read_text())
            start=next(i for i,t in enumerate(tasks) if t.get('ansible.builtin.set_fact',{}).get('velero_write_namespaces')==[])
            harness=package/'fixture.yaml';harness.write_text(yaml.safe_dump([{
                'hosts':'localhost','connection':'local','gather_facts':False,'vars':values,'tasks':tasks[start:]}]))
            for repeat in (False,True):
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(harness)],text=True,capture_output=True,timeout=90,
                    env={**os.environ,'VELERO_FAKE_STATE':str(state),'ANSIBLE_LOCAL_TEMP':str(path/'ansible'),'KUBECONFIG':'/dev/null'})
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                if repeat:self.assertIn('changed=0',result.stdout)
            objects=json.loads(state.read_text())
            secrets=[o for o in objects.values() if o.get('kind')=='Secret']
            self.assertEqual(len(secrets),5);self.assertTrue(all(o['immutable'] for o in secrets))
            cloud=base64.b64decode(objects['Secret|velero|velero-cloud-credentials']['data']['cloud']).decode()
            config=configparser.ConfigParser();config.read_string(cloud)
            self.assertEqual(config['default']['aws_access_key_id'],contents['access_key'])
            self.assertEqual(config['default']['aws_secret_access_key'],contents['secret_key'])
            runtime=objects['ConfigMap|bigbang|velero-runtime-values']
            upstream=yaml.safe_load(runtime['data']['velero.yaml'])['addons']['velero']['values']['upstream']
            self.assertEqual(upstream['schedules'],{})

    def test_native_install_assembly_with_empty_and_selected_namespaces(self):
        tasks=yaml.safe_load((PACKAGE/'deployment/install-run.yaml').read_text())
        assembly=next(t for t in tasks if 'templates/foundation.yaml.j2' in t.get('loop',''))
        for namespaces in ([], ['tenant-fixture'], ['tenant-one','tenant-two']):
            with self.subTest(namespaces=namespaces), tempfile.TemporaryDirectory() as directory:
                path=Path(directory);package=path/'velero'
                shutil.copytree(PACKAGE,package,ignore=shutil.ignore_patterns('__pycache__'))
                values={**yaml.safe_load((PACKAGE/'deployment/defaults.yaml').read_text()),
                        'velero_namespaces':namespaces,'velero_write_namespaces':[], 'owned_objects':[],
                        'velero_data_nodes':['worker-fixture'],'velero_api_cidrs':['192.0.2.4/32'],
                        'velero_kubelet_root':'/var/lib/kubelet'}
                harness=package/'fixture.yaml'
                harness.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                    'vars':values,'tasks':[assembly,{'ansible.builtin.copy':{'dest':str(path/'objects.json'),
                        'content':'{{ owned_objects | to_json }}'}}]}]))
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(harness)],text=True,capture_output=True,timeout=30,
                    env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(path/'ansible'),'KUBECONFIG':'/dev/null'})
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                objects=json.loads((path/'objects.json').read_text())
                roles=[o for o in objects if o['kind']=='Role' and o['metadata']['name']=='velero-selected-resources']
                bindings=[o for o in objects if o['kind']=='RoleBinding' and o['metadata']['name']=='velero-selected-resources']
                self.assertEqual({o['metadata']['namespace'] for o in roles},set(namespaces))
                self.assertEqual(len(bindings),len(namespaces))
                self.assertTrue(all(o['metadata']['labels']['perkforge.io/owner']=='velero-platform-v1' for o in objects))
                self.assertEqual(len([o for o in objects if o['kind']=='PersistentVolumeClaim']),1)
                for role in roles:
                    for rule in role['rules']:
                        if rule['apiGroups']!=['snapshot.storage.k8s.io']:
                            self.assertEqual(rule['verbs'],['get','list','watch'])

    def test_native_runtime_values_and_foundation_render(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory); package=path/'velero'
            shutil.copytree(PACKAGE,package,ignore=shutil.ignore_patterns('__pycache__'))
            ca=path/'public-ca';ca.write_text('SYNTHETIC PUBLIC CA')
            values={'velero_runtime_enabled':True,'velero_kubelet_root':'/var/lib/kubelet','velero_data_nodes':['worker-fixture'],
                    'velero_store_bucket':'backups','velero_store_prefix':'cluster/fixture',
                    'velero_store_storage_class':'longhorn','velero_store_size':'5Gi',
                    'velero_api_cidrs':['192.0.2.4/32'],'velero_api_port':6443,
                    'velero_secret_files':{'ca_cert':str(ca)}}
            play=[{'hosts':'localhost','connection':'local','gather_facts':False,'vars':{**yaml.safe_load((PACKAGE/'deployment/defaults.yaml').read_text()),**values},'tasks':[
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
            backend=yaml.safe_load(runtime['data']['backend.yaml']);self.assertNotIn('storageNode',backend)
            self.assertFalse(any(x['kind']=='PersistentVolume' for x in objects))
            claim=next(x for x in objects if x['kind']=='PersistentVolumeClaim' and x['metadata']['name']=='velero-store')
            self.assertEqual(claim['spec']['storageClassName'],'longhorn')
            self.assertEqual(claim['spec']['resources']['requests']['storage'],'5Gi')
            self.assertNotIn('volumeName',claim['spec'])
            addon=yaml.safe_load(runtime['data']['velero.yaml'])['addons']['velero'];self.assertTrue(addon['enabled'])
            self.assertEqual(addon['flux']['storageNamespace'],'velero')
            location=addon['values']['upstream']['configuration']['backupStorageLocation'][0]
            self.assertEqual(location['config']['insecureSkipTLSVerify'],'false');self.assertNotIn('checksumAlgorithm',location['config'])
            self.assertEqual(location['config']['s3Url'],'https://velero-store.velero-store.svc.cluster.local')
            self.assertEqual(addon['values']['upstream']['schedules'],{})
            if not os.environ.get('VELERO_CHART_SOURCE') or not os.environ.get('PREFLIGHT_SOURCES_DIR') or not shutil.which('helm'):
                self.skipTest('native Ansible passed; exact Helm comparison requires pinned fixture inputs')
            from fixtures.render_helpers import helm,build,ordered_values,child_values
            base=build(ROOT/'clusters/local-grafana-sso');release=next(x for x in base if x['kind']=='HelmRelease' and x['metadata']['name']=='bigbang')
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
            self.assert_private_route(objects,store)
            self.assertFalse(any(x['kind'] in ('PersistentVolume','PersistentVolumeClaim','Secret','ClusterRole','ClusterRoleBinding') for x in store))
            cfg=next(x for x in store if x['kind']=='ConfigMap')['data']['garage.toml']
            for setting in ('db_engine = "sqlite"','metadata_fsync = true','data_fsync = true','metadata_auto_snapshot_interval = "1h"','metadata_snapshots_dir = "/data/meta-snapshots"'):self.assertIn(setting,cfg)
            sts=next(x for x in store if x['kind']=='StatefulSet');self.assertFalse(sts['spec']['template']['spec']['automountServiceAccountToken'])
            self.assertEqual(sts['spec']['template']['spec']['nodeSelector'],{'kubernetes.io/arch':'amd64','storage.perkforge.io/worker':'true'})
            self.assertEqual(sts['spec']['template']['spec']['securityContext']['fsGroupChangePolicy'],'OnRootMismatch')
            self.assertEqual(sts['spec']['template']['spec']['containers'][0]['image'],'docker.io/dxflrs/garage:v2.5.0@sha256:23b16d34e0348d9aca9b960a7429a7e6d494974b5288bfb8f6c3ab856895f71e')

    def assert_private_route(self, foundation, store):
        self.assertFalse(any(x['kind'] in ('Ingress','Middleware') for x in store))
        self.assertNotIn('middlewares.traefik.io',(PACKAGE/'deployment/crds.yaml').read_text())
        service=next(x for x in store if x['kind']=='Service')
        self.assertEqual(service['spec']['type'],'ClusterIP')
        self.assertEqual(service['spec']['ports'],[{'name':'https','port':443,'targetPort':'https'}])
        config=next(x for x in store if x['kind']=='ConfigMap')['data']
        evidence=json.loads((ROOT/'tests/fixtures/velero_native/private_tls_evidence.json').read_text())
        self.assertEqual(hashlib.sha256(config['nginx.conf'].encode()).hexdigest(),evidence['proxy_config_sha256'])
        self.assertTrue(evidence['security']['read_only_rootfs'])
        self.assertEqual(evidence['plain_http_tls_port_status'],400)
        self.assertIn('api_bind_addr = "127.0.0.1:3900"',config['garage.toml'])
        self.assertIn('api_bind_addr = "127.0.0.1:3903"',config['garage.toml'])
        for required in ('listen 8443 ssl;','server_name velero-store.velero-store.svc.cluster.local;',
                         'ssl_protocols TLSv1.2 TLSv1.3;','proxy_pass http://127.0.0.1:3900;',
                         'proxy_set_header Host $http_host;','proxy_http_version 1.1;',
                         'proxy_request_buffering off;','proxy_buffering off;','client_max_body_size 0;',
                         'client_body_temp_path /tmp/client-body;','proxy_temp_path /tmp/proxy;',
                         'fastcgi_temp_path /tmp/fastcgi;','uwsgi_temp_path /tmp/uwsgi;','scgi_temp_path /tmp/scgi;'):
            self.assertIn(required,config['nginx.conf'])
        pod=next(x for x in store if x['kind']=='StatefulSet')['spec']['template']['spec']
        self.assertFalse(pod.get('hostNetwork',False))
        self.assertEqual(pod['nodeSelector'],{'kubernetes.io/arch':'amd64','storage.perkforge.io/worker':'true'})
        self.assertNotIn('nodeName',pod)
        self.assertFalse(pod.get('tolerations',[]))
        tls=next(x for x in pod['containers'] if x['name']=='tls')
        self.assertRegex(tls['image'],r'^docker.io/library/nginx:1\.31\.6-alpine@sha256:[0-9a-f]{64}$')
        self.assertEqual(tls['image'],evidence['proxy_image'])
        self.assertEqual(tls['ports'],[{'name':'https','containerPort':8443}])
        self.assertTrue(tls['securityContext']['readOnlyRootFilesystem'])
        self.assertFalse(tls['securityContext']['allowPrivilegeEscalation'])
        self.assertEqual(tls['securityContext']['capabilities']['drop'],['ALL'])
        self.assertTrue(pod['securityContext']['runAsNonRoot'])
        self.assertTrue(next(x for x in tls['volumeMounts'] if x['name']=='tls')['readOnly'])
        policy=next(x for x in store if x['kind']=='NetworkPolicy')['spec']
        self.assertEqual(policy['policyTypes'],['Ingress','Egress'])
        self.assertEqual(policy['egress'],[])
        self.assertEqual(policy['ingress'],[{'from':[{'namespaceSelector':{'matchLabels':{'kubernetes.io/metadata.name':'velero'}},'podSelector':{}}],'ports':[{'protocol':'TCP','port':8443}]}])
        # Kubernetes ANDs namespace/pod selectors within this one peer; do not split them into OR peers.
        peer=policy['ingress'][0]['from'][0]
        def selected(namespace,labels):
            return namespace==peer['namespaceSelector']['matchLabels']['kubernetes.io/metadata.name'] and all(labels.get(k)==v for k,v in peer['podSelector'].get('matchLabels',{}).items())
        for labels in ({'app.kubernetes.io/name':'velero'},{'velero.io/data-upload-name':'dynamic'}, {'velero.io/repo-name':'maintenance'},{}):
            self.assertTrue(selected('velero',labels))
            self.assertFalse(selected('tenant-home-portal',labels))
            self.assertFalse(selected('kube-system',labels))
        egress=next(x for x in foundation if x['kind']=='NetworkPolicy' and x['metadata']['namespace']=='velero')['spec']['egress']
        expected={'to':[{'namespaceSelector':{'matchLabels':{'kubernetes.io/metadata.name':'velero-store'}},'podSelector':{'matchLabels':{'app':'velero-store'}}}],'ports':[{'protocol':'TCP','port':8443}]}
        self.assertIn(expected,egress)
        self.assertEqual(len(egress),3) # DNS, API, and the private store only.

    def test_native_schedule_render_preserves_scope_retention_and_pause(self):
        for paused, ttl in ((True, '48h'), (False, '72h')):
            with self.subTest(paused=paused, ttl=ttl), tempfile.TemporaryDirectory() as directory:
                path=Path(directory); package=path/'velero'
                shutil.copytree(PACKAGE,package,ignore=shutil.ignore_patterns('__pycache__'))
                ca=path/'ca';ca.write_text('SYNTHETIC PUBLIC CA')
                values={'velero_runtime_enabled':True,'velero_data_nodes':['worker-fixture'],
                        'velero_store_bucket':'backups','velero_store_prefix':'cluster/fixture',
                        'velero_secret_files':{'ca_cert':str(ca)},
                        'velero_schedule_cron':'0 */6 * * *','velero_schedule_namespaces':['velero-poc-app'],
                        'velero_schedule_paused':paused,'velero_backup_ttl':ttl}
                harness=package/'fixture.yaml'
                harness.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                    'vars':{**yaml.safe_load((PACKAGE/'deployment/defaults.yaml').read_text()),**values},'tasks':[
                        {'ansible.builtin.include_tasks':'deployment/runtime-values.yaml'},
                        {'ansible.builtin.copy':{'dest':str(path/'runtime.json'),'content':'{{ velero_desired_runtime | to_json }}'}}]}]))
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(harness)],text=True,capture_output=True,timeout=30,
                    env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(path/'ansible')})
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                runtime=json.loads((path/'runtime.json').read_text())
                upstream=yaml.safe_load(runtime['data']['velero.yaml'])['addons']['velero']['values']['upstream']
                schedule=upstream['schedules']['local-poc']
                self.assertEqual(upstream['configuration']['defaultBackupTTL'],ttl)
                self.assertEqual(schedule['schedule'],'0 */6 * * *')
                self.assertEqual(schedule['paused'],paused)
                self.assertEqual(schedule['template']['includedNamespaces'],['velero-poc-app'])
                self.assertFalse(schedule['template']['includeClusterResources'])
                self.assertTrue(schedule['template']['snapshotMoveData'])
                self.assertEqual(schedule['template']['ttl'],ttl)
                self.assertFalse(schedule['useOwnerReferencesInBackup'])
                if not os.environ.get('VELERO_CHART_SOURCE') or not shutil.which('helm'):
                    self.skipTest('native schedule values passed; exact chart fixture required')
                from fixtures.render_helpers import helm
                rendered=helm(Path(os.environ['VELERO_CHART_SOURCE'])/'chart','velero','velero',[yaml.safe_dump({'upstream':upstream})],[arg for kind in ('VolumeSnapshot','VolumeSnapshotClass','VolumeSnapshotContent') for arg in ('--api-versions','snapshot.storage.k8s.io/v1/'+kind)])
                native=next(x for x in rendered if x['kind']=='Schedule')
                self.assertEqual(native['spec'].get('paused',False),paused)
                self.assertEqual(native['spec']['template'],schedule['template'])

    def test_baseline_uses_no_host_storage_or_custom_promotion_framework(self):
        for name in ('prepare.yaml','recovery.yaml','request.example.yaml','deployment/host-preflight.yaml',
                     'deployment/promote.yaml','deployment/read-selectors.yaml','deployment/recovery-run.yaml'):
            self.assertFalse((PACKAGE/name).exists(),name)
        defaults=yaml.safe_load((PACKAGE/'deployment/defaults.yaml').read_text())
        self.assertFalse(defaults['velero_install_apply'])
        self.assertTrue(defaults['velero_schedule_paused'])
        self.assertEqual(defaults['velero_schedule_cron'],'')
        self.assertEqual(defaults['velero_backup_ttl'],'48h')
        self.assertEqual(defaults['velero_store_storage_class'],'longhorn')
        self.assertEqual(yaml.safe_load((PACKAGE/'profiles/aws.yaml').read_text())['profile']['retention_hours'],336)
        local=yaml.safe_load((PACKAGE/'profiles/local.yaml').read_text())['profile']
        self.assertEqual(local['retention_hours'],48)
        self.assertEqual(local['backing'],'longhorn-pvc')
        self.assertFalse(local['independent_failure_domain'])

    def test_native_runtime_create_repeat_update_and_foreign_owner_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);package=path/'velero'
            shutil.copytree(PACKAGE,package,ignore=shutil.ignore_patterns('__pycache__'))
            binary=path/'kubectl';binary.write_text((ROOT/'tests/fixtures/velero_kubectl.py').read_text());binary.chmod(0o700)
            state=path/'state.json';state.write_text('{}')
            desired={'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'velero-runtime-values','namespace':'bigbang','labels':{'perkforge.io/owner':'velero-platform-v1'}},'data':{'backend.yaml':'backend','velero.yaml':'paused'}}
            harness=package/'fixture.yaml'
            def run():
                harness.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                    'vars':{'vk':[str(binary)],'velero_desired_runtime':desired},
                    'tasks':[{'ansible.builtin.include_tasks':'deployment/update-runtime.yaml'}]}]))
                return subprocess.run(['ansible-playbook','-i','localhost,',str(harness)],text=True,capture_output=True,timeout=30,
                    env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(path/'ansible'),'VELERO_FAKE_STATE':str(state)})
            first=run();self.assertEqual(first.returncode,0,first.stdout+first.stderr)
            repeat=run();self.assertEqual(repeat.returncode,0,repeat.stdout+repeat.stderr);self.assertIn('changed=0',repeat.stdout)
            desired['data']['velero.yaml']='approved schedule settings'
            update=run();self.assertEqual(update.returncode,0,update.stdout+update.stderr)
            current=json.loads(state.read_text());key='ConfigMap|bigbang|velero-runtime-values'
            self.assertEqual(current[key]['data'],desired['data'])
            calls=[json.loads(line) for line in Path(str(state)+'.calls').read_text().splitlines()]
            patch=next(call for call in calls if call[0]=='patch')
            self.assertEqual(json.loads(patch[patch.index('-p')+1])[0]['path'],'/metadata/resourceVersion')
            current[key]['metadata']['labels']['perkforge.io/owner']='another-owner';state.write_text(json.dumps(current))
            before=Path(str(state)+'.calls').read_text().count('"patch"');failed=run()
            self.assertNotEqual(failed.returncode,0)
            self.assertEqual(Path(str(state)+'.calls').read_text().count('"patch"'),before)
            current[key]['metadata']['labels']['perkforge.io/owner']='velero-platform-v1'
            current['inject_runtime_conflict']=True;state.write_text(json.dumps(current))
            previous=deepcopy(current[key]['data']);desired['data']['velero.yaml']='newer requested settings'
            conflict=run();self.assertNotEqual(conflict.returncode,0)
            self.assertIn('compare-and-swap refused',conflict.stdout+conflict.stderr)
            self.assertEqual(json.loads(state.read_text())[key]['data'],previous)

    def test_invalid_schedule_inputs_fail_before_api_or_release_lookup(self):
        valid={'velero_install_apply':True,'velero_install_scope':'velero-foundation-v1',
            'velero_release_tag':'v1.0.0','velero_release_commit':'a'*40,'velero_data_nodes':['worker-fixture'],
            'velero_api_cidrs':['192.0.2.4/32'],
            'velero_store_bucket':'backups','velero_store_prefix':'cluster/fixture',
            'velero_schedule_cron':'0 */6 * * *','velero_schedule_namespaces':['poc-app']}
        for bad in ({'velero_schedule_namespaces':[]},{'velero_schedule_namespaces':['*']},
                    {'velero_schedule_namespaces':['poc-app','poc-app']},{'velero_backup_ttl':'0h'},
                    {'velero_schedule_paused':'false'},{'velero_schedule_cron':'99 * * * *'},
                    {'velero_store_hostname':'shared-ingress.internal'}):
            with self.subTest(bad=bad),tempfile.TemporaryDirectory() as directory:
                path=Path(directory);binary=path/'bin';binary.mkdir();marker=path/'unexpected'
                for name in ('kubectl','git','curl','ssh'):
                    p=binary/name;p.write_text('#!/bin/sh\necho called > "$API_MARKER"\nexit 99\n');p.chmod(0o700)
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(PACKAGE/'install.yaml'),'-e',json.dumps({**valid,**bad})],
                    text=True,capture_output=True,timeout=30,env={**os.environ,'PATH':str(binary)+os.pathsep+os.environ['PATH'],
                    'API_MARKER':str(marker),'ANSIBLE_LOCAL_TEMP':str(path/'ansible'),'KUBECONFIG':'/dev/null'})
                self.assertNotEqual(result.returncode,0)
                self.assertFalse(marker.exists(),result.stdout+result.stderr)

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
        old={key(x):x for x in render('local-grafana-sso')}
        new={key(x):x for x in render('local-velero')}
        self.assertEqual(set(new)-set(old),{('HelmRelease','bigbang','velero-store')})
        for k,v in old.items():
            actual=deepcopy(new[k])
            if k==('HelmRelease','bigbang','bigbang'):
                self.assertEqual(actual['spec']['valuesFrom'][-1],{'kind':'ConfigMap','name':'velero-runtime-values','valuesKey':'velero.yaml','optional':False})
                actual['spec']['valuesFrom'].pop()
                actual['spec']['postRenderers'][0]['kustomize']['patches'].pop()
            self.assertEqual(actual,v,k)
