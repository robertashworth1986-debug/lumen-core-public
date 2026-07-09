from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_TECHNICAL_GOV_REVIEWER_APPROVAL_STACK.py"


def load_module():
    spec = importlib.util.spec_from_file_location("technical_gov_reviewer_approval_stack", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_stack_routes_to_real_technical_government_and_ip_reviewers():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "technical_gov_reviewer_approval_stack_v1"
    assert payload["status"] == "TECHNICAL_GOV_REVIEWER_APPROVAL_STACK_READY_HUMAN_ACTION_REQUIRED"
    assert payload["summary"]["reviewer_track_count"] >= 5
    assert payload["summary"]["official_data_source_count"] >= 6
    assert payload["summary"]["venture_studio_deprioritized"] is True
    assert payload["summary"]["technical_reviewer_first"] is True
    assert payload["summary"]["sam_submission_confirmed"] is True
    assert payload["summary"]["sam_renewal_status"] == "submitted_confirmation_received_monitor_active_status"
    assert payload["summary"]["human_action_required"] is True
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["portal_submission_allowed_without_human"] is False
    assert payload["summary"]["live_trading_allowed"] is False
    assert len(payload["approval_stack_sha256"]) == 64


def test_core_truth_preserves_champion_metrics_and_blocks_overclaims():
    module = load_module()
    payload = module.build_payload()
    metrics = payload["core_truth"]["metrics"]

    assert metrics["kuramoto_holdout_count"] >= 20
    assert metrics["kuramoto_wins_vs_kalman"] >= 20
    assert metrics["kuramoto_estimated_rows_replayed"] >= 2_000_000
    assert metrics["registered_geometry_family_count"] >= 100
    assert metrics["field_validation_claim_allowed"] is False
    assert metrics["real_dollar_savings_claim_allowed"] is False
    assert metrics["live_trading_allowed"] is False
    assert "external field-validation approval" in payload["core_truth"]["blocked_claims"]
    assert "live trading profit" in payload["core_truth"]["blocked_claims"]


def test_sam_email_and_faa_routes_are_human_gated_and_public_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()
    tracks = {track["track_id"]: track for track in payload["reviewer_tracks"]}
    sources = {source["source_id"]: source for source in payload["official_live_data_targets"]}

    assert tracks["patent_counsel_and_pro_bono"]["status"] == "URGENT_REAL_IP_ROUTE"
    assert tracks["national_lab_or_technical_reviewer"]["status"] == "REAL_TECHNICAL_REVIEW_ROUTE"
    assert tracks["agency_reviewer"]["status"] == "POST_SAM_AGENCY_REVIEWER_ROUTE"
    assert sources["aviation_weather_center_api"]["integration_posture"] == "candidate_fast_adapter"
    assert sources["faa_swim"]["integration_posture"] == "access_required"
    assert "SAM Renewal Support" in rendered
    assert "Georgia PATENTS" in rendered
    assert "LANL" in rendered
    assert "FAA / aviation live-data expansion" in rendered
    assert "zoom.us" not in lowered
    assert "password" not in lowered
    assert "meeting id" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
