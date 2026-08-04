from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "outreach_gate", ROOT / "code" / "ops" / "outreach_gate.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
DLA_NV011_STATUS_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "DLA_NV011_OFFICIAL_STATUS_RECEIPT_2026-07-28.json"
)


class OutreachGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = MODULE.load_registry(
            ROOT / "config" / "outreach_registry_v1.json"
        )

    def test_registry_is_valid_and_ids_are_unique(self) -> None:
        MODULE.validate_registry(self.registry)
        ids = [c["outreach_id"] for c in self.registry["campaigns"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_codex_can_draft_but_cannot_send(self) -> None:
        draft = MODULE.evaluate(
            self.registry,
            "evtit-productization-review",
            actor="codex",
            action="draft",
            mode="reply",
        )
        self.assertTrue(draft["allowed"])
        send = MODULE.evaluate(
            self.registry,
            "evtit-productization-review",
            actor="codex",
            action="send",
            mode="reply",
            explicit_approval=True,
            gmail_preflight_complete=True,
        )
        self.assertFalse(send["allowed"])
        self.assertIn("Codex is draft-only", send["reason"])

    def test_existing_thread_campaign_rejects_new_message(self) -> None:
        result = MODULE.evaluate(
            self.registry,
            "epri-opai-membership-mou",
            actor="chatgpt",
            action="send",
            mode="new",
            explicit_approval=True,
            gmail_preflight_complete=True,
        )
        self.assertFalse(result["allowed"])
        self.assertIn("existing thread", result["reason"])

    def test_epri_mou_signature_state_blocks_email_reply(self) -> None:
        no_approval = MODULE.evaluate(
            self.registry,
            "epri-opai-membership-mou",
            actor="chatgpt",
            action="send",
            mode="reply",
            gmail_preflight_complete=True,
        )
        self.assertFalse(no_approval["allowed"])
        no_preflight = MODULE.evaluate(
            self.registry,
            "epri-opai-membership-mou",
            actor="chatgpt",
            action="send",
            mode="reply",
            explicit_approval=True,
        )
        self.assertFalse(no_preflight["allowed"])
        blocked = MODULE.evaluate(
            self.registry,
            "epri-opai-membership-mou",
            actor="chatgpt",
            action="send",
            mode="reply",
            explicit_approval=True,
            gmail_preflight_complete=True,
        )
        self.assertFalse(blocked["allowed"])
        self.assertIn("campaign status is blocked", blocked["reason"])

    def test_waiting_campaign_blocks_another_send(self) -> None:
        result = MODULE.evaluate(
            self.registry,
            "evtit-productization-review",
            actor="chatgpt",
            action="send",
            mode="reply",
            explicit_approval=True,
            gmail_preflight_complete=True,
        )
        self.assertFalse(result["allowed"])
        self.assertIn("wait for a substantive inbound reply", result["reason"])

    def test_receipt_confirmation_is_not_permission_to_follow_up(self) -> None:
        result = MODULE.evaluate(
            self.registry,
            "cdc-rfi-75d301-26-rfi-73483",
            actor="human",
            action="send",
            mode="reply",
            explicit_approval=True,
            gmail_preflight_complete=True,
        )
        self.assertFalse(result["allowed"])
        self.assertIn("receipt_confirmed_waiting", result["reason"])

    def test_project_argos_allows_drafting_but_codex_cannot_send(self) -> None:
        draft = MODULE.evaluate(
            self.registry,
            "hhs-project-argos-sources-sought",
            actor="codex",
            action="draft",
            mode="new",
        )
        self.assertTrue(draft["allowed"])
        self.assertIn("sending is not implied", draft["reason"])

        send = MODULE.evaluate(
            self.registry,
            "hhs-project-argos-sources-sought",
            actor="codex",
            action="send",
            mode="new",
            explicit_approval=True,
            gmail_preflight_complete=True,
        )
        self.assertFalse(send["allowed"])
        self.assertIn("Codex is draft-only", send["reason"])

    def test_dla_nv011_is_authoritatively_closed_without_private_identifiers(
        self,
    ) -> None:
        campaign = next(
            row
            for row in self.registry["campaigns"]
            if row["outreach_id"] == "LC-DLA-MISSIONWEAVE-NV011-001"
        )
        receipt = json.loads(DLA_NV011_STATUS_RECEIPT.read_text(encoding="utf-8"))

        self.assertEqual(campaign["status"], "closed")
        self.assertEqual(campaign["outbound_sequence"], 3)
        self.assertEqual(receipt["decision"], "CLOSED_NOT_FORMALLY_SUBMITTED")
        self.assertEqual(
            receipt["official_message"]["key_determination"],
            "The DSIP record shows the proposal as In Progress, so it was not "
            "formally submitted.",
        )
        self.assertFalse(receipt["official_message"]["reply_requested"])
        self.assertEqual(receipt["selected_template_id"], "NO_DUPLICATE_MONITOR")
        self.assertTrue(
            all(not value for value in receipt["privacy_controls"].values())
        )
        self.assertFalse(receipt["external_action_performed"])


if __name__ == "__main__":
    unittest.main()
