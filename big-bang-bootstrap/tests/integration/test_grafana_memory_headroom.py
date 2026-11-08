"""Pinned renders prove only Grafana's memory limit changes; no live API."""
import copy
import os
from pathlib import Path
import unittest
import yaml
from fixtures.render_helpers import build,helm,ordered_values,child_values,release_name
from security import test_gitlab_namespace_ownership as native
ROOT=Path(__file__).resolve().parents[2]
key=lambda x:(x['kind'],x['metadata'].get('namespace'),x['metadata']['name'])


def previous(values):
    out=[]
    for text in values:
        obj=yaml.safe_load(text)
        resources=obj.get('grafana',{}).get('values',{}).get('upstream',{}).get('resources')
        if resources:resources['limits']['memory']='512Mi'
        out.append(yaml.safe_dump(obj))
    return out


class GrafanaMemoryHeadroom(unittest.TestCase):
    def test_affected_roots_preserve_requests_security_storage_and_unrelated_apps(self):
        sources=Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        stages=('local','local-metrics-crds','local-metrics-pilot','local-metrics-limited-pilot',
                'local-metrics-limited-pilot-ui','local-logging-pilot','local-logging-limited-pilot',
                'local-harbor-app','local-grafana-sso')
        for stage in stages:
            with self.subTest(stage=stage):
                objects=build(ROOT/'clusters'/stage)
                parent=next(x for x in objects if x['kind']=='HelmRelease' and x['metadata']['name']=='bigbang')
                selected=ordered_values(objects,parent)
                outer=[native.GitLabNamespaceOwnership.render(helm(sources/'bigbang/chart','bigbang','bigbang',v),parent['spec']['postRenderers'][0]['kustomize']) for v in (previous(selected),selected)]
                before,after=[{key(x):x for x in docs} for docs in outer]
                self.assertEqual(set(before),set(after))
                if stage in ('local','local-metrics-crds'):
                    self.assertEqual(before,after);continue
                self.assertEqual({k for k in before if before[k]!=after[k]}, {('HelmRelease','bigbang','grafana'),('Secret','bigbang','bigbang-grafana-values')})
                hr=next(x for x in outer[1] if x['kind']=='HelmRelease' and x['metadata']['name']=='grafana')
                for upgrade in (False,True):
                    with self.subTest(upgrade=upgrade):
                        children=[]
                        for parent_objects in outer:
                            docs=helm(sources/'grafana/chart',release_name(hr),'monitoring',child_values(parent_objects,'grafana'),('--is-upgrade',) if upgrade else ())
                            for renderer in hr['spec'].get('postRenderers',[]):docs=native.GitLabNamespaceOwnership.render(docs,renderer['kustomize'])
                            children.append({key(x):copy.deepcopy(x) for x in docs})
                        old,new=children;self.assertEqual(set(old),set(new))
                        deployment=('Deployment','monitoring','monitoring-grafana')
                        self.assertEqual({k for k in old if old[k]!=new[k]},{deployment})
                        containers=[x[deployment]['spec']['template']['spec']['containers'] for x in (old,new)]
                        old_main,new_main=[next(c for c in cs if c['name']=='grafana') for cs in containers]
                        self.assertEqual(old_main['resources']['limits']['memory'],'512Mi')
                        self.assertEqual(new_main['resources']['limits']['memory'],'1Gi')
                        self.assertEqual(new_main['resources']['requests'],{'cpu':'100m','memory':'256Mi'})
                        old_go,new_go=[next(e for e in c.get('env',[]) if e['name']=='GOMEMLIMIT') for c in (old_main,new_main)]
                        self.assertEqual(old_go['value'],'460MiB')
                        self.assertEqual(new_go['value'],'921MiB')
                        new_go['value']=old_go['value']
                        new_main['resources']['limits']['memory']='512Mi'
                        self.assertEqual(old,new)
