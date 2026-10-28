"""Offline review-chain tests; never generate deployment configuration or call an API."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
PREFIX = "example.perkforge.io/"
KEYS = ("cluster", "environment", "profile")


def build(path):
    output = subprocess.check_output(
        ["kubectl", "kustomize", str(path)], text=True,
        env={**os.environ, "KUBECONFIG": "/dev/null"},
    )
    return [obj for obj in yaml.safe_load_all(output) if obj]


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
        self.assertTrue(parent["spec"]["suspend"])
        self.assertTrue(source["spec"]["suspend"])
        self.assertTrue(parent["spec"].get("serviceAccountName"))
        head = subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        self.assertEqual(source["spec"]["ref"]["commit"], head)
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
            self.assertTrue(child["spec"]["suspend"])
            self.assertTrue(child["spec"].get("serviceAccountName"))
        return objects

    def platform_selection(self, cluster):
        objects = build(EXAMPLES / "clusters" / cluster)
        parent = next(obj for obj in objects if obj["kind"] == "Kustomization")
        source = next(obj for obj in objects if obj["kind"] == "GitRepository"
                      and obj["metadata"]["name"] == parent["spec"]["sourceRef"]["name"])
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

    def test_cross_repository_environment_profile_and_target_mismatches_fail(self):
        parent, source = self.platform_selection("dev-il2")
        for key, wrong in (("environment", "local"), ("profile", "il5")):
            with self.subTest(key=key):
                bad = copy.deepcopy(parent)
                bad["metadata"]["annotations"][PREFIX + key] = wrong
                with self.assertRaises(AssertionError):
                    self.follow(bad, source, self.enrollment)
        bad = copy.deepcopy(parent)
        bad["spec"]["path"] = "./clusters/dev-il5"
        with self.assertRaises(AssertionError):
            self.follow(bad, source, self.enrollment)

    def test_unmatched_review_revision_fails(self):
        parent, source = self.platform_selection("dev-il2")
        bad = copy.deepcopy(source)
        bad["spec"]["ref"]["commit"] = "0" * 40
        with self.assertRaises(AssertionError):
            self.follow(parent, bad, self.enrollment)

    def test_real_ansible_seed_preserves_selected_context(self):
        inventory = EXAMPLES / "ansible/inventory.yaml"
        hosts = yaml.safe_load(inventory.read_text())["all"]["children"]["bootstrap_clusters"]["hosts"]
        template = EXAMPLES / "ansible/seed.yaml.j2"
        for cluster, selected in hosts.items():
            with self.subTest(cluster=cluster), tempfile.TemporaryDirectory() as directory:
                argument = json.dumps({"msg": "{{ lookup('ansible.builtin.template', '" + str(template) + "') }}"})
                output = subprocess.check_output(
                    ["ansible", cluster, "-i", str(inventory), "-m", "ansible.builtin.debug", "-a", argument],
                    text=True, env={**os.environ, "ANSIBLE_LOCAL_TEMP": directory, "ANSIBLE_NOCOLOR": "1"},
                )
                response, _ = json.JSONDecoder().raw_decode(output[output.index("{"):])
                documents = list(yaml.safe_load_all(response["msg"]))
                root = next(obj for obj in documents if obj["kind"] == "Kustomization")
                self.assertEqual(context(root), {"cluster": cluster,
                                                "environment": selected["deployment_environment"],
                                                "profile": selected["impact_profile"]})
                self.assertEqual(root["spec"]["path"], selected["gitops_path"])
                self.assertTrue(root["spec"]["suspend"])
