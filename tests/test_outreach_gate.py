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

    def test_dla_campaign_identity_is_stable(self) -> None:
        campaign = MODULE.campaign_by_key(
            self.registry,
            "dla-missionweave-l26bz-nv011-1380",
        )
        self.assertEqual(campaign["outreach_id"], "LC-DLA-MISSIONWEAVE-NV011-001")
        with self.assertRaises(MODULE.RegistryError):
            MODULE.campaign_by_key(
                self.registry,
                "dla-missionweave-dla26bz03-nv011",
            )

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

    def test_epri_opai_follow_up_is_closed_after_substantive_guidance(self) -> None:
        campaign = MODULE.campaign_by_key(
            self.registry,
            "epri-opai-membership-mou",
        )
        self.assertEqual(campaign["status"], "closed")
        self.assertEqual(campaign["outbound_sequence"], 6)
        self.assertEqual(campaign["last_outbound_utc"], "2026-08-03T22:28:19Z")
        self.assertTrue(campaign["inbound_since_last_outbound"])
        self.assertNotIn("2031", campaign["notes"])
        self.assertIn(
            "presence and contributions to Member Representative Committee",
            campaign["notes"],
        )
        self.assertIn(
            "do not establish EPRI or OPAI endorsement",
            campaign["notes"],
        )
        self.assertIn(
            "approval of a specific claim",
            campaign["notes"],
        )
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
        self.assertIn("campaign status is closed", blocked["reason"])

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

    def test_project_argos_is_single_send_locked_while_waiting(self) -> None:
        draft = MODULE.evaluate(
            self.registry,
            "hhs-project-argos-sources-sought",
            actor="codex",
            action="draft",
            mode="reply",
        )
        self.assertTrue(draft["allowed"])
        self.assertIn("sending is not implied", draft["reason"])

        send = MODULE.evaluate(
            self.registry,
            "hhs-project-argos-sources-sought",
            actor="codex",
            action="send",
            mode="reply",
            explicit_approval=True,
            gmail_preflight_complete=True,
        )
        self.assertFalse(send["allowed"])
        self.assertIn("Codex is draft-only", send["reason"])

        human_send = MODULE.evaluate(
            self.registry,
            "hhs-project-argos-sources-sought",
            actor="human",
            action="send",
            mode="reply",
            explicit_approval=True,
            gmail_preflight_complete=True,
        )
        self.assertFalse(human_send["allowed"])
        self.assertIn("waiting_for_reply", human_send["reason"])

        campaign = MODULE.campaign_by_key(
            self.registry, "hhs-project-argos-sources-sought"
        )
        self.assertEqual(campaign["outbound_sequence"], 1)
        self.assertEqual(
            campaign["last_outbound_utc"], "2026-07-29T01:52:18Z"
        )
        self.assertTrue(campaign["inbound_since_last_outbound"])
        self.assertIn("mailbox-system reach only", campaign["notes"])

    def test_emi_argos_is_single_send_locked_while_waiting(self) -> None:
        campaign = MODULE.campaign_by_key(
            self.registry,
            "hhs-project-argos-emi-teaming",
        )
        self.assertEqual(campaign["outbound_sequence"], 1)
        self.assertEqual(campaign["last_outbound_utc"], "2026-07-28T15:39:34Z")
        self.assertFalse(campaign["inbound_since_last_outbound"])
        send = MODULE.evaluate(
            self.registry,
            "hhs-project-argos-emi-teaming",
            actor="human",
            action="send",
            mode="reply",
            explicit_approval=True,
            gmail_preflight_complete=True,
        )
        self.assertFalse(send["allowed"])
        self.assertIn("waiting_for_reply", send["reason"])

    def test_ec_onboarding_receipt_is_confirmed_without_claiming_payment(
        self,
    ) -> None:
        campaign = MODULE.campaign_by_key(
            self.registry,
            "nashville-ec-fall-2026",
        )
        self.assertEqual(campaign["status"], "receipt_confirmed_waiting")
        self.assertEqual(campaign["outbound_sequence"], 6)
        self.assertEqual(campaign["last_outbound_utc"], "2026-07-31T20:32:22Z")
        self.assertTrue(campaign["inbound_since_last_outbound"])
        self.assertIn("everything was received on time", campaign["notes"])
        self.assertIn("does not establish payment", campaign["notes"])
        self.assertIn("Do not resend", campaign["notes"])
        self.assertIn("Profile coming soon", campaign["notes"])
        self.assertIn("mixer has elapsed", campaign["notes"])
        self.assertIn(
            "no receipt establishing completion",
            campaign["notes"],
        )
        self.assertIn(
            "founder_verifies_official_private_kickoff_time_location_and_eia_status",
            campaign["next_allowed_action"],
        )

        send = MODULE.evaluate(
            self.registry,
            "nashville-ec-fall-2026",
            actor="human",
            action="send",
            mode="reply",
            explicit_approval=True,
            gmail_preflight_complete=True,
        )
        self.assertFalse(send["allowed"])
        self.assertIn("receipt_confirmed_waiting", send["reason"])

    def test_launchtn_support_request_is_single_send_locked(self) -> None:
        campaign = MODULE.campaign_by_key(
            self.registry,
            "launchtn-sbir-sttr-support-microgrant",
        )
        self.assertEqual(campaign["status"], "waiting_for_reply")
        self.assertEqual(campaign["outbound_sequence"], 1)
        self.assertEqual(campaign["last_outbound_utc"], "2026-07-30T18:33:55Z")
        self.assertFalse(campaign["inbound_since_last_outbound"])
        self.assertIn("not an award", campaign["notes"])

        send = MODULE.evaluate(
            self.registry,
            "launchtn-sbir-sttr-support-microgrant",
            actor="human",
            action="send",
            mode="reply",
            explicit_approval=True,
            gmail_preflight_complete=True,
        )
        self.assertFalse(send["allowed"])
        self.assertIn("waiting_for_reply", send["reason"])

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
