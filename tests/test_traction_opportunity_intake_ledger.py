from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_TRACTION_OPPORTUNITY_INTAKE_LEDGER.py"


def load_module():
    spec = importlib.util.spec_from_file_location("traction_opportunity_intake_ledger", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_traction_ledger_builds_connected_and_federal_lane_queue():
    module = load_module()
    payload = module.build_payload()

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

    uspto = lanes["uspto_georgia_patents_route"]
    assert "not legal advice" in uspto["claim_boundary"]
    assert "public:georgia_patents" in uspto["source_refs"]

    protecnium = lanes["protecnium_its_infrastructure_signal"]
    assert "not a customer commitment" in protecnium["claim_boundary"]
    assert "customer-discovery" in protecnium["reviewer_action"]


def test_rendered_markdown_excludes_meeting_credentials_and_live_action_authority():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Traction Opportunity Intake Ledger" in rendered
    assert "External send without human: `false`" in rendered
    assert "Final submission without human: `false`" in rendered
    assert "No final portal action" in rendered
    assert "zoom.us" not in lowered
    assert "password" not in lowered
    assert "meeting id" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
