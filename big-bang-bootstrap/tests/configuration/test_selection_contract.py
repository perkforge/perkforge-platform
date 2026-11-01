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

EXAMPLES = Path(__file__).resolve().parents[2]
from fixtures.selection import build, release_for, context, PREFIX
# Configuration tests explicitly consume the same context fixture as bootstrap CI.
KEYS = ("cluster", "environment", "profile")








class SelectionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.enrollment = Path(os.environ["ENROLLMENT_CHECKOUT"]).resolve()
        cls.app = Path(os.environ["TENANT_APP_CHECKOUT"]).resolve()

    def follow(self, parent, source, checkout):
        selected = context(parent)
        self.assertEqual(parent["spec"]["suspend"], checkout == self.enrollment or selected["cluster"] != "local")
        self.assertEqual(source["spec"]["suspend"], checkout == self.enrollment or selected["cluster"] != "local")
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
        # Test the optional enrolled chain explicitly without enabling the operator root.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('clusters', 'enrollments', 'configuration', 'providers', 'profiles'):
                shutil.copytree(EXAMPLES / name, root / name)
            recipe = root / 'clusters/local/kustomization.yaml'
            selected = yaml.safe_load(recipe.read_text())
            selected['resources'].append('../../enrollments/local')
            recipe.write_text(yaml.safe_dump(selected))
            if cluster != 'local':
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
        inventory = yaml.safe_load((EXAMPLES / "configuration/ansible/inventory.yaml").read_text())
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

    def test_identity_first_enrollment_gate_cannot_be_silently_flipped(self):
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


    def test_only_physical_local_template_and_explicit_inputs(self):
        self.assertEqual({p.name for p in (EXAMPLES / 'clusters').iterdir()}, {'local', 'local-headlamp', 'local-keycloak'})
        self.assertEqual({p.name for p in (EXAMPLES / 'profiles').iterdir()}, {'il2'})
        values = yaml.safe_load((EXAMPLES / 'clusters/local/values.yaml').read_text())
        for name in ('headlamp', 'keycloak'):
            self.assertEqual(values['addons'][name]['values']['routes']['inbound'][name]['hosts'],
                             [f'{name}.perkforge.home.arpa'])
        inventory = yaml.safe_load((EXAMPLES / 'configuration/ansible/inventory.yaml').read_text())
        defaults = inventory['all']['children']['bootstrap_clusters']['vars']
        self.assertEqual(defaults['target_kubeconfig'], '/UNCONFIGURED/kubeconfig')
        self.assertFalse(defaults['bootstrap_apply'])
        self.assertNotIn('flux_resource_profile', defaults)

    def test_new_profile_requires_explicit_selection_without_claiming_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('clusters', 'enrollments', 'configuration', 'providers', 'profiles'):
                shutil.copytree(EXAMPLES / name, root / name)
            shutil.copytree(root / 'profiles/il2', root / 'profiles/il5')
            path = root / 'clusters/local/kustomization.yaml'
            value = yaml.safe_load(path.read_text())
            value['resources'] = [x.replace('../../profiles/il2', '../../profiles/il5') for x in value['resources']]
            value['commonAnnotations'][PREFIX + 'profile'] = 'il5'
            path.write_text(yaml.safe_dump(value))
            objects = build(root / 'clusters/local')
            parent = next(o for o in objects if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'bigbang')
            self.assertEqual(context(parent)['profile'], 'il5')
            impact = next(o for o in objects if o['kind'] == 'ConfigMap' and o['metadata']['name'] == 'values-impact')
            # Structural reuse only: copied values still contain the original UI guardrails.
            settings = yaml.safe_load(impact['data']['values.yaml'])['addons']['headlamp']['values']['upstream']
            self.assertFalse(settings['clusterRoleBinding']['create'])
            self.assertFalse(settings['config']['unsafeUseServiceAccountToken'])
