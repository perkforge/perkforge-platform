import contextlib
import importlib.util
import io
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "local-lab/scripts/run-tenant-security-suite.py"
spec = importlib.util.spec_from_file_location("tenant_security_suite", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TenantSecuritySuiteTests(unittest.TestCase):
    def test_default_plan_is_non_mutating_and_has_core_suites(self):
        self.assertEqual(module.DEFAULT_SUITES, ("rbac", "admission", "quota", "network"))
        self.assertFalse(module.SUITES["rbac"][1])
        self.assertTrue(module.SUITES["network"][1])

    def test_default_plan_never_invokes_verifiers_or_writes_evidence(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
                module.sys, "argv", [str(SCRIPT), "--output-root", directory]), \
                patch.object(module.subprocess, "run") as run:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(module.main(), 0)
            run.assert_not_called()
            self.assertEqual(list(Path(directory).iterdir()), [])
            self.assertIn("Plan only", output.getvalue())

    def test_observability_is_available_but_separate(self):
        self.assertIn("observability", module.SUITES)
        self.assertNotIn("observability", module.DEFAULT_SUITES)

    def test_build_command_only_applies_live_checks_when_requested(self):
        with tempfile.TemporaryDirectory() as directory:
            base = module.build_command("network", False, "kubectl", "config", "ctx", Path(directory))
            live = module.build_command("network", True, "kubectl", "config", "ctx", Path(directory))
        self.assertNotIn("--apply", base)
        self.assertIn("--apply", live)
        self.assertIn("--context", live)
        rbac = module.build_command("rbac", True, "kubectl", "config", None, Path("out"))
        self.assertNotIn("--apply", rbac)

    def test_summary_counts_statuses_and_links_evidence_dirs(self):
        started = datetime(2026, 10, 26, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            results = [
                {"suite": "rbac", "status": "passed", "exitCode": 0, "evidenceDirectory": "rbac"},
                {"suite": "quota", "status": "failed", "exitCode": 1, "evidenceDirectory": "quota"},
                {"suite": "network", "status": "error", "exitCode": 2, "evidenceDirectory": "network"},
            ]
            json_path, markdown_path = module.write_summary(
                run_dir, started, started, True, "rancher-local", results)
            data = json.loads(json_path.read_text())
            self.assertEqual(data["summary"], {"total": 3, "passed": 1, "failed": 1, "errors": 1})
            self.assertEqual(data["mode"], "live")
            self.assertIn("`network` | error | 2", markdown_path.read_text())
            self.assertIn("not prove browser SSO", data["limitations"][1])


if __name__ == "__main__":
    unittest.main()
