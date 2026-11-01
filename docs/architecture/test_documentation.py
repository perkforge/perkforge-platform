"""Documentation contracts only; no server, browser, npm fetch or node connection."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest
import tempfile
import subprocess
import yaml

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]

class HTML(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=set();self.links=[]
    def handle_starttag(self,tag,attrs):
        data=dict(attrs)
        if 'id' in data:self.ids.add(data['id'])
        if tag=='a' and 'href' in data:self.links.append(data['href'])

class Documentation(unittest.TestCase):
    def test_numbered_operations_link_to_real_runbook_sections(self):
        views=(ROOT/'views.c4').read_text()
        block=views.split('dynamic view operations {',1)[1].split('\n  dynamic view',1)[0]
        self.assertEqual(re.findall(r"-> [A-Za-z0-9_.]+ '([1-7])\.",block),list('1234567'))
        page=HTML();page.feed((ROOT/'public/runbook.html').read_text())
        anchors=set(re.findall(r'/runbook\.html#([a-z0-9-]+)',views+(ROOT/'model.c4').read_text()))
        self.assertTrue(anchors <= page.ids,anchors-page.ids)
        self.assertTrue({'prepare','approve','boot','install','firstboot','verify','cleanup'} <= anchors)

    def test_short_indexes_match_operation_names_and_link_to_details(self):
        views=(ROOT/'views.c4').read_text().split('dynamic view operations {',1)[1].split('\n  dynamic view',1)[0]
        names=re.findall(r"-> [A-Za-z0-9_.]+ '[1-7]\. ([^']+)'",views)
        readme=(ROOT/'README.md').read_text().split('## Step index',1)[1].split('\n## Navigate',1)[0]
        entries=re.findall(r'^([1-7])\. \[([^]]+)\]\(([^)]+)\) — ([^\n]+)$',readme,re.M)
        self.assertEqual([e[0] for e in entries],list('1234567'))
        self.assertEqual([e[1] for e in entries],names)
        for _,_,link,description in entries:
            path=link.split('#')[0]
            self.assertTrue((ROOT/path).is_file(),link)
            self.assertLessEqual(len(description.split()),10)
        page=(ROOT/'public/runbook.html').read_text()
        nav=page.split('<nav aria-label="Step index">',1)[1].split('</nav>',1)[0]
        linked=re.findall(r'<li><a href="#([^"]+)">([^<]+)</a> — ([^<]+)</li>',nav)
        self.assertEqual([entry[1] for entry in linked],names)
        self.assertEqual([entry[2] for entry in linked],[entry[3] for entry in entries])
        ids=HTML();ids.feed(page)
        self.assertTrue({entry[0] for entry in linked} <= ids.ids)

    def test_each_ordered_stage_explains_roles_and_evidence_gate(self):
        page=(ROOT/'public/runbook.html').read_text()
        views=(ROOT/'views.c4').read_text().split('dynamic view operations {',1)[1].split('\n  dynamic view',1)[0]
        for stage in ['prepare','approve','boot','install','firstboot','verify','cleanup']:
            section=page.split('<section id="'+stage+'">',1)[1].split('</section>',1)[0]
            for label in ['Operator','Automation','Evidence / stop']:
                self.assertIn('<dt>'+label+'</dt>',section)
            note=next(line for line in views.splitlines() if 'notes ' in line and '/runbook.html#'+stage+')' in line)
            for label in ['Operator:','Automation:','Evidence / stop:']:
                self.assertIn(label,note)

    def test_viewer_is_pinned_loopback_only_and_has_no_provisioning_command(self):
        package=json.loads((ROOT/'package.json').read_text())
        lock=json.loads((ROOT/'package-lock.json').read_text())
        self.assertEqual(package['devDependencies'],{'likec4':'1.60.0'})
        self.assertEqual(lock['packages']['node_modules/likec4']['version'],'1.60.0')
        self.assertEqual(package['engines'],lock['packages']['']['engines'])
        self.assertIn('--listen 127.0.0.1',package['scripts']['start'])
        self.assertNotIn('ansible',str(package['scripts']))
        self.assertNotIn('pilot.sh',str(package['scripts']))

    def test_initial_app_instructions_follow_the_declarative_stages(self):
        runbook=(REPO/'big-bang-bootstrap/configuration/ansible/README.md').read_text()
        step=next(line for line in runbook.splitlines() if line.startswith('6. Initial app access:'))
        self.assertIn('default `clusters/local` root selects OpenBao only',step)
        self.assertIn('after OpenBao acceptance, `clusters/local-headlamp`'.lower(),step.lower())
        self.assertIn('after Headlamp acceptance, `clusters/local-keycloak`'.lower(),step.lower())
        self.assertIn('same immutable release',step)
        self.assertNotIn('selects OpenBao and Headlamp',step)

    def test_openbao_observed_flow_links_real_one_time_procedure(self):
        views=(ROOT/'views.c4').read_text().split('dynamic view openbao_initial_admin {',1)[1].split('\n  dynamic view',1)[0]
        for term in ['observed v0.13.0','openbao-initialize.yaml','3/2','custody','stdin','close port-forward']:
            self.assertIn(term,views)
        play=(REPO/'big-bang-bootstrap/configuration/ansible/openbao-initialize.yaml').read_text()
        for term in ['openbao_initialize_apply: false','no_log: true','127.0.0.1:18200','secret_threshold','Refuse initialization of existing data']:
            self.assertIn(term,play)

    def test_current_allowlisted_sources_are_copied_without_recursion(self):
        copies={
         'openbao-initialize.yaml': 'big-bang-bootstrap/configuration/ansible/openbao-initialize.yaml',
         'longhorn-storage-smoke.yaml': 'big-bang-bootstrap/configuration/ansible/longhorn-storage-smoke.yaml',
         'longhorn-smoke-stage.yaml': 'big-bang-bootstrap/configuration/ansible/longhorn-smoke-stage.yaml',
         'verify-longhorn-smoke.py': 'big-bang-bootstrap/configuration/ansible/files/verify-longhorn-smoke.py',
         'longhorn-smoke-pod.yaml.j2': 'big-bang-bootstrap/configuration/ansible/fixtures/longhorn-smoke-pod.yaml.j2',
         'longhorn-smoke-foundation.yaml.j2': 'big-bang-bootstrap/configuration/ansible/fixtures/longhorn-smoke-foundation.yaml.j2',
         'workload-smoke.yml': 'infrastructure/ansible/tests/workload-smoke.yml',
         'workload-smoke.yaml': 'infrastructure/ansible/tests/fixtures/workload-smoke.yaml',
         'prepare.yml': 'pxe/transport/prepare.yml',
         'inputs.example.yml': 'pxe/transport/inputs.example.yml',
         'activate.yml': 'pxe/transport/activate.yml',
         'activation-placement.yml': 'pxe/transport/activation-placement.yml',
         'verify-activation-copies.yml': 'pxe/transport/verify-activation-copies.yml',
         'verify-session-identity.yml': 'pxe/transport/verify-session-identity.yml',
         'shutdown.yml': 'pxe/transport/shutdown.yml',
         'shutdown-tasks.yml': 'pxe/transport/shutdown-tasks.yml',
         'dnsmasq.conf.j2': 'pxe/transport/templates/dnsmasq.conf.j2',
         'grub.cfg.j2': 'pxe/transport/templates/grub.cfg.j2',
         'nginx.conf.j2': 'pxe/transport/templates/nginx.conf.j2',
         'ingress.nft.j2': 'pxe/transport/templates/ingress.nft.j2',
         'stage-media.sh': 'pxe/transport/stage-media.sh',
         'harden-ssh.sh': 'pxe/transport/harden-ssh.sh',
         'access.sh': 'pxe/transport/access.sh',
         'workspace.yml': 'pxe/transport/workspace.yml',
         'workspace.inputs.example.yml': 'pxe/transport/workspace.inputs.example.yml',
         'provisioning.md': 'pxe/README.md',
         'preserve-session.yml': 'pxe/transport/preserve-session.yml',
         'workspace-session.sh.j2': 'pxe/transport/templates/workspace/session.sh.j2',
         'workspace-inputs.yml.j2': 'pxe/transport/templates/workspace/inputs.yml.j2',
         'workspace-manifest.yml.j2': 'pxe/transport/templates/workspace/activation-review.yml.j2',
         'workspace-readme.md.j2': 'pxe/transport/templates/workspace/README.md.j2'}
        temporary=tempfile.TemporaryDirectory(prefix='c4-source-links-')
        self.addCleanup(temporary.cleanup)
        output=Path(temporary.name)/'sources'
        subprocess.run(['node',str(ROOT/'scripts/prepare-sources.mjs'),str(output)],check=True,capture_output=True,text=True)
        self.assertEqual({p.name for p in output.iterdir()},set(copies))
        for name,source in copies.items():
            self.assertEqual(hashlib.sha256((output/name).read_bytes()).digest(),hashlib.sha256((REPO/source).read_bytes()).digest())
        page=HTML();page.feed((ROOT/'public/runbook.html').read_text())
        for link in page.links:
            if link.startswith('sources/'):self.assertTrue((output/link.removeprefix('sources/')).is_file(),link)

    def test_architecture_has_repeat_process_without_session_or_proposal_views(self):
        model=(ROOT/'model.c4').read_text()
        views=(ROOT/'views.c4').read_text()
        page=(ROOT/'public/runbook.html').read_text()
        text='\n'.join([model,views,page])
        for view in ['index','workstation_detail','node_detail','operations','boot_protocol',
                     'installation','security_handoff','service_lifecycle','platform_detail',
                     'workspace_detail','workspace_construction','topology','rke2_detail','storage_detail']:
            self.assertRegex(views,r'view '+view+r'\b')
        for obsolete in ['observed_pilot','worker_discovery','worker_interactive_review','discovery_recovery']:
            self.assertNotRegex(views,r'view '+obsolete+r'\b')
        self.assertNotIn('element planned',model)
        self.assertIn('not a packet trace',text)
        for requirement in ['600MiB','2GiB','Primary Boot Sequence','disk-first',
                            'Begin Installation','password-authenticated sudo','RuntimeMaxSec=infinity']:
            self.assertIn(requirement,text)
        for leaked_history in ['activation-output-', '10:41:44', '107ok', 'installation underway']:
            self.assertNotIn(leaked_history,text)
        self.assertIn('sources/provisioning.md',page)
        self.assertNotRegex(text,r'/home/corey|PRIVATE KEY-----|ssh-ed25519 [A-Za-z0-9+/]{30,}|SHA256:[A-Za-z0-9+/]{20}')

    def test_workspace_recipe_links_construction_to_artifact_ownership(self):
        page=(ROOT/'public/runbook.html').read_text()
        section=page.split('<section id="workspace">',1)[1].split('</section>',1)[0]
        for artifact in ['discovery/', 'inputs.yml', 'activation-review.yml',
                         'session.sh', 'access/', 'handoff-&lt;unique&gt;',
                         'known_hosts', 'summary.txt']:
            self.assertIn(artifact,section)
        for boundary in ['mode0700','mode0600','UNCONFIGURED',
                         'workspace.yml','fresh run',
                         'not served or watched']:
            self.assertIn(boundary,section)
        self.assertIn('href="#workspace"',page.split('<section id="prepare">',1)[1].split('</section>',1)[0])

    def test_public_topology_excludes_physical_identifiers(self):
        inventory=yaml.safe_load((REPO/'infrastructure/ansible/inventory/hosts.yml').read_text())['all']
        self.assertTrue(all(not group['hosts'] for group in inventory['children'].values()))
        text=''.join((ROOT/name).read_text() for name in ['model.c4','views.c4','public/runbook.html'])
        self.assertIn('view topology of local_network',text)
        for name in ['Workstation','control-1','worker-1','worker-2']:
            self.assertIn(name,text)
        self.assertNotRegex(text,r'\b192\.168\.[0-9]+\.[0-9]+\b')
        self.assertNotRegex(text,r'\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b')
        helper=(ROOT/'scripts/prepare-sources.mjs').read_text()
        self.assertNotIn('.topology.yml',helper)
        self.assertIn('/infrastructure/ansible/inventory/.topology.yml', (REPO/'.gitignore').read_text())
