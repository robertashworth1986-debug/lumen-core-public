from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LIVE_FUNDING_PORTAL_HANDOFF.py"
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "NASHVILLE_EC_PORTAL_HANDOFF_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)
MISSIONWEAVE_GATE = (
    ROOT
    / "grant_submissions"
    / "DLA26BZ03_NV011_MissionWeave"
    / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json"
)


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
    missionweave_summary = json.loads(
        MISSIONWEAVE_GATE.read_text(encoding="utf-8")
    )["gate_summary"]

    assert [row["opportunity_number"] for row in queue] == [
        "NASHVILLE-EC-FALL-2026",
        "DLA26BZ03-NV011",
        "26-510",
        "W912HZ26SC005",
        "LAUNCHTN-3686-2026",
    ]
    nashville = queue[0]
    assert nashville["deadline_date"] == "2026-07-17"
    assert nashville["action_gate"] == {
        "status": "PORTAL_SUBMISSION_CONFIRMED",
        "submission_ready_for_human_click": False,
        "required_private_gate_count": 15,
        "passed_private_gate_count": 15,
        "open_gate_count": 0,
        "private_input_present": True,
        "private_values_exposed": False,
    }
    assert nashville["deadline_support"] == {
        "status": "OFFICIAL_SUPPORT_CONFIRMED_CLOSE_TIME_APPLICATION_NOT_SUBMITTED",
        "sent_utc": "2026-07-17T12:05:34Z",
        "do_not_duplicate_send": True,
        "email_is_application": False,
        "reply_required": False,
        "timezone_explicit_in_message": False,
        "operational_timezone": "America/Chicago",
    }
    assert any(
        path.endswith("CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py")
        for path in nashville["package_files"]
    )
    assert any(
        "CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py" in action
        for action in nashville["next_safe_action"]
    )
    missionweave = queue[1]
    assert missionweave["deadline_date"] == "2026-07-22"
    assert missionweave["deadline_utc"] == "2026-07-22T16:00:00Z"
    assert "July 22, 2025" in missionweave["official_deadline_text"]
    assert any("15-file manifest" in action for action in missionweave["next_safe_action"])
    assert any(
        (
            "beyond "
            f"{missionweave_summary['passed_private_gate_count']}/"
            f"{missionweave_summary['required_private_gate_count']}"
        )
        in action
        for action in missionweave["next_safe_action"]
    )
    assert missionweave["action_gate"] == {
        "status": "PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN",
        "submission_ready_for_human_click": False,
        "required_private_gate_count": missionweave_summary[
            "required_private_gate_count"
        ],
        "passed_private_gate_count": missionweave_summary[
            "passed_private_gate_count"
        ],
        "open_gate_count": missionweave_summary["open_gate_count"],
        "private_input_present": True,
        "private_values_exposed": False,
        "private_capture_tool": (
            "code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py"
        ),
        "private_input_sha256_exposed": False,
        "private_volume2_finalizer": (
            "code/ops/FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py"
        ),
        "private_capture_workflow": (
            "grant_submissions/DLA26BZ03_NV011_MissionWeave/"
            "MISSIONWEAVE_DSIP_PRIVATE_CAPTURE_WORKFLOW_2026-07-17.md"
        ),
        "private_final_volume2_present": True,
        "private_final_volume2_path_exposed": False,
        "private_final_volume2_sha256_exposed": False,
        "pre_submit_excludes_action_time_approval": True,
        "credential_values_accepted": False,
        "firm_pin_value_accepted": False,
    }
    assert any(
        "hidden sectioned MissionWeave collector" in action
        for action in missionweave["next_safe_action"]
    )
    assert any("ITAR/JCP" in stop for stop in missionweave["stop_conditions"])
    assert any("final DSIP submission" in stop for stop in missionweave["stop_conditions"])
    for item in queue:
        assert item["external_send_allowed_without_human"] is False
        assert item["final_submit_allowed_without_human"] is False
        assert item["stop_conditions"]
        if item["opportunity_number"] == "NASHVILLE-EC-FALL-2026":
            assert item["human_gate"] == []
            assert item["action_gate"]["status"] == "PORTAL_SUBMISSION_CONFIRMED"
        else:
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
    missionweave_summary = json.loads(
        MISSIONWEAVE_GATE.read_text(encoding="utf-8")
    )["gate_summary"]

    assert "Live Funding Portal Handoff" in rendered
    assert "Navigation before resume signal: `false`" in rendered
    assert "DLA26BZ03-NV011" in rendered
    assert "Passed: `15/15`" in rendered
    assert "Status: `OFFICIAL_SUPPORT_CONFIRMED_CLOSE_TIME_APPLICATION_NOT_SUBMITTED`" in rendered
    assert "Do not duplicate: `true`" in rendered
    assert "Email is application: `false`" in rendered
    assert "Reply required: `false`" in rendered
    assert "Timezone explicit in message: `false`" in rendered
    assert "Operational timezone: `America/Chicago`" in rendered
    assert (
        "Passed: "
        f"`{missionweave_summary['passed_private_gate_count']}/"
        f"{missionweave_summary['required_private_gate_count']}`"
        in rendered
    )
    assert "EPRI administrative onboarding was sent" in rendered
    assert "referred the request to the subject matter expert" in rendered
    assert "bounded acknowledgment is sent" in rendered
    assert "do not reuse the rejected address" in rendered
    assert "EPRI draft" not in rendered
    assert "Private contact data included: `false`" in rendered
    assert "Final submit without human: `false`" in rendered
    assert module.public_safety_hits(rendered) == []
    assert len(payload["handoff_sha256"]) == 64


def test_current_nashville_portal_handoff_mirror_matches_sources() -> None:
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 10
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["private_founder_values_mirrored"] is False
    for artifact in receipt["artifacts"]:
        source_path = Path(artifact["source"])
        destination = Path(artifact["destination"])
        assert source_path.is_absolute() is False
        assert ".." not in source_path.parts
        assert destination.is_file(), artifact["destination"]
        assert destination.stat().st_size == artifact["bytes"]
        destination_hash = hashlib.sha256(destination.read_bytes()).hexdigest().upper()
        assert destination_hash == artifact["sha256"]
        assert artifact["copy_sha256_matched"] is True
