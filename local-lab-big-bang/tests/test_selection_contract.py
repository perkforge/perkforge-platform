"""Offline review-chain tests; never generate deployment configuration or call an API."""
import copy
import json
import os
import re
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
        self.assertTrue(parent["spec"]["suspend"])
        self.assertTrue(source["spec"]["suspend"])
        self.assertTrue(parent["spec"].get("serviceAccountName"))
        head = subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        evidence_root = EXAMPLES.parents[1] if checkout == self.enrollment else self.enrollment
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
                        "config_release_evidence": str(EXAMPLES.parent / "tests/fixtures/platform-v0.1.0.json")}
                result = subprocess.run(
                    ["ansible-playbook", "-i", str(EXAMPLES / "ansible/inventory.yaml"),
                     str(EXAMPLES / "ansible/bootstrap.yaml"), "--limit", "local", "-e", json.dumps(args)],
                    text=True, capture_output=True,
                    env={**os.environ, "ANSIBLE_LOCAL_TEMP": directory, "ANSIBLE_NOCOLOR": "1"})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Assertion failed", result.stdout)
                self.assertNotIn("Reject missing unpublished", result.stdout)
                self.assertNotIn("Check target cluster identity", result.stdout)

    def test_only_local_and_dev_targets_with_consistent_browser_contracts(self):
        self.assertEqual({p.name for p in (EXAMPLES / "clusters").iterdir()}, {"local", "dev"})
        self.assertEqual({p.name for p in (EXAMPLES / "profiles").iterdir()}, {"il2"})
        for cluster in ("local", "dev"):
            values = yaml.safe_load((EXAMPLES / "clusters" / cluster / "values.yaml").read_text())
            app = yaml.safe_load((self.app / "gitops/clusters" / cluster / "values.yaml").read_text())
            host = lambda name: f"{name}-{cluster}-il2.local-lab.test"
            for name in ("headlamp", "keycloak"):
                self.assertEqual(values["addons"][name]["values"]["routes"]["inbound"][name]["hosts"],
                                 [host(name)])
            hostname = yaml.safe_load(values["addons"]["keycloak"]["values"]["upstream"]["extraEnv"])[0]["value"]
            self.assertEqual(hostname, host("keycloak"))
            ingress = values["packages"]["openbao"]["values"]["server"]["ingress"]
            self.assertFalse(ingress["enabled"])
            self.assertEqual(ingress["hosts"][0]["host"], host("openbao"))
            self.assertEqual(app["portalOrigin"], "https://" + host("portal"))
            self.assertEqual(app["identity"]["issuer"], "https://" + host("keycloak") + "/realms/household")

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
