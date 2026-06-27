from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FIELD_VALIDATED_DOLLAR_CLAIM_LADDER.py"


def load_module():
    spec = importlib.util.spec_from_file_location("field_validated_dollar_claim_ladder", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_sector_math_uses_correct_basis_point_values():
    module = load_module()

    assert module.gross_value(1_000_000_000, 0.001) == 10_000
    assert module.windowed_value(10_000, 3) == 2_500
    assert module.gross_value(1_000_000_000, 0.01) == 100_000
    assert module.windowed_value(100_000, 3) == 25_000


def test_claim_ladder_keeps_current_real_savings_gate_closed():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "field_validated_dollar_claim_ladder_v1"
    assert payload["direct_answer"]["can_claim_real_savings_right_now"] is False
    assert payload["current_truth"]["field_validated_savings_claim_allowed_now"] is False
    assert payload["current_truth"]["realized_customer_or_government_savings_allowed_now"] is False
    assert payload["current_truth"]["bounded_estimated_value_claim_allowed_now"] is True
    assert payload["current_truth"]["allowed_estimated_annual_value_usd"] > 0
    assert len(payload["claim_ladder_sha256"]) == 64


def test_capture_table_converts_current_safe_estimate_without_claiming_revenue():
    module = load_module()
    payload = module.build_payload()
    annual = payload["current_truth"]["allowed_estimated_annual_value_usd"]
    rows = {row["capture_rate_pct"]: row for row in payload["capture_from_current_safe_estimate"]}

    assert rows[5.0]["annual_contract_surface_usd"] == round(annual * 0.05, 2)
    assert rows[5.0]["first_3_months_contract_surface_usd"] == round(annual * 0.05 * 0.25, 2)
    assert "revenue requires" in rows[5.0]["boundary"]


def test_ladder_language_requires_field_validation_before_posting_savings_claims():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    text = rendered.lower()

    assert "real savings claim right now: `false`" in text
    assert "field validated savings allowed now: `false`" in text
    assert "not realized savings" in text
    assert "buyer-authorized" in text
    assert "locked baseline" in text
    assert "guaranteed roi" in text
    assert "field-validated avoided-cost claim" in rendered


def test_strongest_family_is_field_replay_request_not_customer_savings_claim():
    module = load_module()
    payload = module.build_payload()
    family = payload["strongest_alpha_flow_family"]

    assert family["family_id"]
    assert family["field_validation_claim_allowed"] is False
    assert family["real_dollar_savings_claim_allowed"] is False
    assert "not yet a customer savings claim" in family["plain_english"]
