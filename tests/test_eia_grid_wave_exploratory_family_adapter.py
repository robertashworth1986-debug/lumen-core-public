from __future__ import annotations

import copy
import hashlib
import importlib.util
import math
from datetime import date, timedelta
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EIA_SCRIPT = ROOT / "code" / "eia_grid_wave_champion_benchmark.py"
ADAPTER_SCRIPT = ROOT / "code" / "eia_grid_wave_exploratory_family_adapter.py"
PROTOCOL = ROOT / "config" / "eia_grid_wave_champion_protocol_v1.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def synthetic_protocol(eia_module):
    protocol = copy.deepcopy(eia_module.load_protocol())
    protocol["panel"]["balancing_authorities"] = [
        {"respondent": "TEST", "name": "Test Authority", "timezone": "Central"}
    ]
    protocol["panel"]["start_date"] = "2024-01-01"
    protocol["panel"]["end_date"] = "2024-10-31"
    protocol["split"].update(
        {
            "minimum_history_days": 60,
            "development_start": "2024-03-15",
            "development_end": "2024-07-31",
            "holdout_start": "2024-08-01",
            "holdout_end": "2024-10-31",
            "development_origin_stride_days": 14,
            "holdout_origin_stride_days": 7,
        }
    )
    return protocol


def synthetic_panel(eia_module, protocol):
    rows = []
    start = date.fromisoformat(protocol["panel"]["start_date"])
    end = date.fromisoformat(protocol["panel"]["end_date"])
    current = start
    index = 0
    while current <= end:
        value = (
            1000.0
            + 80.0 * math.sin(2.0 * math.pi * index / 7.0)
            + 0.5 * index
        )
        for kind, observation in (("D", value), ("DF", value * 1.01)):
            rows.append(
                {
                    "period": current.isoformat(),
                    "respondent": "TEST",
                    "respondent_name": "Test Authority",
                    "timezone": "Central",
                    "type": kind,
                    "type_name": (
                        "Demand"
                        if kind == "D"
                        else "Day-ahead demand forecast"
                    ),
                    "value": observation,
                    "value_units": "megawatthours",
                }
            )
        current += timedelta(days=1)
        index += 1
    return {
        "schema": "eia_grid_validation_panel.v1",
        "protocol": {
            "path": "config/eia_grid_wave_champion_protocol_v1.json",
            "sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
            "frozen_commit": "test",
            "protocol_id": protocol["protocol_id"],
        },
        "quality": {"row_count": len(rows)},
        "row_chain_sha256": eia_module.canonical_sha256(rows),
        "rows": rows,
    }


def test_policy_is_hash_bound_and_permanently_exploratory():
    adapter = load_module(ADAPTER_SCRIPT, "eia_grid_wave_exploratory_adapter")
    eia = load_module(EIA_SCRIPT, "eia_grid_wave_frozen_benchmark")
    policy = adapter.load_policy()

    assert policy["source_protocol"]["sha256"] == adapter.file_sha256(PROTOCOL)
    assert policy["evaluation_contract"]["holdout_previously_observed"] is True
    assert policy["evaluation_contract"]["prospectively_protected"] is False
    assert policy["evaluation_contract"]["promotion_eligible"] is False
    assert policy["candidate"]["id"] not in {
        row["id"] for row in eia.load_protocol()["wave_candidates"]
    }
    assert policy["claim_controls"]["public_performance_claim_allowed"] is False
    assert policy["claim_controls"]["field_validation_claim_allowed"] is False
    assert policy["claim_controls"]["realized_savings_claim_allowed"] is False
    assert policy["claim_controls"]["trading_or_control_execution_allowed"] is False
    assert (
        policy["claim_controls"][
            "external_replication_required_for_any_field_claim"
        ]
        is True
    )


def test_candidate_forecast_uses_only_pre_origin_history():
    adapter = load_module(ADAPTER_SCRIPT, "eia_grid_wave_exploratory_history")
    eia = load_module(EIA_SCRIPT, "eia_grid_wave_frozen_history")
    protocol = synthetic_protocol(eia)
    panel = synthetic_panel(eia, protocol)
    original_rows, summary = adapter.evaluate(panel, protocol, eia)

    first_holdout = min(
        row["target_date"] for row in original_rows if row["split"] == "holdout"
    )
    altered_panel = copy.deepcopy(panel)
    for row in altered_panel["rows"]:
        if row["period"] >= first_holdout and row["type"] == "D":
            row["value"] = float(row["value"]) * 100.0
    altered_panel["row_chain_sha256"] = eia.canonical_sha256(altered_panel["rows"])
    altered_rows, _ = adapter.evaluate(altered_panel, protocol, eia)

    original = next(
        row for row in original_rows if row["target_date"] == first_holdout
    )
    altered = next(
        row for row in altered_rows if row["target_date"] == first_holdout
    )
    assert original["predicted_mwh"] == altered["predicted_mwh"]
    assert original["actual_mwh"] != altered["actual_mwh"]
    assert summary["history_only"] is True
    assert summary["prospectively_protected"] is False
    assert summary["promotion_eligible"] is False


def test_protocol_hash_mismatch_fails_closed():
    adapter = load_module(ADAPTER_SCRIPT, "eia_grid_wave_exploratory_hash")
    eia = load_module(EIA_SCRIPT, "eia_grid_wave_frozen_hash")
    protocol = synthetic_protocol(eia)
    panel = synthetic_panel(eia, protocol)
    policy = copy.deepcopy(adapter.load_policy())
    policy["source_protocol"]["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="protocol hash"):
        adapter.evaluate(panel, protocol, eia, policy)
