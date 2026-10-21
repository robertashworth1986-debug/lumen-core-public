from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
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

    def test_current_operating_contract_and_ci_allow_approved_codex_execution(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/outreach-governance.yml").read_text(
            encoding="utf-8")
        self.assertIn("not restricted to drafts because of its agent name", agents)
        self.assertIn("same outreach preflight required of ChatGPT / Luma", agents)
        self.assertIn("does not enable live orders", agents)
        self.assertIn("not restricted to drafts because of its agent name", workflow)
        self.assertNotIn("draft-only for all external communication", agents)
        self.assertNotIn("draft-only for all external communication", workflow)

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

    def test_codex_can_draft_but_waiting_campaign_still_blocks_send(self) -> None:
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
        self.assertIn("wait for a substantive inbound reply", send["reason"])

    def ready_registry(self) -> dict:
        registry = copy.deepcopy(self.registry)
        registry["campaigns"] = [{
            "campaign_key": "test-approved-outreach",
            "organization": "Test recipient",
            "status": "ready_for_first_outbound",
            "thread_mode": "new_thread_allowed",
            "outbound_sequence": 0,
            "duplicate_detected": False,
            "duplicate_count": 0,
            "inbound_since_last_outbound": False,
            "next_allowed_action": "review_exact_message",
            "outreach_id": "LC-TEST-APPROVED-001",
            "notes": "Synthetic test fixture; not a real recipient or approval.",
        }]
        return registry

    def evaluate_ready(self, registry=None, **options) -> dict:
        defaults = dict(actor="codex", action="send", mode="new",
                        explicit_approval=True, gmail_preflight_complete=True)
        defaults.update(options)
        return MODULE.evaluate(registry or self.ready_registry(),
                               "test-approved-outreach", **defaults)

    def test_approved_codex_send_has_same_eligibility_as_chatgpt(self) -> None:
        for actor in ("codex", "chatgpt", "human"):
            with self.subTest(actor=actor):
                result = self.evaluate_ready(actor=actor)
                self.assertTrue(result["allowed"])
                self.assertIn("send exactly one message", result["required_steps"])

    def test_all_actors_require_actual_boolean_approval_and_preflight(self) -> None:
        for actor in ("codex", "chatgpt", "human"):
            for value in (False, None, "yes", "false", 1):
                with self.subTest(actor=actor, value=value):
                    self.assertFalse(self.evaluate_ready(
                        actor=actor, explicit_approval=value)["allowed"])
                    self.assertFalse(self.evaluate_ready(
                        actor=actor, gmail_preflight_complete=value)["allowed"])

    def test_legacy_private_registry_can_keep_codex_disabled(self) -> None:
        registry = self.ready_registry()
        registry["policy"]["codex_send_allowed"] = False
        registry["policy"].pop("codex_send_requires_explicit_action_time_approval")
        result = self.evaluate_ready(registry)
        self.assertFalse(result["allowed"])
        self.assertIn("disabled in this controlling registry", result["reason"])
        self.assertTrue(self.evaluate_ready(registry, actor="chatgpt")["allowed"])

    def test_codex_enablement_cannot_disable_approval_or_preflight(self) -> None:
        fields = ("codex_send_requires_explicit_action_time_approval",
                  "chatgpt_send_requires_explicit_action_time_approval",
                  "gmail_sent_preflight_required", "draft_only_by_default")
        for field in fields:
            for value in (False, None, "true", 1):
                with self.subTest(field=field, value=value):
                    registry = self.ready_registry()
                    registry["policy"][field] = value
                    with self.assertRaises(MODULE.RegistryError):
                        self.evaluate_ready(registry)
        registry = self.ready_registry()
        registry["policy"].pop("codex_send_requires_explicit_action_time_approval")
        with self.assertRaises(MODULE.RegistryError):
            MODULE.validate_registry(registry)

    def test_codex_permission_must_be_a_boolean(self) -> None:
        for value in (None, "true", "false", 1, 0):
            with self.subTest(value=value):
                registry = self.ready_registry()
                registry["policy"]["codex_send_allowed"] = value
                with self.assertRaises(MODULE.RegistryError):
                    MODULE.validate_registry(registry)

    def test_codex_approval_does_not_override_campaign_or_thread_holds(self) -> None:
        for status in ("closed", "blocked", "waiting_for_reply",
                       "receipt_confirmed_waiting", "action_required_draft_ready"):
            with self.subTest(status=status):
                registry = self.ready_registry()
                registry["campaigns"][0]["status"] = status
                self.assertFalse(self.evaluate_ready(registry)["allowed"])
        registry = self.ready_registry()
        registry["campaigns"][0]["thread_mode"] = "existing_thread_only"
        self.assertFalse(self.evaluate_ready(registry)["allowed"])
        registry = self.ready_registry()
        registry["campaigns"][0].update(duplicate_detected=True, duplicate_count=1)
        self.assertFalse(self.evaluate_ready(registry)["allowed"])

    def test_codex_can_send_approved_requested_reply_in_existing_thread(self) -> None:
        registry = self.ready_registry()
        registry["campaigns"][0].update(status="action_required_draft_ready",
                                      thread_mode="existing_thread_only",
                                      outbound_sequence=1,
                                      inbound_since_last_outbound=True)
        self.assertTrue(self.evaluate_ready(registry, mode="reply")["allowed"])

    def test_unknown_campaign_and_financial_actions_are_not_enabled(self) -> None:
        with self.assertRaises(MODULE.RegistryError):
            MODULE.evaluate(self.ready_registry(), "unregistered", actor="codex",
                            action="send", mode="new", explicit_approval=True,
                            gmail_preflight_complete=True)
        for action in ("trade", "transfer", "pay", "submit", "sign"):
            with self.subTest(action=action), self.assertRaises(MODULE.RegistryError):
                self.evaluate_ready(action=action)

    def test_cli_approved_codex_eligibility_passes_without_sending(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private_registry.json"
            path.write_text(json.dumps(self.ready_registry()), encoding="utf-8")
            command = [sys.executable, str(ROOT / "code/ops/outreach_gate.py"),
                       "--registry", str(path), "check", "--campaign",
                       "test-approved-outreach", "--actor", "codex", "--action",
                       "send", "--mode", "new", "--gmail-preflight-complete"]
            blocked = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(blocked.returncode, 2, blocked.stderr)
            self.assertFalse(json.loads(blocked.stdout)["allowed"])
            allowed = subprocess.run(command + ["--explicit-approval"],
                                     capture_output=True, text=True, check=False)
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertTrue(json.loads(allowed.stdout)["allowed"])
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")),
                             self.ready_registry())

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
        self.assertIn("waiting_for_reply", send["reason"])

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
