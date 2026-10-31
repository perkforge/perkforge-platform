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
        copies={'prepare.yml':'pxe/ansible/prepare.yml','preparation.md':'pxe/ansible/README.md',
            'rhel10.ks.j2':'pxe/kickstart/rhel10.ks.j2','redesign.md':'infrastructure/PROVISIONING-REDESIGN.md',
            'readiness.md':'infrastructure/TOMORROW-READINESS.md','vendor-guidance.md':'infrastructure/RHEL-PROVISIONING-GUIDANCE.md',
            'handoff.md':'pxe/pilot/HANDOFF.md'}
        output=ROOT/'public/sources'
        self.assertEqual({p.name for p in output.iterdir()},set(copies))
        for name,source in copies.items():
            self.assertEqual(hashlib.sha256((output/name).read_bytes()).digest(),hashlib.sha256((REPO/source).read_bytes()).digest())
        page=HTML();page.feed((ROOT/'public/runbook.html').read_text())
        for link in page.links:
            if link.startswith('sources/'):self.assertTrue((ROOT/'public'/link).is_file(),link)

    def test_models_keep_observed_and_planned_separate_without_private_identifiers(self):
        text='\n'.join((ROOT/name).read_text() for name in ['model.c4','views.c4','public/runbook.html'])
        self.assertIn('OBSERVED pilot checkpoint',text)
        self.assertIn('PLANNED ordered operations',text)
        self.assertIn('credential mode undecided',text)
        self.assertIn('not a packet trace',text)
        self.assertNotRegex(text,r'192\.168\.|/home/corey|(?:[0-9a-f]{2}:){5}[0-9a-f]{2}|SHA256:[A-Za-z0-9+/]{20}')
