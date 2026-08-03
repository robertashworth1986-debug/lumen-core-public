from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LIVE_PROOF_VALUE_METER.py"


def load_module():
    spec = importlib.util.spec_from_file_location("live_proof_value_meter", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_value_meter_keeps_estimated_value_separate_from_realized_money(tmp_path, monkeypatch):
    module = load_module()

    top5 = tmp_path / "top5.json"
    dollar = tmp_path / "dollar.json"
    live = tmp_path / "live.json"
    parity = tmp_path / "parity.json"
    geometry = tmp_path / "geometry.json"
    cross_sector = tmp_path / "cross_sector.json"

    write_json(
        top5,
        {
            "global_live_proof_gate": {
                "proposal_specific_live_proof_count": 1,
                "proposal_specific_live_proof_total": 2,
                "packages_with_live_proof": ["DICE"],
                "packages_missing_live_proof": ["NV065"],
                "ready_for_any_final_submit": False,
                "rule": "No final submit until proof gates pass.",
            },
            "packages": [
                {
                    "rank": 1,
                    "package": "DICE",
                    "portal": "DARPA BAAT",
                    "opportunity": "HR001126S0010",
                    "ready_for_final_submit": False,
                    "live_proof": {"proposal_specific_live_proof": True, "proof_status": "PASS_BOUNDED"},
                },
                {
                    "rank": 2,
                    "package": "NV065",
                    "portal": "DSIP",
                    "opportunity": "DON26BZ03-NV065",
                    "ready_for_final_submit": False,
                    "live_proof": {"proposal_specific_live_proof": False, "proof_status": "BLOCKED"},
                },
            ],
        },
    )
    write_json(
        dollar,
        {
            "summary": {
                "allowed_estimated_value_claims": 1,
                "allowed_estimated_hourly_value_usd": 12500,
                "allowed_estimated_annual_value_usd": 109500000,
                "blocked_context_only_annual_value_usd": 26280000000,
                "panel_primary_evidence_mode": "live_measured_delta_rows",
                "live_measured_source_row_count": 1,
            },
            "estimated_value_lanes": [
                {
                    "source": "EIA",
                    "sector": "power_grid",
                    "status": "estimated_value_signal",
                    "claim_band": "large_estimated_signal",
                    "estimated_hourly_value_usd": 12500,
                    "estimated_annual_value_usd": 109500000,
                    "baseline_loss_rate_usd_per_hour": 250000,
                    "optimization_gain_pct": 5,
                    "primary_live_evidence": True,
                    "allowed_language": "Allowed: bounded estimated value signal under stated assumptions.",
                }
            ],
            "context_only_or_blocked_lanes": [
                {
                    "source": "FEDWIRE_OPS",
                    "sector": "financial_market_infra",
                    "status": "blocked_context_only",
                    "estimated_annual_value_usd": 26280000000,
                    "missing_for_stronger_claim": ["live_measured_source"],
                }
            ],
        },
    )
    write_json(
        live,
        {
            "headline": {
                "live_measured_estimated_annual_value_usd": 109500000,
                "context_only_estimated_annual_value_usd": 26280000000,
                "primary_evidence_mode": "live_measured_delta_rows",
                "live_measured_source_row_count": 1,
            }
        },
    )
    write_json(
        parity,
        {
            "live_domain_parity": {
                "feed_ok": 0,
                "feed_total": 3,
                "parity_state": "HTML_LIVE_DATA_FEEDS_MISSING",
                "boundary": "Feeds must be deployed before reviewer-facing live claims.",
            }
        },
    )
    write_json(geometry, {"promotion_gate": {"ready_for_real_dollar_claim": False}})
    write_json(
        cross_sector,
        {
            "status": "NO_CROSS_SECTOR_EFFICIENCY_GAIN_PROVEN",
            "gates": {
                "sector_gain_proven_count": 0,
                "sector_count": 6,
                "cross_sector_efficiency_claim_allowed": False,
                "dollar_projection_from_forecast_error_allowed": False,
            },
            "claim_boundary": "No cross-sector or dollar claim.",
        },
    )

    monkeypatch.setattr(module, "TOP5_PROOF", top5)
    monkeypatch.setattr(module, "DOLLAR_GATE", dollar)
    monkeypatch.setattr(module, "LIVE_BREADTH", live)
    monkeypatch.setattr(module, "PARITY_AUDIT", parity)
    monkeypatch.setattr(module, "GEOMETRY_FRONTIER", geometry)
    monkeypatch.setattr(module, "CROSS_SECTOR_BENCHMARK", cross_sector)

    payload = module.build_payload()

    assert payload["proof_gate"]["proposal_specific_live_proof_count"] == 1
    assert payload["value_gate"]["safe_claim"]["estimated_value_signal_allowed"] is True
    assert payload["value_gate"]["safe_claim"]["realized_customer_or_government_savings_allowed"] is False
    assert payload["value_gate"]["safe_claim"]["trading_profit_claim_allowed"] is False
    assert payload["value_gate"]["safe_claim"]["live_domain_data_feed_ready"] is False
    one_billion = payload["sector_capture_math"][0]
    assert one_billion["sector_or_loss_pool_usd"] == 1_000_000_000
    assert one_billion["capture_examples"][0]["improvement_or_capture_pct"] == 0.01
    assert one_billion["capture_examples"][0]["gross_value_usd"] == 100_000
    assert payload["package_value_readiness"][0]["safe_value_language"].startswith("proposal-specific")
    assert "proof is blocked" in payload["package_value_readiness"][1]["safe_value_language"]
    assert payload["current_model_benchmark"]["sector_gain_proven_count"] == 0
    assert payload["current_model_benchmark"]["dollar_projection_from_forecast_error_allowed"] is False


def test_value_meter_outputs_dashboard_json(tmp_path, monkeypatch):
    module = load_module()
    payload = {
        "generated_utc": "2026-06-22T00:00:00+00:00",
        "answer": {
            "undeniable_live_proof_now": False,
            "current_state": "test",
            "what_is_safe_now": "bounded",
            "what_is_not_safe": "realized",
        },
        "proof_gate": {
            "proposal_specific_live_proof_count": 0,
            "proposal_specific_live_proof_total": 0,
            "ready_for_any_final_submit": False,
        },
        "value_gate": {
            "allowed_estimated_hourly_value_usd": 0,
            "allowed_estimated_annual_value_usd": 0,
            "blocked_context_only_annual_value_usd": 0,
            "safe_claim": {
                "estimated_value_signal_allowed": False,
                "realized_customer_or_government_savings_allowed": False,
                "trading_profit_claim_allowed": False,
                "live_domain_data_feed_ready": False,
            },
        },
        "top_safe_estimated_value_lanes": [],
        "top_blocked_context_value_lanes": [],
        "next_actions": [],
    }
    out_json = tmp_path / "out.json"
    dash_json = tmp_path / "dashboard.json"
    out_md = tmp_path / "meter.md"
    monkeypatch.setattr(module, "OUT_JSON", out_json)
    monkeypatch.setattr(module, "DASHBOARD_JSON", dash_json)
    monkeypatch.setattr(module, "OUT_MD", out_md)

    module.write_outputs(payload)

    assert json.loads(out_json.read_text(encoding="utf-8"))["answer"]["what_is_safe_now"] == "bounded"
    assert json.loads(dash_json.read_text(encoding="utf-8"))["answer"]["what_is_not_safe"] == "realized"
    assert "Live Proof Value Meter" in out_md.read_text(encoding="utf-8")
