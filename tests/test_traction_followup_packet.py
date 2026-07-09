from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_TRACTION_FOLLOWUP_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("traction_followup_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_traction_followup_packet_is_ready_and_human_gated():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "traction_followup_packet_v1"
    assert payload["status"] == "TRACTION_FOLLOWUP_READY_HUMAN_SEND_REQUIRED"
    assert payload["lane"]["lane_id"] == "evtit_blackdog_inkind"
    assert payload["lane"]["status"] == "RESET_NOTE_SENT_TECH_REVIEW_PENDING"
    assert summary["thread_signal_count"] == 7
    assert summary["build_scope_count"] == 6
    assert summary["draft_count"] == 2
    assert summary["diligence_artifacts_present"] is True
    assert summary["reviewer_gate_clear"] is True
    assert summary["unsafe_secret_count"] == 0
    assert summary["unsafe_claim_count"] == 0
    assert summary["human_send_required"] is True
    assert summary["external_send_allowed_without_human"] is False
    assert summary["equity_terms_allowed_without_human"] is False
    assert summary["partnership_claimed"] is False
    assert summary["investment_claimed"] is False
    assert summary["services_award_claimed"] is False
    assert summary["field_validation_claimed"] is False
    assert len(payload["traction_followup_packet_sha256"]) == 64


def test_thread_signals_include_latest_reset_message_without_credentials():
    module = load_module()
    payload = module.build_payload()
    refs = {signal["source_ref"] for signal in payload["thread_signals"]}

    assert "gmail:19f43c8a4ba9346e" in refs
    assert "gmail:19f47e797960c0cd" in refs
    assert "gmail:19f4822c21a4a861" in refs
    assert "gmail:19f484a1fe4aea3b" in refs
    assert "gmail:19f485a69ba2410d" in refs
    for signal in payload["thread_signals"]:
        combined = f"{signal['safe_signal']} {signal['action_meaning']}".lower()
        assert "zoom.us" not in combined
        assert "meeting id" not in combined
        assert "password" not in combined


def test_followup_drafts_are_ready_but_not_send_authority():
    module = load_module()
    payload = module.build_payload()
    drafts = {draft["draft_id"]: draft for draft in payload["followup_drafts"]}

    assert set(drafts) == {"same_day_reset_next_step", "technical_team_packet_note"}
    assert all(draft["human_send_required"] is True for draft in drafts.values())
    reset_body = "\n".join(drafts["same_day_reset_next_step"]["body"])
    assert "30-minute technical fit call" in reset_body
    assert "no partnership" in reset_body.lower()
    assert "field validation" in reset_body.lower()


def test_diligence_artifacts_are_hash_backed():
    module = load_module()
    payload = module.build_payload()
    by_path = {row["path"]: row for row in payload["diligence_artifacts"]}

    expected = [
        "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/REVIEWER_DECISION_BRIEF_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/DATA_ROOM_MANIFEST_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/FEDERAL_SUBMISSION_PROTOCOL_PACKET_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/AUTONOMOUS_QUANT_GOVERNANCE_PACKET_2026-07-09.md",
    ]
    for path in expected:
        row = by_path[path]
        assert row["present"] is True
        assert row["bytes"] > 0
        assert len(row["sha256"]) == 64


def test_rendered_followup_packet_is_public_safe_and_action_gated():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "EVTit Traction Follow-Up Packet" in rendered
    assert "External send without human: `false`" in rendered
    assert "Equity terms without human: `false`" in rendered
    assert "Partnership claimed: `false`" in rendered
    assert "Investment claimed: `false`" in rendered
    assert "Services award claimed: `false`" in rendered
    assert "send_email_allowed_without_human: `False`" in rendered
    assert "zoom.us" not in lowered
    assert "meeting id" not in lowered
    assert "password" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
    assert "@evtit" not in lowered
    assert "@blackdog" not in lowered
