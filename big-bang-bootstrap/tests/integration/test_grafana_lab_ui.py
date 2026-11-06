"""Optional UI adds only its route/policy; actual pinned Grafana remains unchanged."""
import copy
import os
from pathlib import Path
import unittest
import yaml
from fixtures.render_helpers import build, helm, ordered_values, child_values, release_name
from security import test_gitlab_namespace_ownership as native
ROOT = Path(__file__).resolve().parents[2]
key = lambda x: (x['kind'], x['metadata'].get('namespace'), x['metadata']['name'])

class GrafanaLabUI(unittest.TestCase):
    def test_optional_root_preserves_existing_objects_except_ui_value_reference(self):
        base = {key(x): x for x in build(ROOT/'clusters/local-metrics-limited-pilot')}
        ui = {key(x): x for x in build(ROOT/'clusters/local-metrics-limited-pilot-ui')}
        preserved=copy.deepcopy(ui)
        owner=preserved[('HelmRelease','bigbang','bigbang')]
        self.assertEqual(owner['spec']['valuesFrom'].pop(),{'kind':'ConfigMap','name':'values-grafana-lab-ui','valuesKey':'values.yaml'})
        self.assertEqual({k: preserved[k] for k in base}, base)
        self.assertEqual(set(ui)-set(base), {('Ingress','monitoring','grafana-lab'),
                                           ('NetworkPolicy','monitoring','grafana-from-traefik'),
                                           ('ConfigMap','bigbang','values-grafana-lab-ui')})
        route = ui[('Ingress','monitoring','grafana-lab')]
        self.assertEqual(route['spec']['tls'],[{'hosts':['grafana.perkforge.home.arpa'],'secretName':'grafana-local-tls'}])
        self.assertEqual(route['spec']['ingressClassName'],'traefik')
        self.assertEqual(route['spec']['rules'][0]['http']['paths'][0]['backend']['service'],
                         {'name':'monitoring-grafana','port':{'number':80}})
        policy = ui[('NetworkPolicy','monitoring','grafana-from-traefik')]['spec']
        self.assertEqual(policy['ingress'],[{'from':[{'namespaceSelector':{'matchLabels':{'kubernetes.io/metadata.name':'kube-system'}},'podSelector':{'matchLabels':{'app.kubernetes.io/name':'rke2-traefik'}}}], 'ports':[{'protocol':'TCP','port':3000}]}])
        self.assertEqual(policy['podSelector']['matchLabels'],{'app.kubernetes.io/name':'grafana','app.kubernetes.io/instance':'monitoring-grafana'})
        access=list(yaml.safe_load_all((ROOT/'configuration/observability/grafana-ui/access.yaml').read_text()))
        self.assertEqual(access[0]['rules'][0],{'apiGroups':['networking.k8s.io'],'resources':['ingresses','networkpolicies'],'verbs':['create']})
        self.assertEqual(access[1]['subjects'],[{'kind':'ServiceAccount','name':'platform-reconciler','namespace':'flux-system'}])
        self.assertTrue(all(x['metadata']['namespace']=='monitoring' for x in access))
        self.assertFalse(any(key(x) in ui for x in access))

    def test_exact_pinned_grafana_service_selector_auth_storage_and_all_manifests(self):
        sources=Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        rendered=[]
        parents=[]
        for name in ['local-metrics-limited-pilot','local-metrics-limited-pilot-ui']:
            objects=build(ROOT/'clusters'/name)
            parent=next(x for x in objects if x['kind']=='HelmRelease' and x['metadata']['name']=='bigbang')
            umbrella=native.GitLabNamespaceOwnership.render(helm(sources/'bigbang/chart','bigbang','bigbang',ordered_values(objects,parent)),parent['spec']['postRenderers'][0]['kustomize'])
            parents.append({key(x):x for x in umbrella})
            release=next(x for x in umbrella if x['kind']=='HelmRelease' and x['metadata']['name']=='grafana')
            child=helm(sources/'grafana/chart',release_name(release),'monitoring',child_values(umbrella,'grafana'))
            for renderer in release['spec'].get('postRenderers',[]):
                child=native.GitLabNamespaceOwnership.render(child,renderer['kustomize'])
            rendered.append(child)
        # Every unrelated package manifest is byte-for-byte preserved.
        changed={k for k in parents[0] if parents[0][k]!=parents[1][k]}
        self.assertEqual(changed,{('HelmRelease','bigbang','grafana'),('Secret','bigbang','bigbang-grafana-values')})
        before,after=[{key(x):copy.deepcopy(x) for x in objects} for objects in rendered]
        self.assertEqual(set(before),set(after))
        changed={k for k in before if before[k]!=after[k]}
        self.assertEqual(changed,{('ConfigMap','monitoring','monitoring-grafana'),('Deployment','monitoring','monitoring-grafana')})
        for objects in (before,after):
            objects[('ConfigMap','monitoring','monitoring-grafana')]['data'].pop('grafana.ini')
            objects[('Deployment','monitoring','monitoring-grafana')]['spec']['template']['metadata']['annotations'].pop('checksum/config')
        self.assertEqual(before,after)
        service=next(x for x in rendered[1] if x['kind']=='Service' and x['metadata']['name']=='monitoring-grafana')
        deploy=next(x for x in rendered[1] if x['kind']=='Deployment')
        self.assertEqual(service['spec']['ports'][0]['port'],80)
        self.assertTrue(all(deploy['spec']['template']['metadata']['labels'][k]==v for k,v in service['spec']['selector'].items()))
        self.assertEqual(deploy['spec']['template']['spec']['nodeSelector'],{'storage.perkforge.io/worker':'true'})
        configs='\n'.join(str(x.get('data',{})) for x in rendered[1] if x['kind']=='ConfigMap')
        self.assertIn('[auth.anonymous]\\nenabled = false',configs)
        self.assertIn('[auth.generic_oauth]',configs)
        self.assertIn('root_url = https://grafana.perkforge.home.arpa/',configs)
        self.assertIn('cookie_secure = true',configs)
        self.assertIn('enforce_domain = true',configs)
