from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "geometry_time_series_model_routing_benchmark.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_time_series_model_routing_benchmark", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_series_groups_and_sorts_rows_chronologically():
    module = load_module()
    snapshot = {
        "rows": [
            {"date": "2026-03-01", "series_id": "A", "value": "3.0"},
            {"date": "2026-01-01", "series_id": "A", "value": "1.0"},
            {"date": "2026-02-01", "series_id": "A", "value": "2.0"},
            {"date": "2026-02-01", "series_id": "B", "value": "20.0"},
            {"date": "2026-01-01", "series_id": "B", "value": "10.0"},
        ]
    }

    series = module.extract_series(snapshot, "TEST")

    assert [row["series_id"] for row in series] == ["A", "B"]
    assert series[0]["values"] == [1.0, 2.0, 3.0]
    assert series[1]["values"] == [10.0, 20.0]
    assert series[0]["value_field"] == "value"


def test_walk_forward_predictions_do_not_change_when_only_future_tail_changes():
    module = load_module()
    base_values = [100.0 + index + 0.1 * (index % 4) for index in range(64)]
    changed_values = list(base_values)
    changed_values[48:] = [value + 10_000.0 for value in changed_values[48:]]
    base = {
        "source": "TEST",
        "series_id": "S1",
        "value_field": "value",
        "values": base_values,
    }
    changed = {**base, "values": changed_values}

    before = module.evaluate_series(base)
    after = module.evaluate_series(changed)
    before_predictions = {
        (row["evaluation_unit"], row["strategy"]): row["predicted"]
        for row in before
        if row["origin"] <= 48
    }
    after_predictions = {
        (row["evaluation_unit"], row["strategy"]): row["predicted"]
        for row in after
        if row["origin"] <= 48
    }

    assert before_predictions
    assert before_predictions == after_predictions


def test_live_source_evaluation_reports_accepted_and_skipped_series(tmp_path):
    module = load_module()
    accepted_path = tmp_path / "accepted.json"
    skipped_path = tmp_path / "skipped.json"
    accepted_path.write_text(
        json.dumps(
            {
                "rows": [
                    {"date": f"2026-01-{index + 1:02d}", "symbol": "A", "close": 50.0 + index}
                    for index in range(30)
                ]
            }
        ),
        encoding="utf-8",
    )
    skipped_path.write_text(
        json.dumps({"rows": [{"date": "2026-01-01", "value": 1.0}]}),
        encoding="utf-8",
    )
    refs = [
        {"source": "ACCEPTED", "snapshot_json": accepted_path.name},
        {"source": "SKIPPED", "snapshot_json": skipped_path.name},
    ]

    rows, summary = module.evaluate_live_sources(refs, tmp_path)
    leaderboard = module.ranked_aggregate(module.aggregate(rows))
    gate = module.score_against_baseline(leaderboard)

    assert rows
    assert summary["accepted_source_count"] == 1
    assert summary["accepted_series_count"] == 1
    assert summary["skipped_source_count"] == 1
    assert summary["leakage_control"].startswith("expanding history")
    assert {row["family_id"] for row in leaderboard} >= {
        "naive_last",
        "linear_trend",
        "fractal_brownian_surface",
    }
    assert gate["best_baseline"]["kind"] == "baseline"
    assert gate["best_geometry"]["family_id"] == "fractal_brownian_surface"
