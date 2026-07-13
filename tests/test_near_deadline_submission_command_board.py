from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD.py"


def load_module():
    spec = importlib.util.spec_from_file_location("near_deadline_submission_command_board", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_near_deadline_board_identifies_stage_now_and_human_gates():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "near_deadline_submission_command_board_v2"
    assert payload["status"] == "NEAR_DEADLINE_COMMAND_BOARD_ACTIVE_WITH_VERIFIED_SENDS"
    assert payload["summary"]["lane_count"] == 14
    assert payload["summary"]["stage_now_count"] == 3
    assert payload["summary"]["sent_verified_count"] == 2
    assert payload["summary"]["emergency_eligibility_gate_count"] == 1
    assert payload["summary"]["no_bid_or_partner_only_count"] == 4
    assert payload["summary"]["human_gated_count"] == 12
    assert payload["summary"]["final_submit_allowed_without_human"] is False
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["pricing_allowed_without_human"] is False
    assert payload["summary"]["legal_certification_allowed_without_human"] is False

    stage_ids = {row["opportunity_number"] for row in payload["stage_now"]}
    assert "80TECH26RFI0020" not in stage_ids
    assert "ACCAPGAIDPRFI4" not in stage_ids
    assert "693JJ326R000012" in stage_ids
    assert "26-511" in stage_ids
    assert "W912HZ26SC005" in stage_ids

    sent_ids = {row["opportunity_number"] for row in payload["sent_verified"]}
    assert sent_ids == {"80TECH26RFI0020", "ACCAPGAIDPRFI4"}


def test_near_deadline_board_keeps_hud_and_bop_behind_correct_gates():
    module = load_module()
    payload = module.build_payload()

    lanes = {row["opportunity_number"]: row for row in payload["lanes"]}
    assert lanes["PDR-2600-DC-029Q"]["command"] == "ELIGIBILITY_AND_PARTNER_GATE"
    assert lanes["PDR-2600-DC-029Q"]["deadline_utc"] == "2026-07-14T03:59:59Z"
    assert lanes["PDR-2600-DC-029Q"]["official_deadline_text"].endswith("Eastern Time")
    assert lanes["15BCMS26Q70000005"]["command"] == "PRICE_AND_COMPLIANCE_GATE"
    assert lanes["HHS-2026-ACF-ACYF-CA-0037"]["command"] == "NO_SOLO_SUBMIT_PARTNER_ONLY"
    assert lanes["HHS-2026-ACL-NIDILRR-REGE-0212"]["eligibility_state"] == "SMALL_BUSINESS_ELIGIBLE"
    assert lanes["26-508"]["command"] == "NO_BID_MISSED_PREREQUISITE"
    assert "JUNE_16" in lanes["26-508"]["eligibility_state"]

    for lane in payload["lanes"]:
        assert lane["external_send_allowed_without_human"] is False
        assert lane["final_submit_allowed_without_human"] is False
        assert lane["days_to_close"] == module.days_to_close(lane["deadline_date"])
        assert lane["deadline_bucket"] == module.deadline_bucket(lane["days_to_close"])
        assert lane["eligibility_state"]
        assert lane["fit_state"]
        assert len(lane["lane_sha256"]) == 64


def test_near_deadline_board_rendering_is_safe_and_cites_sources():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Near-Deadline Submission Command Board" in rendered
    assert "Final submit without human: `false`" in rendered
    assert "https://seedfund.nsf.gov/project-pitch/" in rendered
    assert "https://www.grants.gov/search-results-detail/362360" in rendered
    assert "Sent And Verified" in rendered
    assert "No-Bid Or Partner-Only" in rendered
    assert len(payload["command_board_sha256"]) == 64

    for marker in module.SENSITIVE_MARKERS:
        assert marker not in lowered
