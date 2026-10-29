"""Offline review-chain tests; never generate deployment configuration or call an API."""
import copy
import json
import os
import re
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

EXAMPLES = Path(__file__).resolve().parents[1]
PREFIX = "example.perkforge.io/"
KEYS = ("cluster", "environment", "profile")


def build(path):
    output = subprocess.check_output(
        ["kubectl", "kustomize", str(path)], text=True,
        env={**os.environ, "KUBECONFIG": "/dev/null"},
    )
    return [obj for obj in yaml.safe_load_all(output) if obj]


def release_for(source, evidence):
    assert source['spec']['ref'] == {'tag': evidence['tag']}
    assert re.fullmatch(r'v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', evidence['tag'])
    assert re.fullmatch(r'[0-9a-f]{40}', evidence['resolvedCommit'])
    assert source['spec']['url'] == f"https://github.com/{evidence['repository']}.git"
    return evidence


def context(obj):
    annotations = obj["metadata"]["annotations"]
    return {key: annotations[PREFIX + key] for key in KEYS}


class SelectionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.enrollment = Path(os.environ["ENROLLMENT_CHECKOUT"]).resolve()
        cls.app = Path(os.environ["TENANT_APP_CHECKOUT"]).resolve()

    def follow(self, parent, source, checkout):
        selected = context(parent)
        self.assertEqual(parent["spec"]["suspend"], selected["cluster"] != "local")
        self.assertEqual(source["spec"]["suspend"], selected["cluster"] != "local")
        self.assertTrue(parent["spec"].get("serviceAccountName"))
        head = subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        evidence_root = EXAMPLES.parent if checkout == self.enrollment else self.enrollment
        name = "enrollment" if checkout == self.enrollment else "portal"
        evidence = json.loads((evidence_root / "release-evidence.json").read_text())["dependencies"][name]
        release_for(source, evidence)
        self.assertEqual(head, evidence["resolvedCommit"])
        resolved = subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", evidence["tag"] + "^{commit}"], text=True).strip()
        self.assertEqual(resolved, head)
        origin = subprocess.check_output(
            ["git", "-C", str(checkout), "remote", "get-url", "origin"], text=True).strip()
        self.assertEqual(source["spec"]["url"].removesuffix(".git"), origin.removesuffix(".git"))
        self.assertEqual(source["metadata"]["namespace"], parent["metadata"]["namespace"])
        relative = Path(parent["spec"]["path"])
        self.assertEqual(relative.name, selected["cluster"])
        target = (checkout / relative).resolve()
        self.assertTrue(target.is_relative_to(checkout))
        self.assertTrue((target / "kustomization.yaml").is_file())
        objects = build(target)
        reconcilers = [obj for obj in objects
                       if obj["kind"] in ("Kustomization", "HelmRelease")]
        self.assertTrue(reconcilers)
        for child in reconcilers:
            self.assertEqual(context(child), selected)
            self.assertEqual(child["spec"]["suspend"], selected["cluster"] != "local")
            self.assertTrue(child["spec"].get("serviceAccountName"))
        return objects

    def platform_selection(self, cluster):
        if cluster == 'local':
            objects = build(EXAMPLES / 'clusters/local')
        else:
            # Exercise documented copy/edit steps in temporary YAML, never ship a second target.
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for name in ('clusters', 'enrollments', 'shared', 'apps', 'providers', 'profiles', 'bigbang'):
                    shutil.copytree(EXAMPLES / name, root / name)
                for kind in ('clusters', 'enrollments'):
                    shutil.copytree(root / kind / 'local', root / kind / cluster)
                    for path in (root / kind / cluster).glob('*.yaml'):
                        value = path.read_text().replace('../../enrollments/local', '../../enrollments/' + cluster)
                        value = value.replace('./clusters/local', './clusters/' + cluster)
                        value = value.replace('cluster: local', 'cluster: ' + cluster).replace('environment: local', 'environment: dev')
                        value = value.replace('suspend: false', 'suspend: true')
                        path.write_text(value)
                objects = build(root / 'clusters' / cluster)
        parent = next(obj for obj in objects if obj['kind'] == 'Kustomization')
        source = next(obj for obj in objects if obj['kind'] == 'GitRepository'
                      and obj['metadata']['name'] == parent['spec']['sourceRef']['name'])
        return parent, source

    def test_inventory_profile_inputs_and_three_repository_contexts_match(self):
        inventory = yaml.safe_load((EXAMPLES / "ansible/inventory.yaml").read_text())
        hosts = inventory["all"]["children"]["bootstrap_clusters"]["hosts"]
        for cluster, values in hosts.items():
            with self.subTest(cluster=cluster):
                parent, source = self.platform_selection(cluster)
                selected = context(parent)
                self.assertEqual(selected, {"cluster": cluster,
                                            "environment": values["deployment_environment"],
                                            "profile": values["impact_profile"]})
                root = yaml.safe_load((EXAMPLES / "clusters" / cluster / "kustomization.yaml").read_text())
                self.assertIn("../../profiles/" + selected["profile"], root["resources"])
                self.assertTrue(values["gitops_path"].endswith("/clusters/" + cluster))
                enrolled = self.follow(parent, source, self.enrollment)
                child = next(obj for obj in enrolled if obj["kind"] == "Kustomization")
                app_source = next(obj for obj in enrolled if obj["kind"] == "GitRepository"
                                  and obj["metadata"]["name"] == child["spec"]["sourceRef"]["name"])
                app = self.follow(child, app_source, self.app)
                self.assertEqual({obj["kind"] for obj in app}, {"ConfigMap", "HelmRelease"})
                app_root = self.app / child["spec"]["path"] / "kustomization.yaml"
                resources = yaml.safe_load(app_root.read_text())["resources"]
                self.assertIn("../../environments/" + selected["environment"], resources)
                self.assertIn("../../profiles/" + selected["profile"], resources)

    def test_local_activation_and_dev_pause_cannot_be_silently_flipped(self):
        for cluster in ('local', 'dev'):
            parent, source = self.platform_selection(cluster)
            for which in ('parent', 'source'):
                bad_parent, bad_source = copy.deepcopy(parent), copy.deepcopy(source)
                target = bad_parent if which == 'parent' else bad_source
                target['spec']['suspend'] = not target['spec']['suspend']
                with self.subTest(cluster=cluster, which=which), self.assertRaises(AssertionError):
                    self.follow(bad_parent, bad_source, self.enrollment)

    def test_cross_repository_environment_profile_and_target_mismatches_fail(self):
        parent, source = self.platform_selection("dev")
        for key, wrong in (("environment", "local"), ("profile", "unselected-profile")):
            with self.subTest(key=key):
                bad = copy.deepcopy(parent)
                bad["metadata"]["annotations"][PREFIX + key] = wrong
                with self.assertRaises(AssertionError):
                    self.follow(bad, source, self.enrollment)
        bad = copy.deepcopy(parent)
        bad["spec"]["path"] = "./clusters/local"
        with self.assertRaises(AssertionError):
            self.follow(bad, source, self.enrollment)

    def test_unmatched_release_tag_or_commit_ref_fails(self):
        parent, source = self.platform_selection("dev")
        for ref in ({"tag": "v99.0.0"}, {"branch": "main"},
                    {"tag": "v0.1.1", "commit": "0" * 40}):
            bad = copy.deepcopy(source)
            bad["spec"]["ref"] = ref
            with self.assertRaises(AssertionError):
                self.follow(parent, bad, self.enrollment)

    def test_bootstrap_rejects_bad_tags_or_evidence_before_api_work(self):
        for tag in ("main", "v99.0.0"):
            with self.subTest(tag=tag), tempfile.TemporaryDirectory() as directory:
                args = {"bootstrap_verify_release": True, "config_tag": tag,
                        "config_release_evidence": str(EXAMPLES / "tests/fixtures/platform-v0.1.0.json")}
                result = subprocess.run(
                    ["ansible-playbook", "-i", str(EXAMPLES / "ansible/inventory.yaml"),
                     str(EXAMPLES / "ansible/bootstrap.yaml"), "--limit", "local", "-e", json.dumps(args)],
                    text=True, capture_output=True,
                    env={**os.environ, "ANSIBLE_LOCAL_TEMP": directory, "ANSIBLE_NOCOLOR": "1"})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Assertion failed", result.stdout)
                self.assertNotIn("Reject missing unpublished", result.stdout)
                self.assertNotIn("Check target cluster identity", result.stdout)

    def test_only_physical_local_template_and_explicit_inputs(self):
        self.assertEqual({p.name for p in (EXAMPLES / 'clusters').iterdir()}, {'local'})
        self.assertEqual({p.name for p in (EXAMPLES / 'profiles').iterdir()}, {'il2'})
        values = yaml.safe_load((EXAMPLES / 'clusters/local/values.yaml').read_text())
        for name in ('headlamp', 'keycloak'):
            self.assertEqual(values['addons'][name]['values']['routes']['inbound'][name]['hosts'],
                             [f'{name}-local-il2.example.test'])
        inventory = yaml.safe_load((EXAMPLES / 'ansible/inventory.yaml').read_text())
        defaults = inventory['all']['children']['bootstrap_clusters']['vars']
        self.assertEqual(defaults['target_kubeconfig'], '/UNCONFIGURED/kubeconfig')
        self.assertFalse(defaults['bootstrap_apply'])
        self.assertNotIn('flux_resource_profile', defaults)

    def test_new_profile_requires_explicit_selection_without_claiming_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('clusters', 'enrollments', 'shared', 'apps', 'providers', 'profiles', 'bigbang'):
                shutil.copytree(EXAMPLES / name, root / name)
            shutil.copytree(root / 'profiles/il2', root / 'profiles/il5')
            path = root / 'clusters/local/kustomization.yaml'
            value = yaml.safe_load(path.read_text())
            value['resources'] = [x.replace('../../profiles/il2', '../../profiles/il5') for x in value['resources']]
            value['commonAnnotations'][PREFIX + 'profile'] = 'il5'
            path.write_text(yaml.safe_dump(value))
            objects = build(root / 'clusters/local')
            parent = next(o for o in objects if o['kind'] == 'Kustomization')
            self.assertEqual(context(parent)['profile'], 'il5')
            impact = next(o for o in objects if o['kind'] == 'ConfigMap' and o['metadata']['name'] == 'values-impact')
            # Structural reuse only: copied values still contain the original UI guardrails.
            settings = yaml.safe_load(impact['data']['values.yaml'])['addons']['headlamp']['values']['upstream']
            self.assertFalse(settings['clusterRoleBinding']['create'])
            self.assertFalse(settings['config']['unsafeUseServiceAccountToken'])

    def test_real_ansible_seed_preserves_selected_context(self):
        inventory = EXAMPLES / "ansible/inventory.yaml"
        hosts = yaml.safe_load(inventory.read_text())["all"]["children"]["bootstrap_clusters"]["hosts"]
        self.assertEqual(yaml.safe_load(inventory.read_text())["all"]["children"]["bootstrap_clusters"]["vars"]["config_tag"], "UNCONFIGURED")
        template = EXAMPLES / "ansible/seed.yaml.j2"
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
