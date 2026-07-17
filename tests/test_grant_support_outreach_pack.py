from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code" / "ops"))

import BUILD_GRANT_SUPPORT_OUTREACH_PACK as packer  # noqa: E402


class GrantSupportOutreachPackTests(unittest.TestCase):
    def fixture_action_board(self) -> dict:
        return {
            "packages": [
                {
                    "rank": 1,
                    "package": "DICE",
                    "portal": "DARPA BAAT",
                    "readiness": "LOCAL_READY_PORTAL_BLOCKED_USER_GATES",
                    "primary_unlock": "BAAT account and submitter authority.",
                    "portal_user_blockers": ["BAAT account and organization profile are unverified."],
                },
                {
                    "rank": 2,
                    "package": "HarborSentinel",
                    "portal": "DSIP",
                    "readiness": "LOCAL_READY_PORTAL_BLOCKED_USER_GATES",
                    "primary_unlock": "DSIP and CMMC/SPRS facts.",
                    "portal_user_blockers": ["CMMC/SPRS/Affirming Official status is unverified."],
                },
                {
                    "rank": 3,
                    "package": "NSF Project Pitch",
                    "portal": "NSF Project Pitch portal",
                    "readiness": "LOCAL_READY_PORTAL_BLOCKED_USER_GATES",
                    "primary_unlock": "Duplicate-pitch status and paste counts.",
                    "portal_user_blockers": ["Portal paste counts must be confirmed."],
                },
            ]
        }

    def test_pack_uses_official_source_urls_and_no_submit_boundary(self) -> None:
        payload = packer.build_pack(
            self.fixture_action_board(),
            {"freeze_signature_sha256": "abc123"},
        )
        self.assertEqual(payload["schema"], "grant_support_outreach_pack_v1")
        urls = {lane["source_url"] for lane in payload["official_support_lanes"]}
        self.assertIn("https://www.sba.gov/local-assistance/federal-contracting-assistance", urls)
        self.assertIn("https://business.defense.gov/Programs/Cyber-Security-Resources/", urls)
        self.assertIn(
            "https://www.uspto.gov/patents/basics/using-legal-services/pro-bono/patent-pro-bono-program",
            urls,
        )
        self.assertIn("https://www.sbir.gov/community/fast", urls)
        self.assertFalse(any(card["ready_to_submit"] for card in payload["package_blocker_snapshot"]))
        self.assertIn("does not authorize upload", payload["boundary"])
        self.assertIn("CMMC", json.dumps(payload))
        self.assertIn("Patent Pro Bono", json.dumps(payload))

    def test_markdown_contains_secret_controls_and_live_breadth_policy(self) -> None:
        payload = packer.build_pack(
            self.fixture_action_board(),
            {"freeze_signature_sha256": "abc123"},
        )
        markdown = packer.render_markdown(payload)
        self.assertIn("Do not send passwords, MFA codes, API keys", markdown)
        self.assertIn("Recommended paid data now: False", markdown)
        self.assertIn("DARPA BAAT", markdown)
        self.assertIn("DSIP", markdown)
        self.assertNotIn("guaranteed funding", markdown.lower())
        self.assertNotIn("guaranteed award", markdown.lower())

    def test_response_templates_are_bounded_and_block_unresolved_tokens(self) -> None:
        payload = packer.build_pack(
            self.fixture_action_board(),
            {"freeze_signature_sha256": "abc123"},
        )

        responses = payload["response_templates"]
        self.assertEqual(
            set(responses),
            {
                "receipt_acknowledgment",
                "verified_fact_request",
                "referral_or_routing",
                "decline_or_no_fit",
                "deadline_confirmation",
                "packet_or_attachment_request",
            },
        )
        self.assertFalse(responses["receipt_acknowledgment"]["reply_required_by_default"])
        self.assertTrue(responses["verified_fact_request"]["reply_required_by_default"])
        self.assertFalse(responses["deadline_confirmation"]["reply_required_by_default"])

        for template in responses.values():
            body = template["body"].lower()
            self.assertIn("best regards", body)
            self.assertNotIn("guaranteed", body)
            self.assertNotIn("world-class", body)
            self.assertNotIn("proven savings", body)
            self.assertTrue(template["required_checks"])

        attachment = responses["packet_or_attachment_request"]
        self.assertIn("claim boundary", " ".join(attachment["required_checks"]).lower())
        self.assertIn("does not claim independent", attachment["body"].lower())

        gate = payload["response_send_gate"]
        self.assertEqual(gate["unresolved_placeholder_token"], "[REPLACE:")
        self.assertFalse(gate["send_allowed_with_unresolved_placeholders"])
        self.assertIn("no_duplicate_send", gate["final_checks"])

        markdown = packer.render_markdown(payload)
        self.assertIn("## Response Templates", markdown)
        self.assertIn("## Response Send Gate", markdown)
        self.assertIn("Send allowed with unresolved placeholders: `False`", markdown)

    def test_write_pack_outputs_json_and_markdown(self) -> None:
        payload = packer.build_pack(
            self.fixture_action_board(),
            {"freeze_signature_sha256": "abc123"},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            old_out = packer.OUT
            old_grants = packer.GRANTS
            old_json = packer.OUT_JSON
            old_md = packer.OUT_MD
            try:
                packer.OUT = Path(temp_dir) / "out"
                packer.GRANTS = Path(temp_dir) / "grant_submissions"
                packer.OUT_JSON = packer.OUT / "grant_support_outreach_pack_latest.json"
                packer.OUT_MD = packer.GRANTS / "GRANT_SUPPORT_OUTREACH_PACK_2026-06-20.md"
                packer.write_pack(payload)
                self.assertTrue(packer.OUT_JSON.exists())
                self.assertTrue(packer.OUT_MD.exists())
            finally:
                packer.OUT = old_out
                packer.GRANTS = old_grants
                packer.OUT_JSON = old_json
                packer.OUT_MD = old_md


if __name__ == "__main__":
    unittest.main()
