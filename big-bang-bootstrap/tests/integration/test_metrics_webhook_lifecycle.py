"""Actual pinned admission install/upgrade lifecycle; no API or real certificates."""
from pathlib import Path
import os
import unittest
import yaml
from fixtures.render_helpers import build,helm,ordered_values,child_values,release_name
from security import test_gitlab_namespace_ownership as namespace_fixture
ROOT=Path(__file__).resolve().parents[2]
render=namespace_fixture.GitLabNamespaceOwnership.render
key=lambda x:(x['kind'],x['metadata'].get('namespace'),x['metadata']['name'])
NAME='monitoring-monitoring-kube-admission'


class MetricsWebhookLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources=Path(os.environ['PREFLIGHT_SOURCES_DIR'])

    def selected(self,stage,upgrade=False,extra=None):
        objects=build(ROOT/'clusters'/stage)
        parent=next(x for x in objects if x['kind']=='HelmRelease' and x['metadata']['name']=='bigbang')
        outer=render(helm(self.sources/'bigbang/chart','bigbang','bigbang',ordered_values(objects,parent)),parent['spec']['postRenderers'][0]['kustomize'])
        hr=next(x for x in outer if x['kind']=='HelmRelease' and x['metadata']['name']=='monitoring')
        values=child_values(outer,'monitoring')
        if extra:values.append(yaml.safe_dump(extra))
        args=('--api-versions','monitoring.coreos.com/v1','--api-versions','monitoring.coreos.com/v1alpha1')+(('--is-upgrade',) if upgrade else ())
        child=helm(self.sources/'monitoring/chart',release_name(hr),'monitoring',values,args)
        for renderer in hr['spec'].get('postRenderers',[]):child=render(child,renderer['kustomize'])
        return {key(x):x for x in child}

    def test_install_vs_upgrade_policy_and_native_hook_ordering(self):
        for stage in ('local-metrics-pilot','local-metrics-limited-pilot','local-metrics-limited-pilot-ui'):
            for upgrade in (False,True):
                with self.subTest(stage=stage,upgrade=upgrade):
                    objects=self.selected(stage,upgrade)
                    expected='Fail' if upgrade else 'Ignore'
                    entries=[]
                    for kind in ('MutatingWebhookConfiguration','ValidatingWebhookConfiguration'):
                        obj=objects[(kind,None,NAME)]
                        entries+=obj['webhooks']
                        for entry in obj['webhooks']:
                            self.assertEqual(entry['failurePolicy'],expected)
                            self.assertNotIn('caBundle',entry['clientConfig'])
                            self.assertEqual(entry['clientConfig']['service']['namespace'],'monitoring')
                            self.assertEqual(entry['clientConfig']['service']['name'],'monitoring-monitoring-kube-operator')
                            self.assertEqual(entry['clientConfig']['service'].get('port',443),443)
                            self.assertNotIn('url',entry['clientConfig'])
                            paths={'prometheusrulemutate.monitoring.coreos.com':'/admission-prometheusrules/mutate','prometheusrulevalidate.monitoring.coreos.com':'/admission-prometheusrules/validate','alertmanagerconfigsvalidate.monitoring.coreos.com':'/admission-alertmanagerconfigs/validate'}
                            self.assertEqual(entry['clientConfig']['service']['path'],paths[entry['name']])
                    self.assertEqual({x['name'] for x in entries},{'prometheusrulemutate.monitoring.coreos.com','prometheusrulevalidate.monitoring.coreos.com','alertmanagerconfigsvalidate.monitoring.coreos.com'})
                    create=objects[('Job','monitoring',NAME+'-create')]
                    patch=objects[('Job','monitoring',NAME+'-patch')]
                    self.assertEqual(create['metadata']['annotations']['helm.sh/hook'],'pre-install,pre-upgrade')
                    self.assertEqual(patch['metadata']['annotations']['helm.sh/hook'],'post-install,post-upgrade')
                    args=patch['spec']['template']['spec']['containers'][0]['args']
                    self.assertIn('--patch-failure-policy='+expected,args)
                    self.assertIn('--secret-name='+NAME,args)
                    self.assertIn('--webhook-name='+NAME,args)
                    self.assertEqual(patch['spec']['template']['spec']['imagePullSecrets'],[{'name':'private-registry'}])

    def test_ca_value_is_ignored_while_native_patch_owns_injection(self):
        synthetic='c3ludGhldGljLXB1YmxpYy1jYS1vbmx5'
        for enabled in (True,False):
            with self.subTest(patch=enabled):
                objects=self.selected('local-metrics-limited-pilot-ui',True,{'upstream':{'prometheusOperator':{'admissionWebhooks':{'caBundle':synthetic,'patch':{'enabled':enabled}}}}})
                for kind in ('MutatingWebhookConfiguration','ValidatingWebhookConfiguration'):
                    for entry in objects[(kind,None,NAME)]['webhooks']:
                        self.assertEqual(entry['failurePolicy'],'Fail')
                        if enabled:self.assertNotIn('caBundle',entry['clientConfig'])
                        else:self.assertEqual(entry['clientConfig']['caBundle'],synthetic)
                self.assertEqual(('Job','monitoring',NAME+'-patch') in objects,enabled)

    def test_policy_normalization_preserves_all_other_rendered_resources(self):
        before,after=[self.selected('local-metrics-limited-pilot-ui',upgrade) for upgrade in (False,True)]
        self.assertEqual(set(before),set(after))
        changed={k for k in before if before[k]!=after[k]}
        expected={('MutatingWebhookConfiguration',None,NAME),('ValidatingWebhookConfiguration',None,NAME),('Job','monitoring',NAME+'-patch')}
        self.assertEqual(changed,expected)
        for kind in ('MutatingWebhookConfiguration','ValidatingWebhookConfiguration'):
            for entry in before[(kind,None,NAME)]['webhooks']:entry['failurePolicy']='Fail'
        args=before[('Job','monitoring',NAME+'-patch')]['spec']['template']['spec']['containers'][0]['args']
        args[args.index('--patch-failure-policy=Ignore')]='--patch-failure-policy=Fail'
        self.assertEqual(before,after)

    def test_registry_override_retirement_preserves_parent_and_child_renders(self):
        objects=build(ROOT/'clusters/local-metrics-limited-pilot-ui')
        parent=next(x for x in objects if x['kind']=='HelmRelease' and x['metadata']['name']=='bigbang')
        values=ordered_values(objects,parent)
        refs=[{'name':'private-registry'}]
        retained=yaml.safe_dump({name:{'values':{'global':{'imagePullSecrets':refs}}} for name in ('monitoring','grafana')})
        outer=[]
        for selected in (values+[retained],values):
            outer.append(render(helm(self.sources/'bigbang/chart','bigbang','bigbang',selected),parent['spec']['postRenderers'][0]['kustomize']))
        self.assertEqual(outer[0],outer[1])
        for name in ('monitoring','grafana'):
            hr=next(x for x in outer[1] if x['kind']=='HelmRelease' and x['metadata']['name']==name)
            child=child_values(outer[1],name)
            if name=='grafana':self.assertEqual(hr['spec']['values']['upstream']['admin'],{'existingSecret':'grafana-admin','passwordKey':'admin-password','userKey':'admin-user'})
            for upgrade in (False,True):
                with self.subTest(child=name,upgrade=upgrade):
                    args=('--api-versions','monitoring.coreos.com/v1','--api-versions','monitoring.coreos.com/v1alpha1')+(('--is-upgrade',) if upgrade else ())
                    before,after=[helm(self.sources/name/'chart',release_name(hr),'monitoring',v,args) for v in (child+[yaml.safe_dump({'global':{'imagePullSecrets':refs}})],child)]
                    self.assertEqual(before,after)
