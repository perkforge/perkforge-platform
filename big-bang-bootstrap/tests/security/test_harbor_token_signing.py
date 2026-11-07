"""Pinned native token parser; synthetic keys, no real credentials or API."""
import os
import copy
from pathlib import Path
import shutil
import subprocess
import unittest
import yaml
from fixtures.render_helpers import build, helm, ordered_values, child_values, release_name
from security.test_harbor_activation import named, indexed, postrender

ROOT = Path(__file__).resolve().parents[2]
SIGNER = 'harbor-token-signing-pkcs1-v1'


class HarborTokenSigning(unittest.TestCase):
    def test_native_pkcs1_parser_and_same_key_identity(self):
        if not shutil.which('go'):
            if os.environ.get('REQUIRE_NATIVE_HARBOR_SIGNING') == '1':
                self.fail('Go is required for the explicitly requested native signing check')
            self.skipTest('Go unavailable; native token signing was not tested')
        fixture = Path(__file__).resolve().parents[1] / 'fixtures/harbor-token-signing'
        # Prefetch the pinned public module explicitly. Discovery cannot download.
        result = subprocess.run(['go', 'test', '-mod=readonly', '-count=1', '-v', '.'],
                                cwd=fixture, text=True, capture_output=True, timeout=180,
                                env={**os.environ, 'GOPROXY':'off', 'GOSUMDB':'off',
                                     'GOTOOLCHAIN':'local', 'GOWORK':'off'})
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('--- PASS: TestHarborTokenSigningEncoding', result.stdout)


class HarborSigningSelection(unittest.TestCase):
    def render(self, objects):
        sources=Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        parent=named(objects,'HelmRelease','bigbang')
        outer=postrender(helm(sources/'bigbang/chart','bigbang','bigbang',ordered_values(objects,parent)),
                         parent['spec']['postRenderers'])
        release=named(outer,'HelmRelease','harbor')
        final=postrender(helm(sources/'harbor/chart',release_name(release),'harbor',child_values(outer,'harbor')),
                         release['spec']['postRenderers'])
        return outer,final

    def test_reference_change_preserves_every_other_effective_field(self):
        current=build(ROOT/'clusters/local-harbor-app')
        before=copy.deepcopy(current)
        config=named(before,'ConfigMap','values-harbor-candidate')['data']
        old=yaml.safe_load(config['values.yaml'])
        self.assertEqual(old['addons']['harbor']['values']['upstream']['core']['secretName'],SIGNER)
        old['addons']['harbor']['values']['upstream']['core']['secretName']='harbor-token-signing'
        config['values.yaml']=yaml.safe_dump(old)
        # Optional exact released checkout additionally proves newer main did not
        # introduce unrelated runtime changes. It is never fetched by discovery.
        baseline=os.environ.get('HARBOR_SIGNING_BASELINE_CHECKOUT')
        if baseline:
            released=build(Path(baseline)/'big-bang-bootstrap/clusters/local-harbor-app')
            data=named(released,'ConfigMap','values-harbor-candidate')['data']
            data['values.yaml']=yaml.safe_dump(yaml.safe_load(data['values.yaml']))
            self.assertEqual(indexed(released),indexed(before))
            before=released
        prior_outer,prior_final=self.render(before)
        outer,final=self.render(current)
        overlays=named(prior_outer,'Secret','bigbang-harbor-values')['stringData']
        values=yaml.safe_load(overlays['overlays'])
        values['upstream']['core']['secretName']=SIGNER
        self.assertEqual(values,yaml.safe_load(named(outer,'Secret','bigbang-harbor-values')['stringData']['overlays']))
        overlays['overlays']=named(outer,'Secret','bigbang-harbor-values')['stringData']['overlays']
        prior_hr=named(prior_outer,'HelmRelease','harbor')
        prior_hr['metadata']['annotations']['checksum/bigbang-values']=named(outer,'HelmRelease','harbor')['metadata']['annotations']['checksum/bigbang-values']
        self.assertEqual(indexed(prior_outer),indexed(outer))
        old_core=named(prior_final,'Deployment','harbor-core')['spec']['template']['spec']
        volume=next(v for v in old_core['volumes'] if v['name']=='token-service-private-key')
        self.assertEqual(volume['secret']['secretName'],'harbor-token-signing')
        volume['secret']['secretName']=SIGNER
        self.assertEqual(indexed(prior_final),indexed(final))
        consumers=[]
        for obj in final:
            if obj['kind']!='Deployment': continue
            pod=obj['spec']['template']['spec']
            for volume in pod.get('volumes',[]):
                if volume.get('secret',{}).get('secretName')==SIGNER:
                    consumers.append(obj['metadata']['name'])
                    mounts=[m for c in pod['containers'] for m in c.get('volumeMounts',[]) if m['name']==volume['name']]
                    self.assertEqual(mounts,[{'name':'token-service-private-key','mountPath':'/etc/core/private_key.pem','subPath':'tls.key'}])
        self.assertEqual(consumers,['harbor-core'])
        registry=yaml.safe_load(named(final,'ConfigMap','harbor-registry')['data']['config.yml'])
        self.assertEqual(registry['auth'],{'htpasswd':{'realm':'harbor-registry-basic-realm','path':'/etc/registry/passwd'}})
