from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code" / "ops"))

from build_opai_action_queue import (  # noqa: E402
    ConfigurationError,
    build_action_queue,
    canonical_json_hash,
    evidence_readiness,
    membership_action,
    parse_utc,
    validate_program,
)


PROGRAM = {
    "schema": "opai_entry_program_v1",
    "source_checked_utc": "2026-07-16T06:05:00Z",
    "claim_boundary": "Does not prove membership, selection, funding, or validation.",
    "sources": {"membership": "https://openpowerai.org/consortium-membership"},
    "membership": {
        "status": "interest_submitted_not_yet_accepted",
        "last_contact_utc": "2026-07-16T05:30:03Z",
        "next_contact_not_before_utc": "2026-07-20T14:00:00Z",
        "suppress_new_contact": True,
        "contact_mode": "existing_thread_only",
        "next_action": "Wait for the onboarding response.",
    },
    "ai_for_power_2026": {
        "application_state": "requires_program_confirmation",
        "public_application_evaluation_window": "May / June 2026",
        "page_still_displays_submit_application": True,
        "pitch_day_date": "2026-08-05",
        "next_action": "Verify the current window.",
    },
    "opportunities": [
        {
            "id": "ami_data_validation",
            "title": "AMI Data Validation",
            "category": "T&D Operations",
            "public_source": "https://epri.brightidea.com/AIforPower2026",
            "fit_score": 10,
            "entry_claim": "Bounded replay validation.",
            "repo_evidence_paths": ["evidence.md", "missing.md"],
            "external_gates": ["utility data", "locked metric"],
        }
    ],
}


class OPAIActionQueueTests(unittest.TestCase):
    def test_membership_guard_suppresses_duplicate_outreach_before_cooldown(self) -> None:
        action = membership_action(
            PROGRAM["membership"],
            now_utc=parse_utc("2026-07-16T12:00:00Z"),
        )
        self.assertEqual(action["state"], "wait")
        self.assertEqual(action["priority"], "blocked")
        self.assertIn("duplicate", action["reason"].lower())
        self.assertEqual(action["contact_mode"], "existing_thread_only")

    def test_membership_follow_up_opens_after_cooldown_when_suppression_is_cleared(self) -> None:
        membership = dict(PROGRAM["membership"])
        membership["suppress_new_contact"] = False
        action = membership_action(
            membership,
            now_utc=parse_utc("2026-07-20T14:00:01Z"),
        )
        self.assertEqual(action["state"], "ready")
        self.assertEqual(action["priority"], "high")

    def test_invalid_program_fails_closed(self) -> None:
        invalid = dict(PROGRAM)
        invalid["schema"] = "unknown"
        with self.assertRaises(ConfigurationError):
            validate_program(invalid)

    def test_evidence_readiness_rejects_escape_paths_and_counts_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "evidence.md").write_text("bounded proof\n", encoding="utf-8")
            readiness = evidence_readiness(
                root,
                ["evidence.md", "missing.md", "../outside.txt"],
            )
        self.assertEqual(readiness["present"], ["evidence.md"])
        self.assertEqual(readiness["present_count"], 1)
        self.assertEqual(readiness["total_count"], 3)
        self.assertIn("../outside.txt", readiness["missing"])

    def test_queue_marks_challenge_urgent_without_claiming_submission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "evidence.md").write_text("bounded proof\n", encoding="utf-8")
            payload = build_action_queue(
                PROGRAM,
                {
                    "schema": "opai_consortium_intelligence_v1",
                    "summary": {"pages_fetched": 7, "pages_failed": 0},
                    "intelligence_hash_sha256": "a" * 64,
                },
                root=root,
                generated_utc="2026-07-16T12:00:00Z",
            )
        self.assertEqual(payload["ai_for_power_2026"]["priority"], "critical")
        self.assertEqual(payload["ai_for_power_2026"]["state"], "verify")
        self.assertEqual(payload["ai_for_power_2026"]["days_to_pitch_day"], 20)
        self.assertFalse(payload["automation_boundary"]["applications_submitted"])
        self.assertFalse(payload["automation_boundary"]["emails_sent"])
        self.assertIn("does not prove", payload["claim_boundary"].lower())

    def test_queue_hash_is_deterministic_for_same_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = build_action_queue(
                PROGRAM,
                {"schema": "opai_consortium_intelligence_seed_v1"},
                root=root,
                generated_utc="2026-07-16T12:00:00Z",
            )
            second = build_action_queue(
                PROGRAM,
                {"schema": "opai_consortium_intelligence_seed_v1"},
                root=root,
                generated_utc="2026-07-16T12:00:00Z",
            )
        self.assertEqual(
            first["action_queue_hash_sha256"],
            second["action_queue_hash_sha256"],
        )
        self.assertEqual(len(first["action_queue_hash_sha256"]), 64)
        self.assertEqual(canonical_json_hash({"a": 1}), canonical_json_hash({"a": 1}))

    def test_program_file_is_valid_json(self) -> None:
        program_path = ROOT / "config" / "opai_entry_program.json"
        payload = json.loads(program_path.read_text(encoding="utf-8"))
        validate_program(payload)


if __name__ == "__main__":
    unittest.main()
