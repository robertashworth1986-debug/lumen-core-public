from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_champion_sample_expansion_bridge_keeps_economic_claims_disciplined() -> None:
    script = ROOT / "code" / "ops" / "BUILD_CHAMPION_SAMPLE_EXPANSION_AND_ECONOMIC_BRIDGE.py"
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True, capture_output=True, text=True, timeout=120)

    payload_path = ROOT / "out" / "ops" / "champion_sample_expansion_and_economic_bridge_latest.json"
    dashboard_path = ROOT / "dashboard" / "data" / "champion_sample_expansion_and_economic_bridge.json"
    doc_path = ROOT / "docs" / "CHAMPION_SAMPLE_EXPANSION_AND_ECONOMIC_BRIDGE_2026-06-30.md"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    summary = payload["summary"]
    econ = payload["economic_bridge"]
    lanes = {row["lane"]: row for row in payload["lane_diagnostics"]}

    assert payload["schema"] == "champion_sample_expansion_and_economic_bridge_v1"
    assert summary["ready_rows"] >= 300
    assert summary["baseline_comparison_count"] >= 900
    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False

    assert lanes["wave_resonance_timing"]["status"] == "strong_internal_replay_champion"
    assert lanes["wave_resonance_timing"]["win_rate"] == 1.0
    assert lanes["wave_resonance_timing"]["baseline_comparison_count"] >= 576
    assert lanes["wave_resonance_timing"]["comparison_gap_to_target"] == 0
    assert lanes["thermal_ventilation"]["status"] == "promising_but_underpowered"
    assert lanes["optimal_curve_transport"]["status"] == "promising_but_underpowered"
    assert lanes["field_guided_control"]["status"] == "adapter_needed_before_claim"
    assert lanes["mission_network_routing"]["status"] == "adapter_needed_before_claim"

    assert "not a direct percent savings claim" in econ["what_600_of_600_means"]
    assert "addressable annual cost" in econ["future_dollar_formula"]
    assert "realized dollar savings" in econ["not_allowed_yet"]
    assert all(row["boundary"].startswith("Example math only") for row in econ["illustrative_only_examples"])

    target_names = {target["name"] for target in payload["validation_targets"]}
    assert "EPRI Incubatenergy Labs / AI for Power" in target_names
    assert "Spark Innovation Center / TVA / UT Research Park" in target_names
    assert dashboard_path.exists()
    assert doc_path.exists()
