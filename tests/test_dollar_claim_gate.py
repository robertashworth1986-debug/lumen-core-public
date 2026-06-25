from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_DOLLAR_CLAIM_GATE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dollar_claim_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dollar_claim_gate_promotes_only_live_measured_lanes(tmp_path, monkeypatch):
    module = load_module()
    pack = tmp_path / "pack.json"
    panel = tmp_path / "panel.json"
    key_gate = tmp_path / "keys.json"

    pack.write_text(
        json.dumps(
            {
                "live_measured_top_lanes": [
                    {
                        "source": "EIA",
                        "sector": "power_grid",
                        "constraint": "frequency_stability",
                        "generated_utc": "2026-06-21T00:00:00+00:00",
                        "primary_live_evidence": True,
                        "measured_source": True,
                        "estimated_hourly_value_usd": 12500,
                        "estimated_daily_value_usd": 300000,
                        "estimated_annual_value_usd": 109500000,
                        "baseline_loss_rate_usd_per_hour": 250000,
                        "optimization_gain_pct": 5,
                    },
                    {
                        "source": "SIM_ONLY",
                        "sector": "synthetic_control",
                        "constraint": "toy",
                        "generated_utc": "2026-06-21T00:00:00+00:00",
                        "primary_live_evidence": False,
                        "measured_source": False,
                        "estimated_hourly_value_usd": 999999,
                        "estimated_annual_value_usd": 8759991240,
                        "baseline_loss_rate_usd_per_hour": 1000000,
                        "optimization_gain_pct": 10,
                    },
                ],
                "context_only_lanes": [
                    {
                        "source": "FEDWIRE_OPS",
                        "sector": "financial_market_infra",
                        "constraint": "settlement_window_integrity",
                        "generated_utc": "2026-06-21T00:00:00+00:00",
                        "primary_live_evidence": False,
                        "measured_source": False,
                        "estimated_hourly_value_usd": 3000000,
                        "estimated_annual_value_usd": 26280000000,
                        "baseline_loss_rate_usd_per_hour": 3000000,
                        "optimization_gain_pct": 20,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    panel.write_text(
        json.dumps({"headline": {"primary_evidence_mode": "live_measured_delta_rows", "live_measured_source_row_count": 1}}),
        encoding="utf-8",
    )
    key_gate.write_text(json.dumps({"summary": {"configured_providers": 3}}), encoding="utf-8")

    monkeypatch.setattr(module, "MULTI_ASSET_PACK", pack)
    monkeypatch.setattr(module, "LIVE_BREADTH_PANEL", panel)
    monkeypatch.setattr(module, "KEY_GATE", key_gate)

    payload = module.build_payload()

    assert payload["summary"]["allowed_estimated_value_claims"] == 1
    assert payload["summary"]["large_estimated_signal_claims"] == 1
    assert payload["summary"]["allowed_estimated_hourly_value_usd"] == 12500
    assert payload["summary"]["blocked_context_only_annual_value_usd"] == 26280000000
    assert payload["context_only_or_blocked_lanes"]
    assert "bounded estimated value" in payload["estimated_value_lanes"][0]["allowed_language"]
    assert "Do not promote the context-only annual figure" in "\n".join(payload["blocked_claim_language"])


def test_market_and_sports_lanes_are_never_profit_or_wagering_claims():
    module = load_module()

    market = module.lane_gate(
        {
            "source": "KRAKEN",
            "sector": "crypto_market",
            "generated_utc": "2026-06-21T00:00:00+00:00",
            "primary_live_evidence": True,
            "measured_source": True,
            "estimated_hourly_value_usd": 100,
            "estimated_annual_value_usd": 876000,
            "baseline_loss_rate_usd_per_hour": 1000,
            "optimization_gain_pct": 10,
        }
    )
    sports = module.lane_gate(
        {
            "source": "SPORTS_ODDS",
            "sector": "sports_odds_decision_data",
            "generated_utc": "2026-06-21T00:00:00+00:00",
            "primary_live_evidence": True,
            "measured_source": True,
            "estimated_hourly_value_usd": 100,
            "estimated_annual_value_usd": 876000,
            "baseline_loss_rate_usd_per_hour": 1000,
            "optimization_gain_pct": 10,
        }
    )

    assert market["status"] == "estimated_value_signal"
    assert sports["status"] == "estimated_value_signal"
    assert "Do not present as trading profit" in market["allowed_language"]
    assert "wagering edge" in sports["allowed_language"]
