from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_REVIEWER_RED_TEAM_GATE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reviewer_red_team_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReviewerRedTeamGateTests(unittest.TestCase):
    def test_gate_scores_dice_and_harbor_without_upload_claims(self) -> None:
        module = load_module()
        payload = module.build_gate()

        self.assertEqual(payload["schema"], "reviewer_red_team_gate_v2")
        self.assertEqual(payload["summary"]["packages_reviewed"], 14)
        self.assertEqual(payload["summary"]["ready_for_upload_count"], 0)
        self.assertEqual(payload["summary"]["argument_conformance_pass_count"], 0)
        self.assertEqual(payload["summary"]["closed_official_decision_count"], 1)
        self.assertEqual(payload["summary"]["argument_blocked_count"], 13)
        self.assertEqual(payload["summary"]["technical_conformance_lane_count"], 13)
        self.assertEqual(payload["summary"]["active_submission_candidate_count"], 3)
        self.assertEqual(payload["summary"]["active_candidate_gate_count"], 3)
        self.assertEqual(
            payload["summary"]["active_candidate_argument_blocked_count"],
            3,
        )
        self.assertEqual(
            payload["summary"]["unrepresented_active_conformance_lane_count"],
            0,
        )
        unhashed = {
            key: value
            for key, value in payload.items()
            if key != "reviewer_gate_sha256"
        }
        self.assertEqual(
            payload["reviewer_gate_sha256"],
            hashlib.sha256(
                json.dumps(unhashed, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        )
        gates = {row["package"]: row for row in payload["reviewer_gates"]}
        gates_by_lane = {
            row["conformance_lane_id"]: row
            for row in payload["reviewer_gates"]
            if row.get("conformance_lane_id")
        }
        self.assertIn("DICE", gates)
        self.assertIn("HarborSentinel", gates)
        self.assertFalse(gates["DICE"]["ready_for_upload"])
        self.assertFalse(gates["HarborSentinel"]["ready_for_upload"])
        self.assertEqual(
            gates["DICE"]["scores"]["reviewer_gate_posture"],
            "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY",
        )
        self.assertEqual(
            gates["HarborSentinel"]["scores"]["reviewer_gate_posture"],
            "LOCAL_REVIEWER_BLOCKED_ARGUMENT_GATE_UNASSESSED",
        )
        for lane_id in (
            "nsf_project_pitch",
            "erdc_sovereign_cloud_cso",
            "launchtn_3686_pitch_2026",
        ):
            self.assertEqual(
                gates_by_lane[lane_id]["scores"]["reviewer_gate_posture"],
                "LOCAL_REVIEWER_BLOCKED_ARGUMENT_CONFORMANCE",
            )
        self.assertEqual(
            gates_by_lane["dla_missionweave_sbir"]["scores"][
                "reviewer_gate_posture"
            ],
            "EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED",
        )
        self.assertEqual(
            gates_by_lane["darpa_falcon_dpa26bz04_dv016"]["scores"][
                "reviewer_gate_posture"
            ],
            "TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY",
        )
        self.assertEqual(
            gates_by_lane["cdc_ai_acquisition_rfi"]["scores"][
                "reviewer_gate_posture"
            ],
            "MONITOR_ONLY_NO_DUPLICATE_SUBMISSION",
        )
        self.assertNotIn("evidence_score", gates["DICE"]["scores"])
        self.assertGreaterEqual(gates["DICE"]["scores"]["artifact_custody_score"], 5)
        self.assertGreaterEqual(gates["HarborSentinel"]["scores"]["artifact_custody_score"], 5)
        self.assertIn("postmortem", "\n".join(gates["DICE"]["must_fix_before_upload"]).lower())
        self.assertIn("DSIP", "\n".join(gates["HarborSentinel"]["must_fix_before_upload"]))
        self.assertTrue(
            any(
                "DICE frozen live-breadth replay ready" in fact
                for fact in gates["DICE"]["artifact_or_portal_facts"]
            )
        )
        self.assertTrue(gates["DICE"]["phrase_checks_informational_only"])
        self.assertTrue(
            any(item["phrase"] == "frozen live-breadth replay" and item["present"] for item in gates["DICE"]["phrase_checks"])
        )
        self.assertTrue(
            any(item["phrase"] == "provenance-gated live-breadth annex" and item["present"] for item in gates["DICE"]["phrase_checks"])
        )
        self.assertTrue(
            any(
                "AIS review-burden profile ready" in fact
                for fact in gates["HarborSentinel"]["artifact_or_portal_facts"]
            )
        )
        self.assertTrue(
            any(
                item["phrase"] == "unlabeled public AIS review-burden profile" and item["present"]
                for item in gates["HarborSentinel"]["phrase_checks"]
            )
        )
        self.assertTrue(
            any(
                item["phrase"] == "measurement discipline and chain-of-custody" and item["present"]
                for item in gates["HarborSentinel"]["phrase_checks"]
            )
        )

    def test_gate_sanitizes_sensitive_identifiers_and_preserves_no_claims(self) -> None:
        module = load_module()
        payload = module.build_gate()
        markdown = module.render_markdown(payload)
        serialized = json.dumps(payload).lower() + markdown.lower()

        self.assertNotRegex(serialized, r"uei\s+[a-z0-9]{8,16}")
        self.assertNotRegex(serialized, r"cage/?ncage\s+[a-z0-9]{3,10}")
        self.assertNotIn("sk-" + "proj", serialized)
        self.assertNotIn('"ready_for_upload": true', serialized)
        self.assertIn("guaranteed funding", serialized)
        self.assertIn("do not claim", serialized)
        self.assertIn("does not authorize upload", markdown)
        self.assertIn(payload["reviewer_gate_sha256"], markdown)

    def test_write_gate_outputs_files(self) -> None:
        module = load_module()
        payload = module.build_gate()
        with tempfile.TemporaryDirectory() as temp_dir:
            old_out = module.OUT
            old_grants = module.GRANTS
            old_json = module.OUT_JSON
            old_md = module.OUT_MD
            try:
                module.OUT = Path(temp_dir) / "out"
                module.GRANTS = Path(temp_dir) / "grant_submissions"
                module.OUT_JSON = module.OUT / "reviewer_red_team_gate_latest.json"
                module.OUT_MD = module.GRANTS / "REVIEWER_RED_TEAM_GATE_2026-06-20.md"
                module.write_gate(payload)
                self.assertTrue(module.OUT_JSON.exists())
                self.assertTrue(module.OUT_MD.exists())
            finally:
                module.OUT = old_out
                module.GRANTS = old_grants
                module.OUT_JSON = old_json
                module.OUT_MD = old_md


if __name__ == "__main__":
    unittest.main()
