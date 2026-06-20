from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LUMENCORE_HIGH_IMPACT_GOAL.py"


def load_module():
    spec = importlib.util.spec_from_file_location("lumencore_high_impact_goal", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_high_impact_goal_keeps_lumenstock_non_security():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "lumencore_high_impact_goal_v1"
    assert "proof-driven adaptive orchestration stack" in payload["north_star_goal"]
    assert payload["lumenstock"]["ticker_style_symbol"] == "LUMEN-PWI"
    assert "not equity" in payload["lumenstock"]["interpretation"]
    assert any("Do not represent LumenStock as stock" in item for item in payload["hard_boundaries"])
    assert any("Representative data before field-performance language" in item for item in payload["operating_doctrine"])


def test_lumenstock_score_uses_current_truth_without_guarantees():
    module = load_module()
    payload = module.build_payload()

    assert 0 <= payload["lumenstock"]["composite"] <= 100
    assert payload["current_truth"]["local_blockers"] == 0
    assert payload["current_truth"]["portal_user_blockers"] > 0
    assert payload["current_truth"]["harbor_ais_posture"] == "PUBLIC_AIS_SINGLE_LANE_GATE_READY"
    assert payload["current_truth"]["harbor_ais_io_preflight_posture"] in {
        "PUBLIC_AIS_SPLIT_IO_READY",
        "PUBLIC_AIS_SPLIT_IO_BLOCKED",
        "NOT_RUN",
    }
    assert payload["current_truth"]["harbor_ais_injection_benchmark_posture"] in {
        "PUBLIC_AIS_INJECTION_BENCHMARK_READY",
        "PUBLIC_AIS_INJECTION_BENCHMARK_REVIEW",
        "NOT_RUN",
    }
    assert payload["current_truth"]["harbor_public_ais_validation_rows"] == 50000
    assert any("controlled-injection detector evidence" in item for item in payload["hard_boundaries"])
    assert any("controlled-injection result" in item for item in payload["next_72_hours"])
    assert "guaranteed funding" in " ".join(payload["hard_boundaries"]).lower()
