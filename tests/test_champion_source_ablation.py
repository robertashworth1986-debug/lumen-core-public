from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CHAMPION_SOURCE_ABLATION.py"


def load_module():
    spec = importlib.util.spec_from_file_location("champion_source_ablation", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_champion_source_ablation_builds_leave_one_source_out():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "champion_source_ablation_v1"
    assert summary["champion_family"] == "kuramoto_phase_coupling"
    assert summary["lane"] == "wave_resonance_timing"
    assert summary["named_baseline"] == "kalman_filter"
    assert summary["holdout_count"] >= 24
    assert summary["wins_vs_named_baseline"] == summary["holdout_count"]
    assert summary["source_system_count"] >= 4
    assert summary["source_ablation_count"] == summary["source_system_count"]
    assert summary["source_ablation_pass_count"] == summary["source_ablation_count"]
    assert summary["all_leave_one_source_out_passed"] is True
    assert summary["min_delta_vs_named_baseline"] > 0
    assert len(payload["source_ablation_sha256"]) == 64


def test_champion_source_ablation_has_source_cards_and_boundaries():
    module = load_module()
    payload = module.build_payload()
    sources = {row["source_system"] for row in payload["source_system_cards"]}

    assert {"energy_grid", "market_data"}.issubset(sources)
    assert len(payload["leave_one_source_out"]) >= 4
    for row in payload["leave_one_source_out"]:
        assert row["passes_positive_margin_after_withholding"] is True
        assert row["holdout_count"] >= 1
        assert row["min_delta_vs_named_baseline"] > 0
        assert "internal robustness" in row["claim_gate"]

    dumped = json.dumps(payload).lower()
    assert "not field validation" in dumped
    assert "not realized savings" in dumped
    assert "fixed frozen-delta price" in dumped


def test_champion_source_ablation_keeps_external_claim_gates_closed():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert summary["fixed_frozen_delta_price_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False


def test_champion_source_ablation_markdown_is_reviewer_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Champion Source Ablation" in rendered
    assert "Leave-One-Source-Out Table" in rendered
    assert "Field-validation claim allowed: `false`" in rendered
    assert "All leave-one-source-out passed: `true`" in rendered
