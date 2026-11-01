"""Offline release refusal and paused seed rendering; no Kubernetes calls."""
import os,json,subprocess,tempfile,unittest,base64
from pathlib import Path
import yaml
from fixtures.selection import EXAMPLES,context

class ReleaseSeedTests(unittest.TestCase):
    def test_active_storage_source_does_not_remove_initial_seed_or_execution_gates(self):
        inventory=yaml.safe_load((EXAMPLES/'configuration/ansible/inventory.yaml').read_text())['all']['children']['bootstrap_clusters']['vars']
        self.assertFalse(inventory['bootstrap_apply'])
        self.assertFalse(inventory['bootstrap_verify_release'])
        self.assertEqual(inventory['config_tag'],'UNCONFIGURED')
        seed=(EXAMPLES/'configuration/ansible/seed.yaml.j2').read_text()
        self.assertEqual(seed.count('suspend: true'),2)
        self.assertIn('tag: {{ config_tag | to_json }}',seed)
        self.assertNotIn('branch:',seed)
        root=yaml.safe_load((EXAMPLES/'clusters/local/kustomization.yaml').read_text())
        self.assertEqual(set(root['resources']),{'../../configuration/defaults','../../configuration/packages/longhorn','../../configuration/packages/rancher','../../configuration/packages/openbao','../../configuration/packages/headlamp','../../configuration/packages/keycloak','../../providers/rke2','../../profiles/il2','../../configuration/packages/bigbang'})

    def test_bootstrap_rejects_bad_tags_or_evidence_before_api_work(self):
        for tag in ("main", "v99.0.0"):
            with self.subTest(tag=tag), tempfile.TemporaryDirectory() as directory:
                args = {"bootstrap_verify_release": True, "config_tag": tag,
                        "config_release_evidence": str(EXAMPLES / "tests/fixtures/platform-v0.1.0.json")}
                result = subprocess.run(
                    ["ansible-playbook", "-i", str(EXAMPLES / "configuration/ansible/inventory.yaml"),
                     str(EXAMPLES / "configuration/ansible/bootstrap.yaml"), "--limit", "local", "-e", json.dumps(args)],
                    text=True, capture_output=True,
                    env={**os.environ, "ANSIBLE_LOCAL_TEMP": directory, "ANSIBLE_NOCOLOR": "1"})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Assertion failed", result.stdout)
                self.assertNotIn("Reject missing unpublished", result.stdout)
                self.assertNotIn("Check target cluster identity", result.stdout)

    def test_real_ansible_seed_preserves_selected_context(self):
        inventory = EXAMPLES / "configuration/ansible/inventory.yaml"
        hosts = yaml.safe_load(inventory.read_text())["all"]["children"]["bootstrap_clusters"]["hosts"]
        self.assertEqual(yaml.safe_load(inventory.read_text())["all"]["children"]["bootstrap_clusters"]["vars"]["config_tag"], "UNCONFIGURED")
        template = EXAMPLES / "configuration/ansible/seed.yaml.j2"
        for cluster, selected in hosts.items():
            with self.subTest(cluster=cluster), tempfile.TemporaryDirectory() as directory:
                argument = json.dumps({"msg": "{{ lookup('ansible.builtin.template', '" + str(template) + "') }}"})
                output = subprocess.check_output(
                    ["ansible", cluster, "-i", str(inventory), "-m", "ansible.builtin.debug", "-a", argument, "-e", "config_tag=v0.1.0"],
                    text=True, env={**os.environ, "ANSIBLE_LOCAL_TEMP": directory, "ANSIBLE_NOCOLOR": "1"},
                )
                response, _ = json.JSONDecoder().raw_decode(output[output.index("{"):])
                documents = list(yaml.safe_load_all(response["msg"]))
                root = next(obj for obj in documents if obj["kind"] == "Kustomization")
                self.assertEqual(context(root), {"cluster": cluster,
                                                "environment": selected["deployment_environment"],
                                                "profile": selected["impact_profile"]})
                self.assertEqual(root["spec"]["path"], selected["gitops_path"])
                source = next(obj for obj in documents if obj["kind"] == "GitRepository")
                self.assertEqual(source["spec"]["ref"], {"tag": "v0.1.0"})
                self.assertTrue(root["spec"]["suspend"])


class ReleasedContextTests(unittest.TestCase):
    def test_current_contract_accepts_matching_context_and_rejects_missing_or_wrong_keys(self):
        task = yaml.safe_load((EXAMPLES / 'configuration/ansible/verify-release.yaml').read_text())[-1]
        current = {'platform.perkforge.io/'+key: value for key,value in
                   [('cluster','local'),('environment','local'),('profile','il2')]}
        for annotations, expected in [(current,0),({},2),({**current,'platform.perkforge.io/environment':'wrong'},2)]:
            with self.subTest(annotations=annotations), tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                encoded=base64.b64encode(yaml.safe_dump({'commonAnnotations':annotations}).encode()).decode()
                play=root/'fixture.yaml';play.write_text(yaml.safe_dump([{'hosts':'local','connection':'local','gather_facts':False,
                    'vars':{'deployment_environment':'local','impact_profile':'il2','released_entrypoint':{'stdout':encoded}},'tasks':[task]}]))
                result=subprocess.run(['ansible-playbook','-i','local,',str(play)],capture_output=True,text=True,timeout=20,
                    env={**os.environ,'ANSIBLE_LOCAL_TEMP':directory+'/local','ANSIBLE_REMOTE_TEMP':directory+'/remote'})
                self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
                if expected:self.assertIn('Published release lacks or mismatches',result.stdout)
