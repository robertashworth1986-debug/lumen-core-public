from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_KURAMOTO_FIELD_REPLAY_REQUEST.py"


def load_module():
    spec = importlib.util.spec_from_file_location("kuramoto_field_replay_request", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_kuramoto_brief_records_direct_measured_nonpromotion():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "kuramoto_field_replay_request_v2"
    assert summary["candidate"] == "kuramoto_phase_coupling"
    assert summary["development_selected_candidate"] == "lissajous_phase_paths"
    assert summary["candidate_was_protocol_selected"] is False
    assert summary["current_status"] == (
        "field_replay_request_blocked_source_specific_baseline_gate_failed"
    )
    assert summary["holdout_count"] == 1525
    assert summary["wins_vs_kalman"] == 482
    assert summary["losses_or_ties_vs_kalman"] == 1043
    assert summary["mean_delta_vs_kalman"] == -0.508190706
    assert summary["registered_baseline_count"] == 6
    assert summary["registered_baseline_mean_win_count"] == 0
    assert summary["registered_baseline_gate_pass_count"] == 0
    assert summary["candidate_beats_all_registered_baselines_after_holm"] is False
    assert summary["panel_row_count"] == 14704
    assert summary["source_system_count"] == 1
    assert len(summary["holdout_chain_sha256"]) == 64


def test_kuramoto_brief_blocks_request_and_preserves_future_protocol():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    request = payload["request_packet"]
    commercial = payload["commercial_boundary"]

    assert request["request_type"] == "not_a_field_replay_request"
    assert request["current_status"] == "blocked"
    assert "Do not ask" in request["one_sentence_non_ask"]
    assert len(request["reviewer_roles"]) >= 3
    assert len(request["data_required_for_future_protocol"]) >= 5
    assert len(request["baseline_controls"]) >= 5
    assert len(request["future_primary_kpis"]) >= 4
    assert len(request["protocol_review_deliverables"]) >= 6
    assert len(request["pre_review_questions"]) >= 6
    assert len(request["unlock_conditions"]) == 5
    assert summary["field_replay_request_allowed"] is False
    assert summary["manual_outreach_allowed"] is False
    assert summary["bulk_email_allowed"] is False
    assert summary["paid_protocol_review_scoping_allowed"] is True
    assert commercial["outreach"]["recipient_selected"] is False
    assert commercial["outreach"]["send_allowed"] is False
    assert commercial["outreach"]["exact_action_time_approval_required"] is True


def test_kuramoto_brief_blocks_overclaiming():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    boundary = payload["claim_boundary"]

    assert summary["internal_performance_champion_present"] is False
    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert summary["fixed_dollar_delta_sale_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False
    assert boundary["not_a_current_champion"] is True
    assert boundary["not_a_field_replay_request"] is True
    assert boundary["not_field_validation"] is True
    assert boundary["not_realized_savings"] is True
    assert "lost on mean skill" in boundary["safe_statement"]
    assert "current performance champion" in payload["no_go_claims"]


def test_kuramoto_brief_markdown_is_reviewer_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Kuramoto Nonpromotion and Protocol Redesign Brief" in rendered
    assert "Direct measured wins vs Kalman: `482/1525`" in rendered
    assert "Losses or ties vs Kalman: `1043`" in rendered
    assert "Mean skill delta vs Kalman: `-0.508190706`" in rendered
    assert "Registered baseline mean wins: `0/6`" in rendered
    assert "All-baseline Holm gate passed: `false`" in rendered
    assert "Field-replay request allowed: `false`" in rendered
    assert "Manual outreach allowed: `false`" in rendered
    assert "Paid protocol-review scoping allowed: `true`" in rendered
    assert "not an outreach packet" in lowered
    assert "24/24" not in rendered
    assert "2506267" not in rendered
    assert "Manual Email Copy" not in rendered
    assert "Packet SHA-256" in rendered
