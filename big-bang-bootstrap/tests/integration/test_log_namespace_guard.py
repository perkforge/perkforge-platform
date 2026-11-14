"""Offline real Ansible rendering; no credentials, Kubernetes or namespace writes."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'big-bang-bootstrap/configuration/observability/log-namespace-guard'
UID = '11111111-1111-4111-8111-111111111111'

def inputs(output):
    context = yaml.safe_load((ROOT/'big-bang-bootstrap/configuration/authorization/contexts/portal.yaml').read_text())['paas_context']
    return dict(log_namespace_guard_render=True, log_context=context,
        log_namespace='tenant-portal', log_namespace_uid=UID, log_scope_id='portal-runtime-v1',
        log_namespace_owner_labels={'platform.perkforge.io/portal-runtime':'true'},
        log_namespace_observed={'apiVersion':'v1','kind':'Namespace','metadata':{
            'name':'tenant-portal','uid':UID,'resourceVersion':'123',
            'labels':{'platform.perkforge.io/portal-runtime':'true','pod-security.kubernetes.io/enforce':'restricted'},
            'annotations':{'unrelated':'preserve'}}}, log_guard_output=str(output))

def render(data, check=False):
    return subprocess.run(['ansible-playbook','-i','localhost,',str(SOURCE/'render.yaml'),'-e',json.dumps(data)] + (['--check'] if check else []),
        capture_output=True,text=True,env=dict(os.environ,KUBECONFIG='/dev/null'))

class NamespaceGuard(unittest.TestCase):
    def test_default_check_inert(self):
        self.assertEqual(render({}).returncode,0)
        # Even selected check mode needs neither private metadata nor destination.
        self.assertEqual(render({'log_namespace_guard_render':True},True).returncode,0)

    def test_exact_native_policy_and_additive_cas(self):
        with tempfile.TemporaryDirectory() as temp:
            data=inputs(Path(temp)/'out'); run=render(data)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            policy,binding=list(yaml.safe_load_all((Path(temp)/'out/policy.yaml').read_text()))
            rules=policy['spec']['matchConstraints']['resourceRules']
            self.assertEqual(rules,[{'apiGroups':[''],'apiVersions':['v1'], 'operations':['CREATE','UPDATE','DELETE'],
                'resources':['namespaces','namespaces/status','namespaces/finalize'],'resourceNames':['tenant-portal'],'scope':'Cluster'}])
            self.assertEqual(policy['spec']['failurePolicy'],'Fail')
            self.assertEqual(binding['spec'],{'policyName':policy['metadata']['name'],'validationActions':['Deny']})
            patch=json.loads((Path(temp)/'out/namespace-patch.json').read_text())
            self.assertEqual(patch[:3],[{'op':'test','path':'/metadata/uid','value':UID},
                {'op':'test','path':'/metadata/resourceVersion','value':'123'},
                {'op':'test','path':'/metadata/annotations','value':{'unrelated':'preserve'}}])
            self.assertEqual(patch[-1]['value'],{'unrelated':'preserve','platform.perkforge.io/log-context':'portal','platform.perkforge.io/log-scope':'portal-runtime-v1'})
            self.assertFalse(any('labels' in p['path'] for p in patch))
            self.assertNotEqual(render(data).returncode,0) # do not overwrite artifacts

    def test_foreign_stale_deleting_and_conflicting_inputs_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            base=inputs(Path(temp)/'out')
            cases=[]
            for key,value in [('log_namespace','tenant-portal-config'),('log_namespace_uid','22222222-2222-4222-8222-222222222222'),('log_scope_id','platform-unassigned-v1')]:
                d=copy.deepcopy(base); d[key]=value; cases.append(d)
            for key,value in [('uid','22222222-2222-4222-8222-222222222222'),('deletionTimestamp','2026-01-01T00:00:00Z')]:
                d=copy.deepcopy(base);d['log_namespace_observed']['metadata'][key]=value;cases.append(d)
            d=copy.deepcopy(base);d['log_namespace_observed']['metadata']['labels']={};cases.append(d)
            d=copy.deepcopy(base);d['log_namespace_observed']['metadata']['annotations']['platform.perkforge.io/log-scope']='prior-owner-v1';cases.append(d)
            for data in cases:
                self.assertNotEqual(render(data).returncode,0)
                self.assertFalse((Path(temp)/'out').exists())

    def test_missing_annotations_and_idempotent_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            data=inputs(Path(temp)/'out'); del data['log_namespace_observed']['metadata']['annotations']
            run=render(data);self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            patch=json.loads((Path(temp)/'out/namespace-patch.json').read_text())
            self.assertEqual(len(patch),3) # resourceVersion CAS protects absent map too
            self.assertEqual(patch[-1]['op'],'add')
