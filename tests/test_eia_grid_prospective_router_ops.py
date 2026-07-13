from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "eia_grid_prospective_router_ops.py"


def load_module():
    spec = importlib.util.spec_from_file_location("eia_grid_prospective_ops", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prediction(module, authority: str, target: str, record_hash: str):
    return {
        "respondent": authority,
        "target_date": target,
        "record_sha256": record_hash,
    }


def settlement(module, authority: str, target: str, prediction_hash: str, router: float):
    specialist_metrics = {
        "xgboost_residual": {"seasonal_mase_7": router},
        "direct_lightgbm_stack": {"seasonal_mase_7": router + 0.1},
        "autoregressive_ridge_p14": {"seasonal_mase_7": router + 0.2},
        "eia_day_ahead_forecast": {"seasonal_mase_7": router + 0.3},
    }
    return {
        "respondent": authority,
        "target_date": target,
        "prediction_record_sha256": prediction_hash,
        "router_seasonal_mase_7": router,
        "router_regret_to_oracle": 0.0,
        "route_hit": True,
        "specialist_metrics": specialist_metrics,
    }


def test_status_counts_common_authority_days_and_keeps_promotion_open():
    module = load_module()
    protocol = module.core.load_protocol()
    predictions = []
    settlements = []
    for authority in protocol["balancing_authorities"]:
        record_hash = f"{authority}-hash"
        predictions.append(prediction(module, authority, "2026-07-14", record_hash))
        settlements.append(settlement(module, authority, "2026-07-14", record_hash, 0.2))

    module.validate_cross_chain(predictions, settlements)
    status = module.build_status(protocol, predictions, settlements)
    assert status["state"] == "PROSPECTIVE_COLLECTION_ACTIVE"
    assert status["common_settled_day_count"] == 1
    assert status["current_best_fixed_specialist"] == "xgboost_residual"
    assert status["router_skill_vs_current_best_fixed"] == pytest.approx(0.0)
    assert status["sample_gates"]["preliminary_30_days_ready"] is False
    assert status["promotion_evaluation_complete"] is False


def test_cross_chain_rejects_orphan_settlement():
    module = load_module()
    predictions = [prediction(module, "CISO", "2026-07-14", "known")]
    settlements = [settlement(module, "CISO", "2026-07-14", "unknown", 0.2)]
    with pytest.raises(ValueError, match="outside the verified chain"):
        module.validate_cross_chain(predictions, settlements)


def test_operational_receipts_form_a_tamper_evident_chain(tmp_path):
    module = load_module()
    path = tmp_path / "runs.jsonl"
    first = module.append_operational_receipt({"run": 1}, path)
    second = module.append_operational_receipt({"run": 2}, path)
    records, terminal = module.core.load_chain(path)
    assert [row["run"] for row in records] == [1, 2]
    assert terminal == second["record_sha256"]
    assert second["prior_record_chain_sha256"] == first["record_sha256"]


def test_cycle_lock_rejects_overlap(tmp_path):
    module = load_module()
    path = tmp_path / "cycle.lock"
    with module.cycle_lock(path):
        with pytest.raises(RuntimeError, match="already locked"):
            with module.cycle_lock(path):
                pass
    assert not path.exists()
