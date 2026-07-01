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


def test_operator_context_preserves_current_champion_and_domain_state():
    module = load_module()
    payload = module.build_payload()
    truth = payload["truth_state"]
    domain = payload["live_domain"]

    assert payload["schema"] == "luma_operator_context_v1"
    assert truth["current_champion"] == "kuramoto_phase_coupling"
    assert truth["named_baseline"] == "kalman_filter"
    assert truth["holdout_wins"] == truth["holdout_count"]
    assert truth["estimated_rows_replayed"] >= 1_000_000
    assert truth["buyer_authorized_field_replay_request_ready"] is True
    assert truth["field_validation_claim_allowed"] is False
    assert truth["real_dollar_savings_claim_allowed"] is False
    assert domain["reviewer_ready"] is True
    assert domain["required_remote_stale_or_missing_count"] == 0
    assert "PUSH_PROOF_FEEDS_TO_VPS.ps1" in domain["safe_deploy_command"]
    assert len(payload["context_sha256"]) == 64


def test_operator_context_exposes_source_gaps_without_plaintext_secrets():
    module = load_module()
    payload = module.build_payload()
    source_breadth = payload["source_breadth"]
    provider_gaps = source_breadth["provider_gaps"]
    sources = {row["source"] for row in provider_gaps}

    assert source_breadth["measured_coverage_pct"] == 100.0
    assert source_breadth["fresh_http_measured_sources_total"] >= 19
    assert source_breadth["fresh_http_enabled_sources_total"] >= 23
    assert source_breadth["fresh_http_total_measured_rows"] >= 500
    assert source_breadth["live_context_replay_rows_evaluated"] >= 150
    assert "EIA" in source_breadth["fresh_http_measured_source_names"]
    assert "NOAA_NCEI" in source_breadth["fresh_http_measured_source_names"]
    assert "EPA_AQS" in sources
    assert "NREL" in sources
    assert "THE_ODDS_API" in sources

    dumped = json.dumps(payload).lower()
    assert "plaintext_secret" not in dumped
    assert "private_key_material" not in dumped
    assert "api_key_value" not in dumped
    assert "api_secret_value" not in dumped


def test_operator_context_keeps_outreach_manual_and_claims_bounded():
    module = load_module()
    payload = module.build_payload()
    outreach = payload["outreach"]
    dollar_gate = payload["dollar_gate"]

    assert outreach["recommended_first_buyer"] == "EPRI AI for Power / Incubatenergy Labs"
    assert outreach["manual_reviewed_outreach_allowed"] is True
    assert outreach["send_without_user_review_allowed"] is False
    assert "Operator must review" in outreach["send_gate"]
    assert dollar_gate["realized_savings_allowed"] is False
    assert dollar_gate["field_validation_required_for_real_dollars"] is True
    assert "buyer-authorized field replay" in dollar_gate["safe_line"]


def test_operator_context_markdown_contains_next_actions_and_prompt():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Luma Operator Context" in rendered
    assert "Current Truth" in rendered
    assert "Provider gaps to fix" in rendered
    assert "Replay Lanes" in rendered
    assert "First Outreach Lane" in rendered
    assert "Long-Arc Operator Prompt" in rendered
    assert "Operate LumenCore as a measurement-first proof-to-pilot platform" in rendered
