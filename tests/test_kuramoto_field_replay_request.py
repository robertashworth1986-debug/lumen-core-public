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


def test_kuramoto_field_replay_request_summarizes_strongest_current_candidate():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "kuramoto_field_replay_request_v1"
    assert summary["candidate"] == "kuramoto_phase_coupling"
    assert summary["lane"] == "wave_resonance_timing"
    assert summary["current_status"] == "ready_to_request_field_replay_not_yet_field_validated"
    assert summary["holdout_count"] >= 20
    assert summary["wins_vs_kalman"] >= 20
    assert summary["estimated_rows_replayed"] >= 2_000_000
    assert summary["source_system_count"] >= 4
    assert len(summary["holdout_chain_sha256"]) == 64
    assert summary["manual_outreach_allowed"] is True
    assert summary["bulk_email_allowed"] is False


def test_kuramoto_field_replay_request_has_actionable_validation_protocol():
    module = load_module()
    payload = module.build_payload()
    request = payload["request_packet"]

    assert "pre-registered holdout windows" in request["one_sentence_ask"]
    assert len(request["buyer_roles"]) >= 4
    assert len(request["data_required"]) >= 5
    assert len(request["baseline_controls"]) >= 5
    assert "kalman_filter" in request["baseline_controls"]
    assert len(request["primary_kpis"]) >= 4
    assert len(request["deliverables"]) >= 6
    assert len(request["pre_call_questions"]) >= 6
    assert request["field_replay_request"]["minimum_holdout_windows"] == 20
    assert request["field_replay_request"]["current_status"] == "ready_to_request_field_replay_not_yet_field_validated"


def test_kuramoto_field_replay_request_blocks_overclaiming():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    boundary = payload["claim_boundary"]
    text = module.render_markdown(payload).lower()

    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert summary["fixed_dollar_delta_sale_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False

    assert boundary["not_field_validation"] is True
    assert boundary["not_realized_savings"] is True
    assert boundary["not_fixed_dollar_delta_value"] is True
    assert boundary["not_live_trading"] is True
    assert "does not prove external operational performance" in boundary["safe_statement"]
    assert "not a completed field-validation claim" in text
    assert "field-validation claim allowed: `false`" in text
    assert "realized savings claim allowed: `false`" in text
    assert "$10k per frozen delta" in payload["no_go_claims"]


def test_kuramoto_field_replay_markdown_is_dashboard_ready():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Kuramoto Field Replay Request" in rendered
    assert "Internal holdout wins vs Kalman: `24/24`" in rendered
    assert "Estimated rows replayed: `2506267`" in rendered
    assert "Source systems: `4`" in rendered
    assert "Manual Email Copy" in rendered
    assert "Claim Boundary" in rendered
    assert "Packet SHA-256" in rendered
