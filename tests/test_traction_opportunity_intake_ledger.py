from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_TRACTION_OPPORTUNITY_INTAKE_LEDGER.py"
CURRENT_RESPONSE_JSON = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json"
)
MISSIONWEAVE_GATE_JSON = (
    ROOT
    / "grant_submissions"
    / "DLA26BZ03_NV011_MissionWeave"
    / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("traction_opportunity_intake_ledger", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_traction_ledger_builds_connected_and_federal_lane_queue():
    module = load_module()
    payload = module.build_payload()
    response_summary = json.loads(
        CURRENT_RESPONSE_JSON.read_text(encoding="utf-8")
    )["summary"]
    missionweave = json.loads(MISSIONWEAVE_GATE_JSON.read_text(encoding="utf-8"))

    assert payload["schema"] == "traction_opportunity_intake_ledger_v1"
    assert payload["status"] == "TRACTION_INTAKE_READY_HUMAN_ACTION_REQUIRED"
    assert payload["summary"]["lane_count"] >= 18
    assert payload["summary"]["top_priority_count"] >= 10
    assert payload["summary"]["gmail_reference_count"] >= 11
    assert payload["summary"]["sweetspot_reference_count"] >= 8
    assert payload["summary"]["public_reference_count"] >= 14
    assert payload["summary"]["human_action_required"] is True
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_submission_allowed_without_human"] is False
    assert (
        payload["summary"]["current_response_record_count"]
        == response_summary["record_count"]
    )
    assert (
        payload["summary"]["current_immediate_human_action_count"]
        == response_summary["immediate_human_action_count"]
    )
    assert (
        payload["summary"]["current_do_not_duplicate_send_count"]
        == response_summary["do_not_duplicate_send_count"]
    )
    assert payload["summary"]["current_state_supersedes_legacy_when_present"] is True
    assert payload["summary"]["current_response_queue_count"] == response_summary["record_count"]
    assert payload["summary"]["missionweave_passed_gate_count"] == 13
    assert payload["summary"]["missionweave_open_gate_count"] == 37
    assert payload["summary"]["missionweave_required_gate_count"] == 50
    assert payload["summary"]["missionweave_submission_ready_for_human_click"] is False
    assert payload["missionweave_action_gate"]["gate_sha256"] == missionweave["gate_sha256"]
    assert len(payload["ledger_sha256"]) == 64


def test_priority_lanes_keep_expected_statuses_and_claim_boundaries():
    module = load_module()
    payload = module.build_payload()
    lanes = {lane["lane_id"]: lane for lane in payload["lanes"]}

    assert lanes["sam_registration_external_validation_watch"]["status"] == "SUBMITTED_EXTERNAL_VALIDATION_PENDING"
    assert lanes["lanl_vision_licensing_followup"]["status"] == "WAITING_POC_RETURN"
    assert lanes["uspto_georgia_patents_route"]["status"] == "PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED"
    assert lanes["protecnium_its_infrastructure_signal"]["status"] == "CUSTOMER_DISCOVERY_SIGNAL_ONLY"
    assert lanes["evtit_blackdog_inkind"]["status"] == "RESET_NOTE_SENT_TECH_REVIEW_PENDING"
    assert lanes["lvlup_first_check"]["status"] == "WAITING_REVIEW"
    assert lanes["darpa_dice_full_submission"]["status"] == "FULL_PROPOSAL_SPRINT"
    assert lanes["fhwa_tsmo_data_initiative"]["status"] == "PHASE_I_TECH_VOLUME"
    assert lanes["nasa_data_center_rfi"]["status"] == "RFI_RESPONSE_PREP"
    assert lanes["openai_build_week_prooflock"]["status"] == (
        "PROJECT_CORE_VERIFIED_EXTERNAL_SUBMISSION_FIELDS_OPEN"
    )
    assert lanes["patent_deadline_counsel"]["status"] == "PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED"

    for lane in payload["lanes"]:
        assert lane["human_gate_required"] is True
        assert len(lane["lane_sha256"]) == 64
        assert lane["claim_boundary"]
        assert "Human" in lane["human_gate"]


def test_latest_response_lanes_are_claim_bounded_and_actionable():
    module = load_module()
    payload = module.build_payload()
    lanes = {lane["lane_id"]: lane for lane in payload["lanes"]}

    sam = lanes["sam_registration_external_validation_watch"]
    assert sam["priority"] == 0
    assert "Submitted is not Active" in sam["claim_boundary"]
    assert "DLA" in sam["reviewer_action"]

    lanl = lanes["lanl_vision_licensing_followup"]
    assert "no LANL license" in lanl["claim_boundary"]
    assert "Mike Erickson" in " ".join(lanl["traction_evidence"])
    assert lanl["current_response_control"]["state"] == "OUTBOUND_SENT_RESPONSE_PENDING"
    assert lanl["current_response_control"]["do_not_duplicate_send"] is True

    uspto = lanes["uspto_georgia_patents_route"]
    assert "not legal advice" in uspto["claim_boundary"]
    assert "public:georgia_patents" in uspto["source_refs"]

    protecnium = lanes["protecnium_its_infrastructure_signal"]
    assert "not a customer commitment" in protecnium["claim_boundary"]
    assert "customer-discovery" in protecnium["reviewer_action"]

    build_week = lanes["openai_build_week_prooflock"]
    assert build_week["priority"] == 2
    assert "2026-07-21 17:00 Pacific" in build_week["deadline_or_gate"]
    assert "/feedback Session ID" in build_week["reviewer_action"]
    assert "not proof of Devpost registration" in build_week["claim_boundary"]
    assert "gmail:19f71ed715ce0c9f" in build_week["source_refs"]


def test_current_queue_and_effective_states_prevent_stale_or_duplicate_actions():
    module = load_module()
    payload = module.build_payload()
    current = {
        row["lane_id"]: row
        for row in payload["current_response_control"]["records"]
    }
    lanes = {lane["lane_id"]: lane for lane in payload["lanes"]}

    nashville = current["nashville_ec_takeoff_fall_2026"]
    assert nashville["deadline"] == "2026-07-17T23:59:00-05:00"
    assert nashville["send_now"] is False
    assert nashville["do_not_duplicate_send"] is True
    assert nashville["decision"] == "COMPLETE_PORTAL_BEFORE_CONFIRMED_CLOSE_NO_DUPLICATE_EMAIL"

    lvlup = current["lvlup_optional_paid_event"]
    assert lvlup["state"] == "WRITTEN_NO_SPONSOR_SPEND_INDEPENDENT_REVIEW_CONFIRMED"
    assert lvlup["send_now"] is False
    assert lvlup["related_legacy_lane_ids"] == ["lvlup_first_check"]
    assert lanes["lvlup_first_check"]["related_current_response_controls"][0]["lane_id"] == lvlup["lane_id"]
    assert lanes["lvlup_first_check"]["effective_status"] == lvlup["state"]
    assert lanes["lvlup_first_check"]["effective_source"].endswith(
        "#related:lvlup_optional_paid_event"
    )

    missionweave = lanes["dla_missionweave_sbir"]
    assert missionweave["effective_status"] == "PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN"
    assert missionweave["current_action_gate"]["passed_gate_count"] == 13
    assert missionweave["current_action_gate"]["open_gate_count"] == 37
    assert missionweave["current_action_gate"]["submission_ready_for_human_click"] is False
    assert "July 22, 2026 at 12:00 p.m. Eastern Time" in missionweave["effective_deadline_or_gate"]

    serialized = json.dumps(payload).lower()
    assert "one-time-password" not in serialized
    assert "password" not in serialized
    assert all(len(row["record_sha256"]) == 64 for row in current.values())


def test_rendered_markdown_excludes_meeting_credentials_and_live_action_authority():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()
    response_control = json.loads(CURRENT_RESPONSE_JSON.read_text(encoding="utf-8"))
    current_decisions = {
        row["decision"]
        for row in response_control["records"]
        if isinstance(row.get("decision"), str) and row["decision"]
    }

    assert "Traction Opportunity Intake Ledger" in rendered
    assert "Current Response Overlay" in rendered
    assert "Current Response Queue" in rendered
    assert "Legacy Intake Queue With Effective-State Controls" in rendered
    assert "supersedes a legacy lane status" in rendered
    assert current_decisions
    assert all(decision in rendered for decision in current_decisions)
    assert "SEND_EXISTING_GMAIL_DRAFT_AFTER_EXACT_GATE" not in rendered
    lanl_section = rendered.split("### 2. LANL VISION licensing opportunity follow-up", 1)[1].split("### 2.", 1)[0]
    assert lanl_section.index("Current response state") < lanl_section.index("- Evidence:")
    assert "External send without human: `false`" in rendered
    assert "Final submission without human: `false`" in rendered
    assert "MissionWeave gates: `13/50` passed; `37` open" in rendered
    assert "2026-07-17T23:59:00-05:00" in rendered
    assert "No final portal action" in rendered
    assert "zoom.us" not in lowered
    assert "password" not in lowered
    assert "meeting id" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
