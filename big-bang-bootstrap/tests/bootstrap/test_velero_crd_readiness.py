"""Native Ansible readiness checks; no cluster connection or mutations."""
import json
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'configuration/packages/velero'


class VeleroCSIReadiness(unittest.TestCase):
    def test_crd_storage_version_boolean_is_not_a_resource_quantity(self):
        spec=importlib.util.spec_from_file_location('velero_guard',PACKAGE/'filter_plugins/velero_guard.py')
        guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
        desired={'apiVersion':'apiextensions.k8s.io/v1','kind':'CustomResourceDefinition',
                 'metadata':{'name':'sample.velero.io','labels':{'perkforge.io/owner':'velero-platform-v1'}},
                 'spec':{'versions':[{'name':'v1','served':True,'storage':True}]}}
        actual=json.loads(json.dumps(desired))
        self.assertTrue(guard.owned_matches(actual,desired))
        actual['spec']['versions'][0]['storage']=False
        self.assertFalse(guard.owned_matches(actual,desired))
        actual['spec']['versions'][0]['storage']='True'
        self.assertFalse(guard.owned_matches(actual,desired))
        volume={'kind':'PersistentVolumeClaim','metadata':desired['metadata'],
                'spec':{'resources':{'requests':{'storage':'5Gi'}}}}
        actual=json.loads(json.dumps(volume));actual['spec']['resources']['requests']['storage']='5368709120'
        self.assertTrue(guard.owned_matches(actual,volume))
        actual['spec']['resources']['requests']['storage']='4Gi'
        self.assertFalse(guard.owned_matches(actual,volume))

    def test_omitted_deny_rules_preserve_exact_network_policy_semantics(self):
        spec=importlib.util.spec_from_file_location('velero_guard',PACKAGE/'filter_plugins/velero_guard.py')
        guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
        desired={'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy',
                 'metadata':{'name':'isolation','labels':{'perkforge.io/owner':'velero-platform-v1'}},
                 'spec':{'podSelector':{},'policyTypes':['Ingress','Egress'],'ingress':[],'egress':[]}}
        actual=json.loads(json.dumps(desired));del actual['spec']['ingress'];del actual['spec']['egress']
        self.assertTrue(guard.owned_matches(actual,desired))
        self.assertNotIn('ingress',actual['spec'])
        for edit in ('allow-ingress','allow-egress','selector','policy-types'):
            changed=json.loads(json.dumps(actual))
            if edit=='allow-ingress':changed['spec']['ingress']=[{}]
            if edit=='allow-egress':changed['spec']['egress']=[{}]
            if edit=='selector':changed['spec']['podSelector']={'matchLabels':{'app':'other'}}
            if edit=='policy-types':changed['spec']['policyTypes']=['Egress']
            with self.subTest(edit=edit):self.assertFalse(guard.owned_matches(changed,desired))

    def test_native_readiness_reads_json_and_rejects_bad_conditions(self):
        tasks = yaml.safe_load((PACKAGE / 'deployment/crds.yaml').read_text())[:2]
        self.assertEqual(len(tasks[0]['loop']), 3)
        for case in ('ready', 'false', 'missing', 'wrong-name', 'duplicate', 'malformed'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                binary = path / 'kubectl'
                binary.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
args=sys.argv[1:]
with Path(os.environ['CALLS']).open('a') as f:f.write(json.dumps(args)+'\\n')
assert len(args)==5 and args[:2]==['get','crd'] and args[-2:]==['-o','json'],args
case=os.environ['CASE']
if case=='malformed':print('not-json');raise SystemExit(0)
conditions=[{'type':'Established','status':'True'}]
if case=='false':conditions[0]['status']='False'
if case=='missing':conditions=[]
if case=='duplicate':conditions*=2
print(json.dumps({'metadata':{'name':'other' if case=='wrong-name' else args[2]},'status':{'conditions':conditions}}))
''')
                binary.chmod(0o700)
                harness = path / 'fixture.yaml'
                harness.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                    'vars':{'vk':[str(binary)]},'tasks':tasks}]))
                calls=path/'calls.jsonl'
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(harness)],text=True,capture_output=True,timeout=30,
                    env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(path/'ansible'),'CALLS':str(calls),'CASE':case,'KUBECONFIG':'/dev/null'})
                if case=='ready':self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                else:self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                observed=[json.loads(line) for line in calls.read_text().splitlines()]
                self.assertEqual([call[2] for call in observed],tasks[0]['loop'])
                self.assertTrue(all(call[:2]==['get','crd'] and call[-2:]==['-o','json'] for call in observed))
                self.assertIn('changed=0',result.stdout)
