from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_truth_chain_promotes_only_live_measured_value_signal(tmp_path) -> None:
    module = load_module(
        "frozen_delta_truth_chain",
        ROOT / "code" / "ops" / "BUILD_FROZEN_DELTA_TRUTH_CHAIN.py",
    )

    live_panel = tmp_path / "live_breadth_value_panel_latest.json"
    live_panel.write_text(
        json.dumps(
            {
                "headline": {
                    "total_estimated_hourly_value_usd": 1_000_000.0,
                    "total_estimated_annual_value_usd": 8_760_000_000.0,
                    "live_measured_estimated_hourly_value_usd": 12.5,
                    "live_measured_estimated_annual_value_usd": 109_500.0,
                    "context_only_estimated_hourly_value_usd": 999_987.5,
                    "context_only_estimated_annual_value_usd": 8_759_890_500.0,
                    "primary_evidence_mode": "live_measured_delta_rows",
                    "live_measured_source_row_count": 1,
                    "unmeasured_source_row_count": 2,
                    "reference_fallback_used": True,
                    "measured_sources": 1,
                    "enabled_sources": 3,
                    "measured_coverage_pct": 33.33,
                }
            }
        ),
        encoding="utf-8",
    )
    valuation = tmp_path / "master_valuation_latest.json"
    valuation.write_text(
        json.dumps({"inputs": {"annual_value_signal_usd": 99_000_000_000.0}, "valuation": {}}),
        encoding="utf-8",
    )

    old_paths = {
        "LIVE_PANEL": module.LIVE_PANEL,
        "MASTER_VAL": module.MASTER_VAL,
        "READINESS": module.READINESS,
        "PUBLIC_TRUTH": module.PUBLIC_TRUTH,
        "GRANTS_QUEUE": module.GRANTS_QUEUE,
        "JOBS_QUEUE": module.JOBS_QUEUE,
        "OPP_TRACKER": module.OPP_TRACKER,
        "EXEC_EVENTS_A": module.EXEC_EVENTS_A,
        "EXEC_EVENTS_B": module.EXEC_EVENTS_B,
    }
    try:
        module.LIVE_PANEL = live_panel
        module.MASTER_VAL = valuation
        module.READINESS = tmp_path / "missing_readiness.json"
        module.PUBLIC_TRUTH = tmp_path / "missing_public_truth.json"
        module.GRANTS_QUEUE = tmp_path / "missing_grants.json"
        module.JOBS_QUEUE = tmp_path / "missing_jobs.json"
        module.OPP_TRACKER = tmp_path / "missing_tracker.json"
        module.EXEC_EVENTS_A = tmp_path / "missing_events_a.jsonl"
        module.EXEC_EVENTS_B = tmp_path / "missing_events_b.jsonl"

        metrics = module.collect_state()["metrics"]
    finally:
        for name, value in old_paths.items():
            setattr(module, name, value)

    assert metrics["annual_value_signal_usd"] == 109_500.0
    assert metrics["promoted_live_measured_annual_value_usd"] == 109_500.0
    assert metrics["context_total_annual_value_usd"] == 8_760_000_000.0
    assert metrics["context_only_annual_value_usd"] == 8_759_890_500.0
    assert metrics["legacy_valuation_annual_value_signal_usd"] == 99_000_000_000.0
    assert metrics["primary_evidence_mode"] == "live_measured_delta_rows"
