from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PROOF_TO_REVENUE_ENGINE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("proof_to_revenue_engine", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_proof_to_revenue_engine_promotes_manual_paid_pilot_not_overclaims():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    live_summary = json.loads(module.LIVE_DOMAIN_JSON.read_text(encoding="utf-8"))["summary"]
    expected_live_hash_verified = (
        live_summary.get("domain_deployment_state") == "LIVE_DOMAIN_HASH_VERIFIED"
        and bool(live_summary.get("live_domain_reviewer_ready"))
    )

    assert payload["schema"] == "proof_to_revenue_engine_v1"
    assert summary["live_domain_hash_verified"] is expected_live_hash_verified
    assert summary["revenue_stage"] == (
        "manual_paid_pilot_scoping_ready"
        if expected_live_hash_verified
        else "proof_stack_not_ready_for_outreach"
    )
    assert summary["manual_reviewed_outreach_allowed"] is True
    assert summary["send_without_user_review_allowed"] is False
    assert summary["bulk_email_allowed"] is False
    assert summary["field_validation_claim_allowed"] is False
    assert summary["realized_savings_claim_allowed"] is False
    assert summary["fixed_frozen_delta_price_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False
    assert summary["champion_family"] == "kuramoto_phase_coupling"
    assert summary["holdout_wins"] >= 20
    assert len(payload["proof_to_revenue_sha256"]) == 64


def test_proof_to_revenue_engine_has_targets_and_safe_email_template():
    module = load_module()
    payload = module.build_payload()
    template = payload["safe_email_template"]

    assert payload["top_manual_targets"]
    assert "Reviewer URL:" in template["body"]
    assert template["send_mode"] == "manual_review_only"
    assert "field validation or realized savings yet" in template["body"]
    dumped = json.dumps(payload).lower()
    assert "realized savings" in dumped
    assert "fixed value per frozen delta" in dumped
    assert "send_without_user_review_allowed" in dumped
    assert '"send_without_user_review_allowed": false' in dumped


def test_proof_to_revenue_markdown_answers_next_questions():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    live_hash_verified = payload["summary"]["live_domain_hash_verified"]

    assert "Proof To Revenue Engine" in rendered
    assert "Deployment Verification" in rendered
    assert "Field Validation Unlock" in rendered
    assert "What To Ask Next" in rendered
    assert f"Live domain hash verified: `{str(live_hash_verified).lower()}`" in rendered
    assert (
        "public hashes match" if live_hash_verified else "public hash verification is still pending"
    ) in rendered
