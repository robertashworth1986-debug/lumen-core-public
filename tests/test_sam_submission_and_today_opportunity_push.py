from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_SAM_SUBMISSION_AND_TODAY_OPPORTUNITY_PUSH.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sam_submission_and_today_opportunity_push", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_sam_submission_and_today_push_records_real_sent_actions():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "sam_submission_and_today_opportunity_push_v1"
    assert payload["status"] == "SAM_SUBMITTED_AND_TODAY_OPPORTUNITY_PUSH_READY"
    assert payload["summary"]["sam_registration_submitted"] is True
    assert payload["summary"]["sam_confirmation_email_received"] is True
    assert payload["summary"]["same_day_external_push_count"] == 3
    assert payload["summary"]["same_day_federal_email_push_count"] == 2
    assert payload["summary"]["portal_submission_completed_count"] == 1
    assert payload["summary"]["air_force_aac_rfi_sent"] is True
    assert payload["summary"]["fhwa_tsmo_capability_note_sent"] is True
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_portal_submission_allowed_without_human"] is False
    assert len(payload["today_push_sha256"]) == 64


def test_remaining_gates_keep_full_proposal_and_portal_boundaries():
    module = load_module()
    payload = module.build_payload()
    gates = {gate["gate_id"]: gate for gate in payload["remaining_gates"]}
    pushes = {push["push_id"]: push for push in payload["submitted_pushes"]}

    assert pushes["sam_entity_renewal_submission"]["status"] == "SUBMITTED_CONFIRMATION_RECEIVED"
    assert pushes["air_force_aac_rfi_capability_statement"]["gmail_sent_id"] == "19f48d5933c9b5cb"
    assert pushes["fhwa_tsmo_capability_intent_note"]["status"] == "SENT_AS_CAPABILITY_NOTE_NOT_FINAL_PROPOSAL"
    assert "not a final proposal" in " ".join(pushes["fhwa_tsmo_capability_intent_note"]["claim_boundary"]).lower()
    assert "fhwa_tsmo_full_proposal" in gates
    assert "dsip_missionweave_phase1" in gates
    assert "nsf_seed_fund_pitch_or_invited_proposal" in gates
    for gate in payload["remaining_gates"]:
        assert gate["blocked_until"]


def test_rendered_today_push_is_public_safe_and_no_overclaim():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "SAM Submission And Today Opportunity Push" in rendered
    assert "SAM registration submitted: `true`" in rendered
    assert "No FHWA final proposal was represented as submitted." in rendered
    assert "No FedRAMP, ATO, field validation, realized savings, or award status was claimed." in rendered
    assert "External send without human: `false`" in rendered
    assert "Final portal submission without human: `false`" in rendered
    assert "zoom.us" not in lowered
    assert "password" not in lowered
    assert "meeting id" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
