from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_KRAKEN_INSTITUTIONAL_ALPHA_GAUNTLET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("kraken_institutional_alpha_gauntlet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_institutional_gauntlet_is_ready_but_blocks_live_and_large_fund_claims():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "kraken_institutional_alpha_gauntlet_v1"
    assert payload["status"] == "INSTITUTIONAL_ALPHA_GAUNTLET_READY_LIVE_BLOCKED"
    assert summary["gauntlet_row_count"] > 0
    assert summary["large_fund_ready_count"] == 0
    assert summary["trusted_with_large_fund_now"] is False
    assert summary["global_runtime_paper"] is True
    assert summary["kraken_runtime_paper"] is True
    assert summary["global_live_orders_disabled"] is True
    assert summary["kraken_live_orders_disabled"] is True
    assert summary["order_placement_allowed"] is False
    assert summary["capital_movement_allowed"] is False
    assert summary["private_credential_use_allowed_without_human"] is False
    assert len(payload["institutional_alpha_gauntlet_sha256"]) == 64


def test_gauntlet_rows_include_capacity_stress_and_promotion_fail_reasons():
    module = load_module()
    payload = module.build_payload()

    for row in payload["gauntlet_rows"]:
        assert 0 <= row["signal_quality_score"] <= 100
        assert 0 <= row["execution_quality_score"] <= 100
        assert 0 <= row["capacity_quality_score"] <= 100
        assert 0 <= row["stress_survivability_score"] <= 100
        assert 0 <= row["replay_readiness_score"] <= 100
        assert 0 <= row["institutional_alpha_score"] <= 100
        assert row["capacity"]["large_fund_capacity_proven"] is False
        assert row["capacity"]["large_fund_gap"]
        assert row["promotion_fail_reasons"]
        assert row["allowed_next_step"] == "paper_replay_and_slippage_stress_only"
        assert row["live_order_allowed"] is False
        assert len(row["gauntlet_row_sha256"]) == 64


def test_rendered_gauntlet_is_public_safe_and_not_an_advice_or_live_packet():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Kraken Institutional Alpha Gauntlet" in rendered
    assert "Large-fund ready now: `0`" in rendered
    assert "Trusted with large fund now: `false`" in rendered
    assert "Order placement allowed: `false`" in rendered
    assert "Capital movement allowed: `false`" in rendered
    assert "not investment advice" in lowered
    assert "does not authorize live trading" in lowered
    assert "password" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
    assert "sk-" not in lowered
