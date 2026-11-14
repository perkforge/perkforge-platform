"""Offline opt-in placement preservation against the pinned Big Bang checkout."""
from pathlib import Path
import os, shutil, subprocess, tempfile, unittest, yaml
ROOT=Path(__file__).resolve().parents[2]
class FluxPlacement(unittest.TestCase):
 def test_only_selected_controller_placement_changes(self):
  sources=os.environ.get('PREFLIGHT_SOURCES_DIR')
  if not sources:self.skipTest('PREFLIGHT_SOURCES_DIR required for exact pinned Flux fixture')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'base').mkdir();shutil.copytree(Path(sources)/'bigbang/base/flux',p/'base/flux')
   play=[{'hosts':'localhost','connection':'local','gather_facts':False,'vars':{'flux_checkout':d,'flux_kustomize_node_selector':{'node-role.kubernetes.io/control-plane':''}},'tasks':[{'ansible.builtin.include_tasks':str(ROOT/'configuration/ansible/prepare-flux.yaml')}]}]
   (p/'test.yaml').write_text(yaml.safe_dump(play));subprocess.run(['ansible-playbook','-i','localhost,',str(p/'test.yaml')],check=True,capture_output=True)
   def render(path):return {(o['kind'],o.get('metadata',{}).get('namespace'),o['metadata']['name']):o for o in yaml.safe_load_all(subprocess.check_output(['kubectl','kustomize',str(path)],text=True))}
   a=render(p/'base/flux');b=render(p/'base/perkforge-flux-placement');self.assertEqual(a.keys(),b.keys());k=('Deployment','flux-system','kustomize-controller')
   self.assertEqual([key for key in a if a[key]!=b[key]],[k]);a[k]['spec']['template']['spec']['nodeSelector']['node-role.kubernetes.io/control-plane']='';self.assertEqual(a,b)
   play[0]['vars']['flux_kustomize_node_selector']={};(p/'test.yaml').write_text(yaml.safe_dump(play));subprocess.run(['ansible-playbook','-i','localhost,',str(p/'test.yaml')],check=True,capture_output=True)
   self.assertEqual(render(p/'base/flux')[k]['spec']['template']['spec']['nodeSelector'],{'kubernetes.io/os':'linux'})
