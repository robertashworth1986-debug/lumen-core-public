from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_VENTURE_STUDIO_TERMS_GUARDRAIL_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("venture_studio_terms_guardrail_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_venture_studio_guardrail_is_ready_for_counsel_review():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "venture_studio_terms_guardrail_packet_v1"
    assert payload["status"] == "VENTURE_STUDIO_TERMS_GUARDRAIL_READY_COUNSEL_REVIEW_REQUIRED"
    assert summary["terms_signal_count"] == 4
    assert summary["diligence_question_count"] == 8
    assert summary["counterproposal_count"] == 4
    assert summary["customer_segment_count"] == 5
    assert summary["commercial_offer_count"] == 5
    assert summary["evtit_workstream_count"] == 6
    assert summary["reviewer_gate_clear"] is True
    assert summary["unsafe_secret_count"] == 0
    assert summary["unsafe_claim_count"] == 0
    assert summary["counsel_review_required"] is True
    assert len(payload["venture_studio_terms_guardrail_sha256"]) == 64


def test_venture_studio_guardrail_preserves_yc_benchmark_and_questions():
    module = load_module()
    payload = module.build_payload()
    question_ids = {row["question_id"] for row in payload["diligence_questions"]}
    counter_ids = {row["counter_id"] for row in payload["safe_counterproposals"]}

    assert payload["yc_benchmark"]["standard_deal_source"] == "https://www.ycombinator.com/deal"
    assert "500k" in payload["yc_benchmark"]["public_terms_summary"].lower()
    assert "7%" in payload["yc_benchmark"]["public_terms_summary"]
    assert {"equity_vesting", "cash_budget", "ip_ownership", "funding_support"}.issubset(question_ids)
    assert {"paid_credibility_sprint", "milestone_equity_option", "yc_parallel_path"}.issubset(counter_ids)
    assert payload["position"]["call_posture"] == "Interested, not committed."


def test_venture_studio_guardrail_blocks_terms_cash_and_claims():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert summary["equity_terms_accepted"] is False
    assert summary["cash_commitment_accepted"] is False
    assert summary["services_terms_accepted"] is False
    assert summary["partnership_claimed"] is False
    assert summary["investment_claimed"] is False
    assert summary["funding_intro_committed"] is False
    assert summary["external_send_allowed_without_human"] is False
    assert summary["pricing_commitment_allowed_without_human"] is False
    assert summary["private_file_share_allowed_without_human"] is False
    assert "Venture Studio Terms Guardrail Packet" in rendered
    assert "Equity terms accepted: `false`" in rendered
    assert "api_key" not in lowered
    assert "client_secret" not in lowered
    assert "refresh_token" not in lowered
    assert "password" not in lowered
