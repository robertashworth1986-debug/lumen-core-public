from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LUMA_OPERATOR_CONTEXT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("luma_operator_context", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_operator_context_preserves_nonpromotion_and_domain_state():
    module = load_module()
    payload = module.build_payload()
    truth = payload["truth_state"]
    domain = payload["live_domain"]

    assert payload["schema"] == "luma_operator_context_v2"
    assert truth["internal_performance_champion_present"] is False
    assert truth["current_champion"] is None
    assert truth["measured_reference_candidate"] == "kuramoto_phase_coupling"
    assert truth["development_selected_candidate"] == "lissajous_phase_paths"
    assert truth["candidate_was_protocol_selected"] is False
    assert truth["named_baseline"] == "kalman_local_linear_trend"
    assert truth["holdout_wins"] == 482
    assert truth["holdout_count"] == 1525
    assert truth["mean_delta_vs_named_baseline"] == -0.508191
    assert truth["registered_baseline_mean_win_count"] == 0
    assert truth["registered_baseline_count"] == 6
    assert truth["candidate_beats_all_registered_baselines_after_holm"] is False
    assert truth["buyer_authorized_field_replay_request_ready"] is False
    assert truth["field_validation_claim_allowed"] is False
    assert truth["real_dollar_savings_claim_allowed"] is False

    assert domain["feed_only_deploy_ready"] is True
    assert domain["local_ready"] is True
    assert domain["reviewer_ready"] is False
    assert domain["required_remote_hash_match_count"] < domain["required_feed_count"]
    assert domain["required_remote_stale_or_missing_count"] > 0
    assert "PUSH_PROOF_FEEDS_TO_VPS.ps1" in domain["safe_deploy_command"]
    assert len(payload["context_sha256"]) == 64


def test_operator_context_separates_source_inventory_and_replay_evidence():
    module = load_module()
    payload = module.build_payload()
    truth = payload["truth_state"]
    lanes = payload["locked_replay_lanes"]

    assert truth["geometry_inventory_measured_source_count"] == 24
    assert truth["geometry_inventory_measured_row_count"] == 17081
    assert truth["geometry_inventory_is_performance_evidence"] is False
    assert truth["compatibility_route_count"] == 4
    assert truth["direct_measured_route_count"] == 2
    assert truth["conditioned_synthetic_route_count"] == 2
    assert truth["baseline_comparison_count"] == 22
    assert truth["raw_candidate_win_count"] == 10
    assert truth["direct_all_baseline_global_holm_positive_count"] == 0
    assert truth["performance_rows_reviewed"] == 32608
    assert truth["legacy_ready_rows_excluded"] == 358
    assert truth["numeric_fallback_count"] == 0

    assert len(lanes) == 4
    assert {row["evidence_mode"] for row in lanes} == {
        "direct_measured_replay",
        "source_conditioned_synthetic_stress",
    }
    assert sum(row["global_holm_positive_count"] for row in lanes) == 0


def test_operator_context_exposes_source_gaps_without_plaintext_secrets():
    module = load_module()
    payload = module.build_payload()
    source_breadth = payload["source_breadth"]
    provider_gaps = source_breadth["provider_gaps"]
    sources = {row["source"] for row in provider_gaps}

    assert source_breadth["measured_coverage_pct"] == 100.0
    assert source_breadth["fresh_http_measured_sources_total"] == 25
    assert source_breadth["fresh_http_enabled_sources_total"] == 29
    assert source_breadth["fresh_http_total_measured_rows"] == 2580
    assert source_breadth["live_context_replay_rows_evaluated"] == 32608
    assert "EIA" in source_breadth["fresh_http_measured_source_names"]
    assert "NOAA_NCEI" in source_breadth["fresh_http_measured_source_names"]
    assert "EPA_AQS" in sources
    assert "NREL" in sources
    assert "THE_ODDS_API" in source_breadth[
        "fresh_http_failed_or_thin_source_names"
    ]

    dumped = json.dumps(payload).lower()
    assert "plaintext_secret" not in dumped
    assert "private_key_material" not in dumped
    assert "api_key_value" not in dumped
    assert "api_secret_value" not in dumped


def test_operator_context_keeps_outreach_closed_and_offer_bounded():
    module = load_module()
    payload = module.build_payload()
    outreach = payload["outreach"]
    dollar_gate = payload["dollar_gate"]

    assert outreach["recommended_first_buyer"] is None
    assert outreach["manual_reviewed_outreach_allowed"] is False
    assert outreach["send_without_user_review_allowed"] is False
    assert outreach["paid_protocol_review_scoping_allowed"] is True
    assert outreach["top_contact_lane"]["routing_status"] == (
        "inbound_only_no_new_outreach"
    )
    assert outreach["top_contact_lane"]["send_now_allowed"] is False
    assert "No send is authorized" in outreach["send_gate"]
    assert "exact action-time approval" in outreach["send_gate"]
    assert dollar_gate["realized_savings_allowed"] is False
    assert dollar_gate["field_validation_required_for_real_dollars"] is True
    assert "bounded source-native benchmark" in dollar_gate["safe_line"]


def test_operator_context_markdown_contains_truth_and_next_actions():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Luma Operator Context" in rendered
    assert "Current Truth" in rendered
    assert "Internal performance champion present: `false`" in rendered
    assert "Current performance champion: `none`" in rendered
    assert "Paired-day wins: `482/1525`" in rendered
    assert "Mean skill delta: `-0.508191`" in rendered
    assert "Direct measured routes: `2`" in rendered
    assert "Conditioned-synthetic routes: `2`" in rendered
    assert "Direct all-baseline global promotions: `0`" in rendered
    assert "Geometry source inventory: `24` measured sources / `17081` rows" in rendered
    assert "Provider gaps to fix" in rendered
    assert "Replay Lanes" in rendered
    assert "Protocol Review Lane" in rendered
    assert "Long-Arc Operator Prompt" in rendered
    assert "measurement-first evidence and benchmark" in rendered
    assert "reviewer-safe proof that survives hostile reading" in rendered
    assert "24/24" not in rendered
    assert "current internal champion" not in lowered
    assert len(payload["next_10_actions"]) == 10
