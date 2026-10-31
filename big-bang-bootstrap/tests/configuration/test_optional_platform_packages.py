"""Native offline Big Bang/child renders; never apply or contact a Kubernetes API."""
import os
from pathlib import Path
import tempfile
import unittest
import yaml
from fixtures.render_helpers import build, helm, ordered_values, application_package_fixture

ROOT=Path(__file__).resolve().parents[2]

class OptionalPlatformPackages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources=Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        cls.root=build(ROOT/'clusters/local')
        cls.parent=next(x for x in cls.root if x['kind']=='HelmRelease')
        cls.inputs=application_package_fixture(ROOT)+build(ROOT/'configuration/packages/longhorn')+build(ROOT/'configuration/packages/rancher')
        outer=helm(cls.sources/'bigbang/chart','bigbang','bigbang',ordered_values(cls.inputs,cls.parent))
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);(p/'render.yaml').write_text(yaml.safe_dump_all(outer))
            (p/'kustomization.yaml').write_text(yaml.safe_dump({'apiVersion':'kustomize.config.k8s.io/v1beta1','kind':'Kustomization','resources':['render.yaml'],**cls.parent['spec']['postRenderers'][0]['kustomize']}))
            cls.outer=build(p)
        cls.children={}
        for name,namespace in [('longhorn','longhorn-system'),('rancher','cattle-system')]:
            values=next(x for x in cls.outer if x['kind']=='Secret' and x['metadata']['name']==name+'-values')['stringData']['values.yaml']
            cls.children[name]=helm(cls.sources/name,name,namespace,[values])

    def test_current_root_selects_only_active_longhorn_behind_paused_seed(self):
        self.assertFalse(self.parent['spec']['suspend'])
        names={x['metadata']['name'] for x in self.root}
        self.assertIn('values-longhorn', names)
        self.assertFalse({'values-headlamp','values-keycloak','values-rancher','values-openbao','rancher-official','tenant-enrollments'} & names)
        outer=helm(self.sources/'bigbang/chart','bigbang','bigbang',ordered_values(self.root,self.parent))
        releases={x['metadata']['name']:x for x in outer if x['kind']=='HelmRelease'}
        self.assertEqual(set(releases), {'longhorn'})
        self.assertFalse(releases['longhorn']['spec']['suspend'])
        self.assertEqual({x['metadata']['name'] for x in outer if x['kind']=='GitRepository'}, {'longhorn','bigbang-wrapper'})
        self.assertFalse(any(x['kind'] in ['Deployment','StatefulSet','PersistentVolumeClaim','Namespace','ClusterRole','ClusterRoleBinding'] for x in outer))
        self.assertFalse(any(x['kind']=='Kustomization' for x in self.root))

    def test_opt_in_graph_and_external_rancher_credential(self):
        releases={x['metadata']['name']:x for x in self.outer if x['kind']=='HelmRelease'}
        for name in ['longhorn','rancher']:
            self.assertEqual(releases[name]['spec']['suspend'], name != 'longhorn')
            self.assertEqual(releases[name]['spec']['serviceAccountName'],name+'-installer')
        self.assertIn({'name':'longhorn','namespace':'bigbang'},releases['keycloak']['spec']['dependsOn'])
        self.assertFalse(releases['rancher']['spec'].get('dependsOn'))
        ref=releases['rancher']['spec']['valuesFrom'][-1]
        self.assertEqual(ref,dict(kind='Secret',name='rancher-bootstrap-values',valuesKey='values.yaml',optional=False))
        self.assertFalse(any(x['kind']=='Secret' and x['metadata']['name']=='rancher-bootstrap-values' for x in self.inputs))
        source=next(x for x in self.outer if x['kind']=='GitRepository' and x['metadata']['name']=='longhorn')
        self.assertEqual(source['spec']['ref']['tag'],'longhorn-1.13.0')
        repo=next(x for x in self.inputs if x['kind']=='HelmRepository' and x['metadata']['name']=='rancher-official')
        self.assertEqual(repo['spec']['url'],'https://releases.rancher.com/server-charts/stable')

    def test_longhorn_render_has_worker_placement_and_retained_two_replica_class(self):
        objects=self.children['longhorn']
        for obj in objects:
            if obj['kind'] in ['DaemonSet','Deployment']:
                self.assertEqual(obj['spec']['template']['spec']['nodeSelector'],{'storage.perkforge.io/worker':'true'})
        maps={x['metadata']['name']:x for x in objects if x['kind']=='ConfigMap'}
        sc=yaml.safe_load(maps['longhorn-storageclass']['data']['storageclass.yaml'])
        self.assertEqual(sc['parameters']['numberOfReplicas'],'2')
        self.assertEqual(sc['reclaimPolicy'],'Retain')
        self.assertTrue(sc['allowVolumeExpansion'])
        self.assertEqual(sc['metadata']['annotations']['storageclass.kubernetes.io/is-default-class'],'false')
        settings=yaml.safe_load(maps['longhorn-default-setting']['data']['default-setting.yaml'])
        self.assertFalse(settings['v2-data-engine'])
        self.assertFalse(settings['replica-soft-anti-affinity'])
        self.assertEqual(str(settings['storage-over-provisioning-percentage']),'100')
        self.assertEqual(str(settings['storage-minimal-available-percentage']),'25')
        self.assertTrue(settings['create-default-disk-labeled-nodes'])

    def test_rancher_strict_tls_and_no_generated_bootstrap_or_cert_manager(self):
        objects=self.children['rancher']
        self.assertFalse(any(x['kind'] in ['Certificate','Issuer','ClusterIssuer','PersistentVolumeClaim'] for x in objects))
        deployment=next(x for x in objects if x['kind']=='Deployment' and x['metadata']['name']=='rancher')
        text=yaml.safe_dump(deployment)
        self.assertIn('continuous-delivery=false',text)
        self.assertIn('strict',text)
        self.assertIn('secretName: tls-ca',text)
        self.assertIn('cacerts.pem',text)
        self.assertIn('secretName: tls-ca-additional',text)
        ingress=next(x for x in objects if x['kind']=='Ingress')
        self.assertEqual(ingress['spec']['ingressClassName'],'traefik')
        self.assertEqual(ingress['spec']['tls'][0]['secretName'],'tls-rancher-ingress')

    def test_keycloak_alternate_claim_has_no_static_binding(self):
        objects=build(ROOT/'configuration/packages/keycloak/prerequisites-longhorn')
        self.assertFalse(any(x['kind'] in ['PersistentVolume','StorageClass'] for x in objects))
        claim=next(x for x in objects if x['kind']=='PersistentVolumeClaim')
        self.assertEqual(claim['spec']['storageClassName'],'longhorn')
        self.assertNotIn('volumeName',claim['spec'])
        self.assertEqual(claim['spec']['resources']['requests']['storage'],'4Gi')

    def test_pinned_chart_cluster_rbac_and_objects_covered_by_prerequisites(self):
        mapping={'CustomResourceDefinition':('apiextensions.k8s.io','customresourcedefinitions'),
                 'ClusterRole':('rbac.authorization.k8s.io','clusterroles'),
                 'ClusterRoleBinding':('rbac.authorization.k8s.io','clusterrolebindings'),
                 'PriorityClass':('scheduling.k8s.io','priorityclasses')}
        for name in ['longhorn','rancher']:
            foundation=build(ROOT/'configuration/packages'/name/'prerequisites')
            rules=next(x for x in foundation if x['kind']=='ClusterRole')['rules']
            for obj in self.children[name]:
                if obj['kind'] not in mapping:continue
                group,resource=mapping[obj['kind']]
                for verb in ['get','create','patch','delete']:
                    self.assertTrue(any(group in r['apiGroups'] and resource in r['resources'] and verb in r['verbs'] and ('resourceNames' not in r or obj['metadata']['name'] in r['resourceNames']) for r in rules),(name,obj['kind'],obj['metadata']['name'],verb))
            self.assertFalse(any('*' in r.get('verbs',[])+r.get('resources',[])+r.get('apiGroups',[]) for r in rules))

if __name__=='__main__':unittest.main()
