from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_energy_price_pressure_forecast_writes_safe_claim_gates() -> None:
    script = ROOT / "code" / "ops" / "BUILD_ENERGY_PRICE_PRESSURE_FORECAST.py"
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True, capture_output=True, text=True, timeout=120)

    payload_path = ROOT / "out" / "ops" / "energy_price_pressure_forecast_latest.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    summary = payload["summary"]

    assert payload["schema"] == "energy_price_pressure_forecast.v1"
    assert summary["hourly_grid_rows"] > 0
    assert summary["forecast_rows"] == 24
    assert summary["ready_for_price_pressure_claim"] is True
    assert summary["actual_electricity_price_series_connected"] is False
    assert summary["ready_for_real_dollar_claim"] is False
    assert summary["kraken_live_execution_allowed"] is False
    assert "not an actual wholesale power price forecast" in payload["evidence_boundary"]


def test_rolling_champion_gate_keeps_repeat_standard() -> None:
    script = ROOT / "code" / "ops" / "BUILD_ROLLING_CHAMPION_GATE.py"
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True, capture_output=True, text=True, timeout=120)

    payload_path = ROOT / "out" / "ops" / "rolling_champion_gate_latest.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    summary = payload["summary"]

    assert payload["schema"] == "rolling_champion_gate.v1"
    assert summary["entity_count"] >= 1
    assert summary["ready_for_real_dollar_claim"] is False
    assert summary["kraken_live_execution_allowed"] is False
    assert all(row["ready_for_real_dollar_claim"] is False for row in payload["promotion_board"])
    assert all(row["field_validation"] is False for row in payload["promotion_board"])
    for row in payload["promotion_board"]:
        if row["status"] == "rolling_champion":
            assert row["repeat_live_win_count"] >= 2
        if row["status"] == "triple_source_candidate":
            assert row["repeat_live_win_count"] < 2
            assert row["source_count"] >= 3
