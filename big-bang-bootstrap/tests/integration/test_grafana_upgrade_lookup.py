"""Pinned upgrade lookup against synthetic APIs; never a live cluster or Secret."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml
from fixtures.lookup_server import lookup_server
from fixtures.render_helpers import build, helm, ordered_values, child_values, release_name
from security import test_gitlab_namespace_ownership as namespace_fixture
ROOT=Path(__file__).resolve().parents[2]
render=namespace_fixture.GitLabNamespaceOwnership.render
key=lambda x:(x['kind'],x['metadata'].get('namespace'),x['metadata']['name'])
LOOKUP='/apis/helm.toolkit.fluxcd.io/v2/namespaces/bigbang/helmreleases/grafana'


def legacy(values):
    out=[]
    for text in values:
        obj=yaml.safe_load(text)
        obj.get('grafana',{}).get('values',{}).pop('autoRollingUpgrade',None)
        out.append(yaml.safe_dump(obj))
    return out


class GrafanaUpgradeLookup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources=Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        cls.role=next(x for x in yaml.safe_load_all((ROOT/'configuration/observability/metrics-prerequisites/foundation.yaml').read_text()) if x and x['kind']=='Role' and x['metadata']['name']=='grafana-installer')

    def stage(self,name):
        objects=build(ROOT/'clusters'/name)
        parent=next(x for x in objects if x['kind']=='HelmRelease' and x['metadata']['name']=='bigbang')
        return parent,ordered_values(objects,parent)

    def outer(self,parent,values):
        return render(helm(self.sources/'bigbang/chart','bigbang','bigbang',values),parent['spec']['postRenderers'][0]['kustomize'])

    def test_all_existing_roots_preserve_apps_claims_rbac_and_child_manifests(self):
        for stage in ('local','local-metrics-review','local-metrics-crds','local-metrics-pilot','local-metrics-limited-pilot','local-metrics-limited-pilot-ui','local-logging-pilot','local-logging-limited-pilot'):
            with self.subTest(stage=stage):
                parent,values=self.stage(stage)
                old,new=[self.outer(parent,v) for v in (legacy(values),values)]
                a,b=[{key(x):x for x in objects} for objects in (old,new)]
                self.assertEqual(set(a),set(b))
                if stage in ('local','local-metrics-review','local-metrics-crds'):
                    self.assertEqual(a,b);continue
                self.assertEqual({k for k in a if a[k]!=b[k]}, {('HelmRelease','bigbang','grafana'),('Secret','bigbang','bigbang-grafana-values')})
                children=[]
                for outer in (old,new):
                    hr=next(x for x in outer if x['kind']=='HelmRelease' and x['metadata']['name']=='grafana')
                    child=helm(self.sources/'grafana/chart',release_name(hr),'monitoring',child_values(outer,'grafana'))
                    for renderer in hr['spec'].get('postRenderers',[]):child=render(child,renderer['kustomize'])
                    children.append(child)
                self.assertEqual(children[0],children[1])
                # The only successful-render change is bypassing an unused lookup.
                upgrade=helm(self.sources/'grafana/chart',release_name(hr),'monitoring',child_values(new,'grafana'),('--is-upgrade',))
                for renderer in hr['spec'].get('postRenderers',[]):upgrade=render(upgrade,renderer['kustomize'])
                self.assertEqual(children[1],upgrade)

    def server_render(self,values,role,history=None,is_upgrade=True):
        with tempfile.TemporaryDirectory() as td, lookup_server(role,secrets={},helmrelease_lookup=True,monitoring_api=True,helmreleases=history) as (url,requests):
            d=Path(td);config={'apiVersion':'v1','kind':'Config','clusters':[{'name':'fixture','cluster':{'server':url}}],'users':[{'name':'fixture','user':{}}],'contexts':[{'name':'fixture','context':{'cluster':'fixture','user':'fixture'}}],'current-context':'fixture'}
            kc=d/'kubeconfig';kc.write_text(yaml.safe_dump(config));args=['helm','template','monitoring-grafana',str(self.sources/'grafana/chart'),'--namespace','monitoring','--kube-version','1.36.5','--kubeconfig',str(kc),'--dry-run=server']
            if is_upgrade:args+=['--is-upgrade']
            for i,text in enumerate(values):
                p=d/f'{i}.yaml';p.write_text(text);args+=['-f',str(p)]
            result=subprocess.run(args,capture_output=True,text=True,timeout=45,env={**os.environ,'KUBECONFIG':str(kc)})
            return result,list(requests)

    def test_real_upgrade_forbidden_lookup_reproduced_and_fixed_without_permission(self):
        parent,values=self.stage('local-metrics-limited-pilot-ui')
        old,new=[self.outer(parent,v) for v in (legacy(values),values)]
        old_values,new_values=[child_values(x,'grafana') for x in (old,new)]
        initial,requests=self.server_render(old_values,self.role,is_upgrade=False)
        self.assertEqual(initial.returncode,0,initial.stderr);self.assertNotIn(LOOKUP,requests)
        failed,requests=self.server_render(old_values,self.role)
        self.assertNotEqual(failed.returncode,0);self.assertIn('error calling lookup',failed.stderr);self.assertIn('forbidden',failed.stderr.lower());self.assertIn(LOOKUP,requests)
        fixed,requests=self.server_render(new_values,self.role)
        self.assertEqual(fixed.returncode,0,fixed.stderr);self.assertNotIn(LOOKUP,requests);self.assertFalse(any('/secrets/' in p for p in requests))
        self.assertFalse(any(x['metadata']['name'].endswith('-upgrade') or x['metadata']['name'].endswith('-upgrade-sa') for x in yaml.safe_load_all(fixed.stdout) if x))

    def test_actual_helper_history_cutoff_current_install_needs_no_migration(self):
        parent,values=self.stage('local-metrics-limited-pilot-ui');old=self.outer(parent,legacy(values));vals=child_values(old,'grafana')
        # A synthetic narrowly authorized reader establishes helper semantics only;
        # no role/grant is added to repository deployment configuration or live API.
        reader={'metadata':{'namespace':'bigbang'},'rules':[{'apiGroups':['helm.toolkit.fluxcd.io'],'resources':['helmreleases'],'resourceNames':['grafana'],'verbs':['get']}]}
        for version,expects_hook in [('13.2.4-bb.0',False),('9.2.0-bb.0',True)]:
            history={('bigbang','grafana'):{'apiVersion':'helm.toolkit.fluxcd.io/v2','kind':'HelmRelease','metadata':{'name':'grafana','namespace':'bigbang'},'status':{'history':[{'chartVersion':version}]}}}
            with self.subTest(version=version):
                result,requests=self.server_render(vals,reader,history)
                self.assertEqual(result.returncode,0,result.stderr);self.assertIn(LOOKUP,requests)
                jobs=[x for x in yaml.safe_load_all(result.stdout) if x and x['kind']=='Job' and x['metadata']['name']=='monitoring-grafana-upgrade']
                self.assertEqual(bool(jobs),expects_hook)
