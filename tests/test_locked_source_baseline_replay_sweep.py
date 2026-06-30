from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_locked_source_baseline_replay_sweep_runs_full_ready_universe() -> None:
    script = ROOT / "code" / "ops" / "BUILD_LOCKED_SOURCE_BASELINE_REPLAY_SWEEP.py"
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True, capture_output=True, text=True, timeout=240)

    payload_path = ROOT / "out" / "ops" / "locked_source_baseline_replay_sweep_latest.json"
    dashboard_path = ROOT / "dashboard" / "data" / "locked_source_baseline_replay_sweep.json"
    doc_path = ROOT / "docs" / "LOCKED_SOURCE_BASELINE_REPLAY_SWEEP_2026-06-30.md"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    summary = payload["summary"]

    assert payload["schema"] == "locked_source_baseline_replay_sweep_v1"
    assert summary["ready_rows"] >= 300
    assert summary["adapter_backed_routes"] >= 300
    assert summary["geometry_routes_replayed"] > 0
    assert summary["energy_proxy_routes_replayed"] > 0
    assert summary["baseline_comparison_count"] >= 900
    assert summary["numeric_samples_read"] > 0
    assert summary["source_conditioned_replay_claim_allowed"] is True
    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert summary["fixed_dollar_delta_sale_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False
    assert summary["medical_or_addiction_treatment_claim_allowed"] is False
    assert payload["claim_gates"]["buyer_or_agency_heldout_data_required"] is True
    assert dashboard_path.exists()
    assert doc_path.exists()
