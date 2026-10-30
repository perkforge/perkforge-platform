"""Offline release refusal and paused seed rendering; no Kubernetes calls."""
import os,json,subprocess,tempfile,unittest
from pathlib import Path
import yaml
from fixtures.selection import EXAMPLES,context

class ReleaseSeedTests(unittest.TestCase):
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
