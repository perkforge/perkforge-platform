import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "local-lab/scripts/manage-security-findings.py"
spec = importlib.util.spec_from_file_location("security_findings", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SecurityFindingsRegisterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.candidate_path = self.root / "candidate-findings.json"
        self.candidate_path.write_text(json.dumps({
            "schemaVersion": "perkforge.security-findings/v1alpha1",
            "findings": [{
                "findingId": "PF-RBAC-ALPHA-CAN-READ-BRAVO",
                "title": "Cross-tenant read unexpectedly allowed",
                "status": "untriaged",
                "testSuite": "rbac",
                "testId": "alpha-cannot-read-bravo",
                "potentialControlIds": ["AC-3", "AC-6"],
                "evidenceArtifact": "rbac/report.json",
                "expected": "deny",
                "actual": "allow",
                "target": {"tenant": "tenant-alpha"},
            }],
        }))
        self.register = module.empty_register()

    def tearDown(self):
        self.temp.cleanup()

    def import_one(self):
        imported = module.import_candidates(self.register, self.candidate_path)
        self.assertEqual(len(imported), 1)
        return imported[0]

    def test_import_is_idempotent_and_preserves_source_as_candidate(self):
        finding_id = self.import_one()
        self.assertEqual(module.import_candidates(self.register, self.candidate_path), [])
        record = self.register["findings"][0]
        self.assertEqual(record["findingId"], finding_id)
        self.assertEqual(record["status"], "candidate")
        self.assertEqual(record["risk"]["status"], "unassessed")
        self.assertEqual(record["sourceCandidate"]["actual"], "allow")
        self.assertEqual(record["history"][0]["actor"], "candidate-import")

    def test_only_untriaged_candidates_are_imported(self):
        payload = json.loads(self.candidate_path.read_text())
        payload["findings"][0]["status"] = "confirmed"
        self.candidate_path.write_text(json.dumps(payload))
        with self.assertRaisesRegex(module.RegisterError, "only untriaged"):
            module.import_candidates(self.register, self.candidate_path)

    def test_transition_requires_actor_rationale_and_valid_state(self):
        finding_id = self.import_one()
        with self.assertRaisesRegex(module.RegisterError, "actor and rationale"):
            module.transition(self.register, finding_id, "triage", actor=" ", rationale="review")
        with self.assertRaisesRegex(module.RegisterError, "not allowed"):
            module.transition(self.register, finding_id, "closed", actor="reviewer", rationale="done")
        module.transition(self.register, finding_id, "triage", actor="reviewer",
                          rationale="Reviewing source evidence")
        self.assertEqual(self.register["findings"][0]["history"][-1]["from"], "candidate")

    def test_risk_assessment_requires_both_rationales(self):
        finding_id = self.import_one()
        module.transition(self.register, finding_id, "triage", actor="reviewer", rationale="review")
        module.transition(self.register, finding_id, "confirmed", actor="reviewer", rationale="reproduced")
        with self.assertRaisesRegex(module.RegisterError, "impact rationale"):
            module.transition(self.register, finding_id, "risk-assessed", actor="assessor",
                              rationale="assessed", likelihood_rationale="repeatable")
        module.transition(self.register, finding_id, "risk-assessed", actor="assessor",
                          rationale="assessed", impact_rationale="cross-tenant disclosure",
                          likelihood_rationale="reproduced in verification",
                          residual_risk_rationale="cross-tenant reads remain possible until fix")
        risk = self.register["findings"][0]["risk"]
        self.assertEqual(risk["status"], "assessed")
        self.assertEqual(risk["decision"], "pending")
        self.assertEqual(self.register["findings"][0]["history"][-1]["riskAssessment"]["impactRationale"],
                         "cross-tenant disclosure")

    def test_risk_acceptance_requires_authority_and_future_expiry(self):
        finding_id = self.import_one()
        module.transition(self.register, finding_id, "triage", actor="reviewer", rationale="review")
        module.transition(self.register, finding_id, "confirmed", actor="reviewer", rationale="confirmed")
        module.transition(self.register, finding_id, "risk-assessed", actor="assessor",
                          rationale="assessed", impact_rationale="impact",
                          likelihood_rationale="likelihood",
                          residual_risk_rationale="risk remains pending corrective work")
        with self.assertRaisesRegex(module.RegisterError, "authorized decision maker"):
            module.transition(self.register, finding_id, "accepted", actor="assessor",
                              rationale="accept", accepted_until="2099-01-01")
        tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
        module.transition(self.register, finding_id, "accepted", actor="reviewer",
                          rationale="authorized temporary acceptance",
                          decision_authority="system owner", accepted_until=tomorrow)
        self.assertEqual(self.register["findings"][0]["risk"]["decision"], "accept")
        self.assertEqual(self.register["findings"][0]["history"][-1]["riskAcceptance"]["decisionAuthority"],
                         "system owner")

    def test_closure_requires_passing_retest_and_evidence_and_can_reopen(self):
        finding_id = self.import_one()
        module.transition(self.register, finding_id, "triage", actor="reviewer", rationale="review")
        module.transition(self.register, finding_id, "confirmed", actor="reviewer", rationale="confirmed")
        module.transition(self.register, finding_id, "risk-assessed", actor="assessor",
                          rationale="assessed", impact_rationale="impact",
                          likelihood_rationale="likelihood",
                          residual_risk_rationale="risk remains pending corrective work")
        due = (dt.date.today() + dt.timedelta(days=30)).isoformat()
        module.transition(self.register, finding_id, "remediation-planned", actor="owner",
                          rationale="corrective work planned", owner="platform-team", due_date=due)
        module.transition(self.register, finding_id, "in-progress", actor="owner", rationale="started")
        module.transition(self.register, finding_id, "retest", actor="owner", rationale="change deployed",
                          evidence="change/commit-123")
        with self.assertRaisesRegex(module.RegisterError, "passing retest"):
            module.transition(self.register, finding_id, "closed", actor="reviewer",
                              rationale="attempt close", evidence="retest/report.json",
                              retest_result="fail")
        module.transition(self.register, finding_id, "closed", actor="reviewer",
                          rationale="negative retest passed", evidence="retest/report.json",
                          retest_result="pass")
        self.assertEqual(self.register["findings"][0]["status"], "closed")
        module.transition(self.register, finding_id, "in-progress", actor="reviewer",
                          rationale="regression observed", evidence="retest/regression.json",
                          retest_result="fail")
        self.assertEqual(self.register["findings"][0]["status"], "in-progress")
        self.assertTrue(self.register["findings"][0]["history"][-1]["retest"]["reopenedAfterClosure"])

    def test_register_write_uses_private_file_mode(self):
        path = self.root / "private" / "register.json"
        module.write_register(path, self.register)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    @unittest.skipUnless(hasattr(__import__("os"), "chmod"), "POSIX permissions are required")
    def test_register_refuses_group_or_world_readable_file(self):
        path = self.root / "loose-register.json"
        path.write_text(json.dumps(self.register))
        path.chmod(0o644)
        with self.assertRaisesRegex(module.RegisterError, "permissions are too broad"):
            module.load_register(path)


if __name__ == "__main__":
    unittest.main()
