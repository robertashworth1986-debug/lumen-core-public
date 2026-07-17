from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LIVE_FUNDING_PORTAL_HANDOFF.py"


def load_module():
    spec = importlib.util.spec_from_file_location("live_funding_portal_handoff", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_handoff_reserves_current_session_browser_and_uses_current_board() -> None:
    module = load_module()
    payload = module.build_payload(date(2026, 7, 17))

    assert payload["schema"] == "lumencore.live_funding_portal_handoff.v2"
    assert payload["status"] == "SESSION_BROWSER_RESERVED_FOR_USER_AUTHENTICATION"
    assert len(payload["source_command_board_sha256"]) == 64
    control = payload["browser_control"]
    assert control["browser_scope"] == "CURRENT_CODEX_SESSION_IN_APP_BROWSER_ONLY"
    assert control["resume_signal"] == "I'm in"
    assert control["navigation_allowed_before_resume_signal"] is False
    assert control["inspect_current_page_before_navigation"] is True
    assert control["preserve_current_url"] is True
    assert control["browser_navigation_performed_by_builder"] is False
    assert control["credential_collection_allowed"] is False
    assert payload["browser_navigation_performed"] is False
    assert payload["external_action_performed"] is False
    assert payload["final_submit_allowed_without_human"] is False


def test_handoff_prioritizes_current_deadlines_and_preserves_all_stop_gates() -> None:
    module = load_module()
    payload = module.build_payload(date(2026, 7, 17))
    queue = sorted(payload["queue"], key=lambda row: row["priority"])

    assert [row["opportunity_number"] for row in queue] == [
        "NASHVILLE-EC-FALL-2026",
        "DLA26BZ03-NV011",
        "26-510",
        "W912HZ26SC005",
        "LAUNCHTN-3686-2026",
    ]
    assert queue[0]["deadline_date"] == "2026-07-17"
    missionweave = queue[1]
    assert missionweave["deadline_date"] == "2026-07-22"
    assert missionweave["deadline_utc"] == "2026-07-22T16:00:00Z"
    assert "July 22, 2025" in missionweave["official_deadline_text"]
    assert any("15-file manifest" in action for action in missionweave["next_safe_action"])
    assert any("0/50 to 50/50" in action for action in missionweave["next_safe_action"])
    assert missionweave["action_gate"] == {
        "status": "PRIVATE_DSIP_FACTS_NOT_CAPTURED",
        "submission_ready_for_human_click": False,
        "required_private_gate_count": 50,
        "passed_private_gate_count": 0,
        "open_gate_count": 50,
        "private_input_present": False,
        "private_values_exposed": False,
    }
    assert any("ITAR/JCP" in stop for stop in missionweave["stop_conditions"])
    assert any("final DSIP submission" in stop for stop in missionweave["stop_conditions"])
    for item in queue:
        assert item["external_send_allowed_without_human"] is False
        assert item["final_submit_allowed_without_human"] is False
        assert item["stop_conditions"]
        assert item["human_gate"]
        assert len(item["source_lane_sha256"]) == 64


def test_handoff_keeps_patent_and_sam_private_and_bounded() -> None:
    module = load_module()
    payload = module.build_payload(date(2026, 7, 17))
    controls = {row["system"]: row for row in payload["account_maintenance"]}

    patent = controls["USPTO Patent Center"]
    assert "six required official docket categories" in patent["next_safe_action"]
    assert any("Do not infer" in stop for stop in patent["stop_conditions"])
    sam = controls["SAM.gov public API credential rotation"]
    assert "hidden-input installer" in sam["next_safe_action"]
    assert any("Do not paste" in stop for stop in sam["stop_conditions"])
    assert payload["private_contact_data_included"] is False
    assert payload["credentials_included"] is False


def test_rendered_handoff_is_public_safe_and_has_no_stale_send_state() -> None:
    module = load_module()
    payload = module.build_payload(date(2026, 7, 17))
    rendered = module.render_markdown(payload)

    assert "Live Funding Portal Handoff" in rendered
    assert "Navigation before resume signal: `false`" in rendered
    assert "DLA26BZ03-NV011" in rendered
    assert "Passed: `0/50`" in rendered
    assert "EPRI administrative onboarding was sent" in rendered
    assert "EPRI draft" not in rendered
    assert "Private contact data included: `false`" in rendered
    assert "Final submit without human: `false`" in rendered
    assert module.public_safety_hits(rendered) == []
    assert len(payload["handoff_sha256"]) == 64
