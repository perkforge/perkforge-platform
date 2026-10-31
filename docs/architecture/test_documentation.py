"""Documentation contracts only; no server, browser, npm fetch or node connection."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest

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

    def test_current_allowlisted_sources_are_copied_without_recursion(self):
        copies={'prepare.yml': 'pxe/pilot/prepare.yml',
         'inputs.example.yml': 'pxe/pilot/inputs.example.yml',
         'activate.yml': 'pxe/pilot/activate.yml',
         'activation-placement.yml': 'pxe/pilot/activation-placement.yml',
         'verify-activation-copies.yml': 'pxe/pilot/verify-activation-copies.yml',
         'verify-pilot-identity.yml': 'pxe/pilot/verify-pilot-identity.yml',
         'shutdown.yml': 'pxe/pilot/shutdown.yml',
         'shutdown-tasks.yml': 'pxe/pilot/shutdown-tasks.yml',
         'dnsmasq.conf.j2': 'pxe/pilot/templates/dnsmasq.conf.j2',
         'grub.cfg.j2': 'pxe/pilot/templates/grub.cfg.j2',
         'nginx.conf.j2': 'pxe/pilot/templates/nginx.conf.j2',
         'ingress.nft.j2': 'pxe/pilot/templates/ingress.nft.j2',
         'stage-media.sh': 'pxe/pilot/stage-media.sh',
         'harden-ssh.sh': 'pxe/pilot/history/console/harden-ssh.sh'}
        output=ROOT/'public/sources'
        self.assertEqual({p.name for p in output.iterdir()},set(copies))
        for name,source in copies.items():
            self.assertEqual(hashlib.sha256((output/name).read_bytes()).digest(),hashlib.sha256((REPO/source).read_bytes()).digest())
        page=HTML();page.feed((ROOT/'public/runbook.html').read_text())
        for link in page.links:
            if link.startswith('sources/'):self.assertTrue((ROOT/'public'/link).is_file(),link)

    def test_architecture_has_repeat_process_without_session_or_proposal_views(self):
        model=(ROOT/'model.c4').read_text()
        views=(ROOT/'views.c4').read_text()
        page=(ROOT/'public/runbook.html').read_text()
        text='\n'.join([model,views,page])
        for view in ['index','workstation_detail','node_detail','operations','boot_protocol',
                     'installation','security_handoff','service_lifecycle','platform_detail']:
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
        self.assertIn('candidate deliberately aborts',page)
        self.assertIn('HANDOFF.md',page)
        self.assertIn('EXECUTION-JOURNAL.md',page)
        self.assertNotRegex(text,r'192\.168\.|/home/corey|(?:[0-9a-f]{2}:){5}[0-9a-f]{2}|SHA256:[A-Za-z0-9+/]{20}')
