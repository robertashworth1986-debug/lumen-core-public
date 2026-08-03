from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_TECHNICAL_GOV_REVIEWER_APPROVAL_STACK.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "technical_gov_reviewer_approval_stack", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_stack_routes_reviewers_and_labels_sam_receipt_historical():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "technical_gov_reviewer_approval_stack_v2"
    assert payload["status"] == (
        "TECHNICAL_GOV_REVIEWER_APPROVAL_STACK_READY_HUMAN_ACTION_REQUIRED"
    )
    assert summary["reviewer_track_count"] >= 5
    assert summary["official_data_source_count"] >= 6
    assert summary["venture_studio_deprioritized"] is True
    assert summary["technical_reviewer_first"] is True
    assert summary["sam_historical_submission_receipt_present"] is True
    assert summary["sam_historical_submission_receipt_generated_utc"].startswith(
        "2026-07-09"
    )
    assert summary["sam_current_active_status_verified"] is False
    assert summary["sam_current_status"] == (
        "historical_submission_receipt_present_current_active_status_not_verified"
    )
    assert summary["human_action_required"] is True
    assert summary["external_send_allowed_without_human"] is False
    assert summary["portal_submission_allowed_without_human"] is False
    assert summary["live_trading_allowed"] is False
    assert len(payload["approval_stack_sha256"]) == 64


def test_core_truth_records_source_specific_nonpromotion():
    module = load_module()
    payload = module.build_payload()
    metrics = payload["core_truth"]["metrics"]
    safe_claim = payload["core_truth"]["safe_technical_claim"]

    assert metrics["registered_geometry_family_count"] == 140
    assert metrics["internal_performance_champion_present"] is False
    assert metrics["compatible_adapter_route_count"] == 4
    assert metrics["direct_measured_route_count"] == 2
    assert metrics["conditioned_synthetic_route_count"] == 2
    assert metrics["baseline_comparison_count"] == 22
    assert metrics["direct_all_baseline_global_holm_positive_count"] == 0
    assert metrics["performance_rows_reviewed"] == 32608
    assert metrics["legacy_ready_rows_excluded"] == 358
    assert metrics["numeric_fallback_count"] == 0
    assert metrics["source_inventory_measured_count"] == 24
    assert metrics["source_inventory_measured_rows"] == 17081
    assert metrics["source_inventory_is_performance_evidence"] is False

    assert metrics["kuramoto_candidate_was_protocol_selected"] is False
    assert (
        metrics["kuramoto_development_selected_candidate"]
        == "lissajous_phase_paths"
    )
    assert metrics["kuramoto_holdout_count"] == 1525
    assert metrics["kuramoto_wins_vs_kalman"] == 482
    assert metrics["kuramoto_losses_or_ties_vs_kalman"] == 1043
    assert metrics["kuramoto_mean_delta_vs_kalman"] == -0.508190706
    assert metrics["kuramoto_estimated_rows_replayed"] == 15250
    assert metrics["kuramoto_registered_baseline_mean_win_count"] == 0
    assert metrics["kuramoto_registered_baseline_count"] == 6
    assert metrics["kuramoto_all_baseline_holm_gate_passed"] is False
    assert metrics["field_validation_claim_allowed"] is False
    assert metrics["real_dollar_savings_claim_allowed"] is False
    assert metrics["live_trading_allowed"] is False

    assert "not development-selected" in safe_claim
    assert "482 of 1,525" in safe_claim
    assert "mean skill delta -0.508190706" in safe_claim
    assert "bounded source-native protocol review" in safe_claim
    assert "external field-validation approval" in payload["core_truth"][
        "blocked_claims"
    ]
    assert "live trading profit" in payload["core_truth"]["blocked_claims"]


def test_routes_are_currently_bounded_and_public_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()
    tracks = {track["track_id"]: track for track in payload["reviewer_tracks"]}
    sources = {
        source["source_id"]: source
        for source in payload["official_live_data_targets"]
    }

    assert tracks["patent_counsel_and_pro_bono"]["status"] == (
        "CLOSED_ROUTE_DO_NOT_REOPEN"
    )
    assert tracks["national_lab_or_technical_reviewer"]["status"] == (
        "REAL_TECHNICAL_REVIEW_ROUTE"
    )
    assert tracks["agency_reviewer"]["status"] == (
        "CURRENT_SAM_STATUS_REVERIFY_BEFORE_ELIGIBILITY_CLAIM"
    )
    assert sources["aviation_weather_center_api"]["integration_posture"] == (
        "candidate_fast_adapter"
    )
    assert sources["faa_swim"]["integration_posture"] == "access_required"
    assert "SAM Status Support" in rendered
    assert "current active status is not verified" in lowered
    assert "Georgia PATENTS" in rendered
    assert "closed" in lowered
    assert "LANL" in rendered
    assert "FAA / aviation live-data expansion" in rendered
    assert "24/24" not in rendered
    assert "2,506,267" not in rendered
    assert "zoom.us" not in lowered
    assert "password" not in lowered
    assert "meeting id" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
