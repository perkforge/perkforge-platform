"""Offline audience/disclosure contracts; no live APIs or publishing."""
import json
import importlib.util
import tempfile
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
META = json.loads((ROOT / "audiences.json").read_text())


class AudienceArchitecture(unittest.TestCase):
    def test_independent_roots_have_exact_declared_models_and_views(self):
        self.assertEqual(set(META["bundles"]), {"tenant", "security"})
        for audience, bundle in META["bundles"].items():
            source = REPO / bundle["sourceRoot"]
            self.assertNotEqual(ROOT, source)
            self.assertFalse(source.is_relative_to(ROOT))
            actual = {str(p.relative_to(source)) for p in source.rglob("*.c4")}
            self.assertEqual(actual, set(bundle["models"]))
            text = "\n".join((source / p).read_text() for p in bundle["models"])
            views = re.findall(r"(?:dynamic )?view ([a-z_]+) \{", text)
            self.assertEqual(set(views), set(bundle["views"]))
            self.assertEqual(len(views), len(set(views)))
            self.assertTrue(all(v.startswith(audience + "_") for v in views))
        # Operator validation cannot recursively absorb either audience.
        self.assertEqual({p.name for p in ROOT.glob("*.c4")}, {"model.c4", "views.c4"})

    def test_tenant_source_has_no_reviewer_or_operator_payload(self):
        source = REPO / META["bundles"]["tenant"]["sourceRoot"]
        text = (source / "model.c4").read_text()
        for marker in ["review_platform", "security_image_intake", "production_pki", "workstation_detail", "perkforge.home.arpa"]:
            self.assertNotIn(marker, text)
        for root in [source, REPO / META["bundles"]["security"]["sourceRoot"]]:
            self.assertFalse((root / "public").exists())
            for path in root.rglob("*"):
                self.assertFalse(path.is_symlink(), str(path))
                if path.is_file() and path.suffix in {".md", ".c4"}:
                    self.assertNotRegex(path.read_text(), r"/home/|PRIVATE KEY-----|192\.168\.\d+\.\d+|(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}")

    def test_build_runner_keeps_sources_assets_and_outputs_separate(self):
        code = (ROOT / "scripts/audience-models.mjs").read_text()
        self.assertIn("['tenant', 'security']", code)
        self.assertIn("../${audience}-architecture", code)
        self.assertIn("dist-${audience}", code)
        self.assertIn("rmSync(output, { recursive: true, force: true })", code)
        self.assertNotIn("--public", code)
        self.assertNotIn("publish", code)
        package = json.loads((ROOT / "package.json").read_text())
        self.assertIn("npm run validate:audiences", package["scripts"]["validate"])
        self.assertIn("npm run build:audiences", package["scripts"]["build"])
        for name in ["dist-tenant/", "dist-security/"]:
            self.assertIn(name, (ROOT / ".gitignore").read_text())

    def test_review_metadata_keeps_approval_and_evidence_limits(self):
        self.assertRegex(META["reviewedPlatformCommit"], r"^[0-9a-f]{40}$")
        self.assertEqual(META["reviewedAt"], "2026-11-09")
        self.assertIn("pending", META["disclosureApproval"])
        self.assertEqual(set(META["statusLegend"]), {"implemented", "planned", "unverified"})
        self.assertEqual(set(META["coordination"]), {21, 43, 44, 45, 77, 79, 80, 81})
        for audience in META["bundles"].values():
            readme = (REPO / audience["sourceRoot"] / "README.md").read_text()
            self.assertIn(META["reviewedPlatformCommit"], readme)
            self.assertIn(META["reviewedAt"], readme)
            self.assertIn("unverified", readme.lower())

    def test_model_source_links_are_pinned_and_resolve(self):
        expected = META["reviewedPlatformCommit"]
        count = 0
        for bundle in META["bundles"].values():
            text = (REPO / bundle["sourceRoot"] / "model.c4").read_text()
            for revision, path in re.findall(r"https://github.com/perkforge/perkforge-platform/blob/([^/]+)/([^\s']+)", text):
                self.assertEqual(revision, expected)
                self.assertTrue((REPO / path).is_file(), path)
                count += 1
        self.assertGreaterEqual(count, 5)

    def test_relative_document_links_resolve(self):
        files = [ROOT / "README.md"]
        for bundle in META["bundles"].values():
            files.extend((REPO / bundle["sourceRoot"]).glob("*.md"))
        for file in files:
            for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", file.read_text()):
                if re.match(r"(?:https?://|mailto:|#)", target):
                    continue
                path, _, fragment = target.partition("#")
                dest = file.parent / path
                self.assertTrue(dest.is_file(), f"{file}: {target}")
                if fragment and dest.suffix == ".md":
                    headings = re.findall(r"^#+ (.+)$", dest.read_text(), re.M)
                    slugs = [re.sub(r"[^a-z0-9_ -]", "", h.lower()).replace(" ", "-") for h in headings]
                    self.assertIn(fragment, slugs, f"{file}: {target}")

    def test_intake_remains_planned_and_harbor_scan_disabled(self):
        model = (REPO / "docs/security-architecture/model.c4").read_text()
        for view in ["security_image_intake", "security_chart_intake", "security_promotion"]:
            block = model.split("dynamic view " + view + " {", 1)[1].split("\n  }", 1)[0]
            self.assertIn("PLANNED", block)
        values = (REPO / "big-bang-bootstrap/configuration/packages/harbor/candidate-values.yaml").read_text()
        self.assertIn("trivy: {enabled: false}", values)
        readme = (REPO / "docs/security-architecture/README.md").read_text()
        for term in ["every copied runnable platform", "Chart.lock", "Controller-created", "Trivy defaults", "trusted producer", "stale/missing", "maintainers must decide"]:
            self.assertIn(term.lower(), readme.lower())

    def test_tenant_boundary_and_rationale_caveats_are_explicit(self):
        tenant = (REPO / "docs/tenant-architecture/README.md").read_text()
        security = (REPO / "docs/security-architecture/README.md").read_text()
        for term in ["namespace is not", "bypass", "replication is not backup", "planned", "unverified"]:
            self.assertIn(term.lower(), tenant.lower())
        for term in ["Keycloak", "Mattermost", "Self-hosting", "SaaS", "wildcard authority", "not an ATO", "server-enforced"]:
            if term == "not an ATO":
                self.assertIn("not a live\nassessment, an ATO", security)
            else:
                self.assertIn(term, security)

    def test_control_map_is_review_prompts_not_compliance_evidence(self):
        text = (REPO / "docs/security-architecture/controls.md").read_text()
        for family in ["AC-3", "AC-6", "IA-2", "IA-5", "SC-7", "SC-8", "RA-5", "SI-7", "CM-3", "AU-9", "CP-10"]:
            self.assertIn(family, text)
        for phrase in ["review prompts", "No claim", "runtime/assessment", "exception", "No live test"]:
            self.assertIn(phrase.lower(), text.lower())

    def test_generated_payload_verifier_rejects_hidden_models_and_assets(self):
        spec = importlib.util.spec_from_file_location("bundle_verifier", ROOT / "scripts/verify-audience-bundles.py")
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "index.html").write_text("local test")
            payload = output / "app.js"
            safe = " ".join(META["bundles"]["tenant"]["views"])
            payload.write_text(safe)
            self.assertEqual(verifier.verify_bundle(output, "tenant"), 2)
            for forbidden in ["security_context", "production_pki", "/home/", "-----BEGIN PRIVATE KEY-----"]:
                payload.write_text(safe + " " + forbidden)
                with self.assertRaises(ValueError):
                    verifier.verify_bundle(output, "tenant")
            payload.write_text(safe)
            (output / "runbook.html").write_text("operator content")
            with self.assertRaises(ValueError):
                verifier.verify_bundle(output, "tenant")
            (output / "runbook.html").unlink()
            (output / "sources").mkdir()
            (output / "sources" / "copied.txt").write_text("operator source")
            with self.assertRaises(ValueError):
                verifier.verify_bundle(output, "tenant")

    def test_ci_docs_disclose_pause_without_claiming_validation_ran(self):
        doc = (REPO / "docs/platform/ci.md").read_text()
        status = doc.split("## Retained selection design", 1)[0]
        for term in ["validation paused", "explicit false", "not", "until the owner explicitly", "does not change workflows"]:
            self.assertIn(term, status)
        for name in ["gitops-selection.yml", "configuration-release.yml"]:
            self.assertIn("if: ${{ false }}", (REPO / ".github/workflows" / name).read_text())


if __name__ == "__main__":
    unittest.main()
